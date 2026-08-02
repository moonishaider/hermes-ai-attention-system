"""Direct, auditable provider routes for the approved Hermes runtime models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import load_json
from .storage import Store


class ModelRouteError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SmokeResult:
    route: str
    provider: str
    model: str
    success: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    response_received: bool
    error_class: str | None = None


class DirectModelClient:
    """Calls only configured official endpoints; never logs prompt or response text."""

    KEY_ENV = {"deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY"}

    def __init__(self, config_path: Path, store: Store, *, timeout_seconds: int = 45) -> None:
        self.config = load_json(config_path)
        self.store = store
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _secret(key_name: str) -> str:
        if os.environ.get(key_name):
            return os.environ[key_name]
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    name, value = line.split("=", 1)
                    if name.strip() == key_name:
                        return value.strip()
        return ""

    @staticmethod
    def _tls_context() -> ssl.SSLContext:
        """Use an existing trusted CA bundle; never disable certificate validation."""
        candidates = []
        if os.environ.get("SSL_CERT_FILE"):
            candidates.append(Path(os.environ["SSL_CERT_FILE"]))
        candidates.append(Path("/etc/ssl/cert.pem"))
        candidates.extend((Path.home() / ".hermes/hermes-agent/.venv/lib").glob("python*/site-packages/certifi/cacert.pem"))
        bundle = next((path for path in candidates if path.is_file()), None)
        return ssl.create_default_context(cafile=str(bundle)) if bundle else ssl.create_default_context()

    def generate(
        self, route: str, prompt: str, *, image_data_url: str | None = None,
        feature: str = "runtime", max_output_tokens: int = 24,
    ) -> dict[str, Any]:
        spec = self.config["routes"].get(route)
        if not spec:
            raise ModelRouteError(f"unknown route: {route}")
        provider = spec["provider"]
        key = self._secret(self.KEY_ENV[provider])
        if not key:
            raise ModelRouteError(f"missing {self.KEY_ENV[provider]}")
        if route == "vision" and image_data_url is None:
            raise ModelRouteError("vision route requires an explicit image")
        if not prompt.strip() or len(prompt) > 50_000:
            raise ModelRouteError("prompt must contain 1 to 50,000 characters")
        if not 16 <= max_output_tokens <= 512:
            raise ModelRouteError("max_output_tokens must be between 16 and 512")
        if provider == "deepseek":
            body: dict[str, Any] = {
                "model": spec["model"], "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_output_tokens, "temperature": 0,
            }
            if spec.get("thinking"):
                body["thinking"] = {"type": "enabled"}
        else:
            content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
            if image_data_url:
                content.append({"type": "input_image", "image_url": image_data_url})
            body = {"model": spec["model"], "input": [{"role": "user", "content": content}], "max_output_tokens": max_output_tokens}

        started = time.monotonic()
        usage: dict[str, Any] = {}
        error_class = None
        success = False
        received = False
        output_text = ""
        try:
            request = Request(
                spec["endpoint"], data=json.dumps(body).encode(), method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
            with urlopen(request, timeout=self.timeout_seconds, context=self._tls_context()) as response:
                payload = json.loads(response.read())
            usage = payload.get("usage") or {}
            received = bool(payload)
            if provider == "deepseek":
                output_text = str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""))
            else:
                output_text = str(payload.get("output_text") or "")
                if not output_text:
                    output_text = "\n".join(
                        str(part.get("text", ""))
                        for item in payload.get("output", []) if isinstance(item, dict)
                        for part in item.get("content", []) if isinstance(part, dict) and part.get("type") == "output_text"
                    )
            success = True
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            error_class = type(exc).__name__
        latency = round((time.monotonic() - started) * 1000)
        input_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        output_tokens = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        cost = (input_tokens * float(spec["input_usd_per_million"]) + output_tokens * float(spec["output_usd_per_million"])) / 1_000_000
        self.store.record_usage(
            provider=provider, model=spec["model"], feature=feature, context_id="synthetic" if feature.startswith("route-smoke") else None,
            input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost, latency_ms=latency, success=success,
        )
        return {**asdict(SmokeResult(route, provider, spec["model"], success, latency, input_tokens, output_tokens, cost, received, error_class)), "text": output_text}

    def smoke(self, route: str, *, image_data_url: str | None = None) -> dict[str, Any]:
        result = self.generate(
            route, "Reply with exactly HERMES_ROUTE_OK. This is a synthetic connectivity test.",
            image_data_url=image_data_url, feature=f"route-smoke:{route}",
        )
        result.pop("text", None)
        return result
