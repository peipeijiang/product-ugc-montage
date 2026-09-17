#!/usr/bin/env python3
"""Small, dependency-free updrama adapter for GEM-3.1-TTS, Doubao TTS 2.0, and Suno v4.5.

No request is made on import. Callers must explicitly invoke create_* and must
obtain user authorization before doing so. Credentials are read from
UPDRAMA_API_KEY (or API_KEY); never put them in a prompt, manifest, or source.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import tempfile
import ssl
try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CONTEXT = ssl.create_default_context()
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class UpdramaError(RuntimeError):
    pass


def build_request(model: str, prompt: str, params: dict | None = None,
                  notify_url: str | None = None) -> dict:
    """Validate the supplied audio contract without I/O, shared by dry/live runs.

    Doubao follows the pasted top-level parameter table. Its conflicting
    speaker example is NOT evidence that either spelling was live-tested.
    """
    if model not in ('gem-3.1-tts', 'doubao-tts-2.0', 'suno-v4.5'):
        raise UpdramaError('unconfigured audio model; no request was submitted')
    if not isinstance(prompt,str) or not prompt.strip():
        raise UpdramaError('nonempty prompt/script required')
    if params is not None and not isinstance(params,dict):
        raise UpdramaError('params must be an object')
    params=dict(params or {})
    if model in ('gem-3.1-tts','doubao-tts-2.0'):
        if not isinstance(params.get('voice_id'),str) or not params['voice_id'].strip():
            raise UpdramaError('explicit catalog-compatible voice_id required')
    if model=='doubao-tts-2.0':
        enums={'speech_rate':('-50','-25','0','25','50','100'),
               'emotion':('auto','happy','sad','angry','fearful','surprised','calm'),
               'emotion_scale':('1','2','3','4','5'),
               'format':('mp3','wav','ogg_opus')}
        for key,values in enums.items():
            if key in params and str(params[key]) not in values:
                raise UpdramaError('unsupported Doubao '+key)
        if params.get('emotion','auto')=='auto':
            params.pop('emotion_scale',None)
    if model=='suno-v4.5':
        if params.get('make_instrumental')!='instrumental' or params.get('lyrics'):
            raise UpdramaError('this adapter requires instrumental BGM without lyrics')
        if params.get('mv','chirp-v4-5') not in ('chirp-v4-5','chirp-v4','chirp-v3-5','chirp-bluejay'):
            raise UpdramaError('unsupported Suno model version')
    request={'model':model,'prompt':prompt,'params':params}
    if notify_url:
        parsed=urllib.parse.urlsplit(notify_url)
        if parsed.scheme not in ('http','https') or not parsed.netloc:
            raise UpdramaError('notify_url must be an absolute HTTP(S) URL')
        request['notify_url']=notify_url
    return request


@dataclass
class TaskReceipt:
    task_id: str
    model: str
    prompt_sha256: str
    request: dict[str, Any]
    created_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "model": self.model,
            "prompt_sha256": self.prompt_sha256,
            "request": self.request,
            "created_at": self.created_at,
        }


class UpdramaClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_s: float = 60.0, journal: str | Path | None = None):
        self.base_url = (base_url or os.getenv("UPDRAMA_BASE_URL") or "https://api.lk888.ai").rstrip("/")
        self.api_key = api_key or os.getenv("UPDRAMA_API_KEY") or os.getenv("LK888_API_KEY") or os.getenv("API_KEY")
        self.timeout_s = timeout_s
        self.journal = Path(journal) if journal else None
        if not self.api_key:
            raise UpdramaError("Set UPDRAMA_API_KEY (or API_KEY) before an audio-generation request.")

    def _save(self, data: dict) -> None:
        if self.journal is None:
            raise UpdramaError("A per-task journal is required before paid creation")
        fd, name = tempfile.mkstemp(prefix=self.journal.name + '.', dir=self.journal.parent)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.journal)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _record_status(self, task_id: str, status: dict) -> None:
        if self.journal and self.journal.exists():
            record = json.loads(self.journal.read_text())
            if str(record.get('receipt', {}).get('task_id')) != str(task_id):
                raise UpdramaError('journal task_id mismatch')
            record['last_status'] = status
            self._save(record)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s, context=_SSL_CONTEXT) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:
            raise UpdramaError(f"updrama {method} {path} failed: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UpdramaError(f"updrama returned non-JSON from {path}") from exc
        if not isinstance(data,dict):
            raise UpdramaError(f'updrama returned a non-object response from {path}')
        if data.get("code") not in (None, 200, "200"):
            raise UpdramaError(f"updrama error from {path}: {data}")
        return data

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def create(self, model: str, prompt: str, params: dict[str, Any] | None = None, notify_url: str | None = None) -> TaskReceipt:
        request = build_request(model,prompt,params,notify_url)
        if self.journal is None:
            raise UpdramaError('A per-task journal is required; paid creation was not attempted')
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        intent = {'schema_version': 1, 'state': 'creating', 'base_url': self.base_url,
                  'request': request, 'created_at': time.time()}
        try:
            # Claim the operation BEFORE POST. A crash/ambiguous response blocks
            # repeat creation instead of risking a second charge.
            with self.journal.open('x') as f:
                json.dump(intent, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            existing = json.loads(self.journal.read_text())
            if existing.get('request') != request or existing.get('base_url') != self.base_url:
                raise UpdramaError('journal belongs to another request/provider; do not overwrite it')
            if existing.get('receipt'):
                return TaskReceipt(**existing['receipt'])
            raise UpdramaError('Creation outcome uncertain or in progress. Reconcile the existing provider task; do not resubmit.')
        try:
            data = self._request("POST", "/v1/media/generate", request)
            payload = data.get("data") if isinstance(data, dict) else None
            task_id = (payload or {}).get("task_id") or data.get("task_id")
            if task_id is None:
                raise UpdramaError('create response did not contain task_id; reconcile before retry')
            receipt = TaskReceipt(str(task_id), model, self._prompt_hash(prompt), request, time.time())
            self._save({**intent, 'state':'submitted', 'receipt':receipt.as_dict()})
            return receipt
        except Exception:
            # Keep the intent even for network errors: the server may have billed.
            raise

    def resume(self) -> TaskReceipt:
        if not self.journal or not self.journal.is_file():
            raise UpdramaError('existing journal required for resume')
        record = json.loads(self.journal.read_text())
        if record.get('base_url') != self.base_url or not record.get('receipt'):
            raise UpdramaError('provider mismatch or uncertain creation; reconcile manually')
        return TaskReceipt(**record['receipt'])

    def create_gem_tts(self, script: str, voice_id: str) -> TaskReceipt:
        if not voice_id:
            raise UpdramaError("voice_id is required for GEM-3.1-TTS")
        return self.create("gem-3.1-tts", script, {"voice_id": voice_id})

    def create_doubao_tts(
        self,
        script: str,
        voice_id: str,
        *,
        speech_rate: str = "0",
        emotion: str = "auto",
        emotion_scale: str = "4",
        audio_format: str = "mp3",
    ) -> TaskReceipt:
        """Create one complete Doubao TTS 2.0 narration.

        The supplied docs conflict between ``voice_id`` and ``speaker``.
        This adapter follows the top-level table's ``voice_id``; callers should
        query the live voice catalog and pass a frozen-market-compatible
        preset. ``emotion_scale`` is omitted for ``auto`` per the documented
        parameter linkage rule.
        """
        if not voice_id:
            raise UpdramaError("voice_id is required for Doubao TTS 2.0")
        params: dict[str, Any] = {
            "voice_id": voice_id,
            "speech_rate": str(speech_rate),
            "emotion": emotion,
            "format": audio_format,
        }
        if emotion != "auto":
            params["emotion_scale"] = str(emotion_scale)
        return self.create("doubao-tts-2.0", script, params)

    def create_suno_instrumental(self, style_prompt: str, model_version: str = "chirp-v4-5") -> TaskReceipt:
        params = {"make_instrumental": "instrumental", "mv": model_version}
        return self.create("suno-v4.5", style_prompt, params)

    def list_models(self) -> dict[str, Any]:
        """Return the provider's current model catalog (read-only)."""
        return self._request("GET", "/v1/models")

    def list_voices(self, model: str = "gem-3.1-tts") -> dict[str, Any]:
        """Try the provider voice catalog; callers must verify model compatibility."""
        path = "/v1/skills/voices?" + urllib.parse.urlencode({"model": model})
        return self._request("GET", path)

    def status(self, task_id: str) -> dict[str, Any]:
        path = "/v1/media/status?" + urllib.parse.urlencode({"task_id": task_id})
        raw = self._request("GET", path)
        data = raw.get('data') if isinstance(raw.get('data'), dict) else raw
        if not isinstance(data.get('is_final'), bool) or data.get('state') not in ('pending','running','success','failed'):
            raise UpdramaError('malformed task status; no new task was created')
        self._record_status(task_id, data)
        return data

    def wait(self, task_id: str, poll_s: float = 4.0, timeout_s: float = 900.0) -> dict[str, Any]:
        deadline = time.time() + timeout_s
        while True:
            try:
                status = self.status(task_id)
            except UpdramaError:
                if time.time() >= deadline:
                    raise
                time.sleep(max(3.0, min(poll_s, 5.0)))
                continue
            if status.get("is_final") is True:
                state = status.get("state")
                if state != "success":
                    raise UpdramaError(f"task {task_id} ended in state={state}: {status}")
                return status
            if time.time() >= deadline:
                raise UpdramaError(f"task {task_id} exceeded timeout {timeout_s}s")
            time.sleep(max(3.0, min(poll_s, 5.0)))

    def download_result(self, status: dict[str, Any], output_path: str | Path) -> Path:
        if status.get('is_final') is not True or status.get('state') != 'success':
            raise UpdramaError('only successful terminal tasks may be downloaded')
        url = status.get("result_url")
        if not url:
            raise UpdramaError("successful task has no result_url")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Keep incomplete downloads separate from the usable artifact.
            with urllib.request.urlopen(url, timeout=self.timeout_s, context=_SSL_CONTEXT) as response:
                with output.with_suffix(output.suffix + '.part').open('wb') as target:
                    while chunk := response.read(1024 * 1024):
                        target.write(chunk)
            os.replace(output.with_suffix(output.suffix + '.part'), output)
        except Exception as exc:
            raise UpdramaError(f"download failed: {exc}") from exc
        return output


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="updrama GEM/Doubao/Suno adapter; --dry-run never calls the API")
    parser.add_argument("provider", choices=("gem", "doubao", "suno"))
    parser.add_argument("prompt")
    parser.add_argument("--voice-id")
    parser.add_argument("--speech-rate", default="0")
    parser.add_argument("--emotion", default="auto")
    parser.add_argument("--emotion-scale", default="4")
    parser.add_argument("--format", dest="audio_format", default="mp3")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--resume", action="store_true", help="resume saved task; never POST")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dry_run:
        if args.provider == "gem":
            model, params = "gem-3.1-tts", {"voice_id": args.voice_id}
        elif args.provider == "doubao":
            model = "doubao-tts-2.0"
            params = {"voice_id": args.voice_id, "speech_rate": args.speech_rate, "emotion": args.emotion, "format": args.audio_format}
            if args.emotion != "auto":
                params["emotion_scale"] = args.emotion_scale
        else:
            model, params = "suno-v4.5", {"make_instrumental": "instrumental", "mv": "chirp-v4-5"}
        try:
            request=build_request(model,args.prompt,params)
        except UpdramaError as exc:
            parser.error(str(exc))
        print(json.dumps({**request, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0
    if not args.journal:
        parser.error('--journal is required for paid work or resume')
    client = UpdramaClient(journal=args.journal)
    if args.resume:
        receipt = client.resume()
    elif args.provider == "gem":
        receipt = client.create_gem_tts(args.prompt, args.voice_id or "")
    elif args.provider == "doubao":
        receipt = client.create_doubao_tts(args.prompt, args.voice_id or "", speech_rate=args.speech_rate, emotion=args.emotion, emotion_scale=args.emotion_scale, audio_format=args.audio_format)
    else:
        receipt = client.create_suno_instrumental(args.prompt)
    print(json.dumps(receipt.as_dict(), ensure_ascii=False, indent=2))
    if args.wait or args.output:
        status = client.wait(receipt.task_id)
        if args.output:
            client.download_result(status, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
