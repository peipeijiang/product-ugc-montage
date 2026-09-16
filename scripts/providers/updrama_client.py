#!/usr/bin/env python3
"""Small, dependency-free updrama adapter for GEM-3.1-TTS and Suno v4.5.

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class UpdramaError(RuntimeError):
    pass


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
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_s: float = 60.0):
        self.base_url = (base_url or os.getenv("UPDRAMA_BASE_URL") or "https://api.lk888.ai").rstrip("/")
        self.api_key = api_key or os.getenv("UPDRAMA_API_KEY") or os.getenv("API_KEY")
        self.timeout_s = timeout_s
        if not self.api_key:
            raise UpdramaError("Set UPDRAMA_API_KEY (or API_KEY) before an audio-generation request.")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:
            raise UpdramaError(f"updrama {method} {path} failed: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UpdramaError(f"updrama returned non-JSON from {path}") from exc
        if isinstance(data, dict) and data.get("code") not in (None, 200, "200"):
            raise UpdramaError(f"updrama error from {path}: {data}")
        return data

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def create(self, model: str, prompt: str, params: dict[str, Any] | None = None, notify_url: str | None = None) -> TaskReceipt:
        request: dict[str, Any] = {"model": model, "prompt": prompt, "params": params or {}}
        if notify_url:
            request["notify_url"] = notify_url
        data = self._request("POST", "/v1/media/generate", request)
        payload = data.get("data") if isinstance(data, dict) else None
        task_id = (payload or {}).get("task_id") or data.get("task_id")
        if task_id is None:
            raise UpdramaError(f"create response did not contain task_id: {data}")
        return TaskReceipt(str(task_id), model, self._prompt_hash(prompt), request, time.time())

    def create_gem_tts(self, script: str, voice_id: str) -> TaskReceipt:
        if not voice_id:
            raise UpdramaError("voice_id is required for GEM-3.1-TTS")
        return self.create("gem-3.1-tts", script, {"voice_id": voice_id})

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
        return self._request("GET", path)

    def wait(self, task_id: str, poll_s: float = 4.0, timeout_s: float = 900.0) -> dict[str, Any]:
        deadline = time.time() + timeout_s
        while True:
            status = self.status(task_id)
            if status.get("is_final") is True:
                state = status.get("state")
                if state != "success":
                    raise UpdramaError(f"task {task_id} ended in state={state}: {status}")
                return status
            if time.time() >= deadline:
                raise UpdramaError(f"task {task_id} exceeded timeout {timeout_s}s")
            time.sleep(poll_s)

    def download_result(self, status: dict[str, Any], output_path: str | Path) -> Path:
        url = status.get("result_url")
        if not url:
            raise UpdramaError("successful task has no result_url")
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, output)
        except Exception as exc:
            raise UpdramaError(f"download failed: {exc}") from exc
        return output


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="updrama GEM/Suno adapter; --dry-run never calls the API")
    parser.add_argument("provider", choices=("gem", "suno"))
    parser.add_argument("prompt")
    parser.add_argument("--voice-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        params = {"voice_id": args.voice_id} if args.provider == "gem" else {"make_instrumental": "instrumental", "mv": "chirp-v4-5"}
        print(json.dumps({"model": "gem-3.1-tts" if args.provider == "gem" else "suno-v4.5", "prompt": args.prompt, "params": params, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0
    client = UpdramaClient()
    receipt = client.create_gem_tts(args.prompt, args.voice_id or "") if args.provider == "gem" else client.create_suno_instrumental(args.prompt)
    print(json.dumps(receipt.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
