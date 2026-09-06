"""Direct, auditable provider routes for the approved Hermes runtime models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, UTC
from uuid import uuid4
import json
import hashlib
import os
from pathlib import Path
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from .config import load_json
from .storage import Store


class _NoModelRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Model endpoint redirect refused', headers, fp)

def urlopen(request, *, timeout, context):
    return build_opener(HTTPSHandler(context=context), _NoModelRedirect()).open(request,timeout=timeout)


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
        feature: str = "runtime", max_output_tokens: int = 2048, thinking_override: bool | None = None,
    ) -> dict[str, Any]:
        spec = self.config["routes"].get(route)
        if not spec:
            raise ModelRouteError(f"unknown route: {route}")
        if thinking_override is not None and not (thinking_override is False and route == "difficult" and feature == "dloa-synthesis"):
            raise ModelRouteError("Thinking override is restricted to final DLOA composition")
        provider = spec["provider"]
        endpoints={'deepseek':'https://api.deepseek.com/chat/completions','openai':'https://api.openai.com/v1/responses'}
        if provider not in endpoints or spec.get('endpoint')!=endpoints[provider]:raise ModelRouteError('Unapproved model endpoint')
        month=datetime.now(UTC).strftime('%Y-%m')
        if self.store.monthly_cost(month)>=float(self.config['budget_usd_monthly']['hard']):raise ModelRouteError('Monthly hard budget reached')
        key = self._secret(self.KEY_ENV[provider])
        if not key:
            raise ModelRouteError(f"missing {self.KEY_ENV[provider]}")
        if route == "vision" and image_data_url is None:
            raise ModelRouteError("vision route requires an explicit image")
        prompt_limit = 500_000 if feature == "dloa-synthesis" else 65_000 if feature in {"turn-semantic-intent", "personal-semantic-intent"} else 50_000
        if not prompt.strip() or len(prompt) > prompt_limit:
            raise ModelRouteError(f"prompt must contain 1 to {prompt_limit:,} characters")
        if not 16 <= max_output_tokens <= 8192:
            raise ModelRouteError("max_output_tokens must be between 16 and 8192")
        if provider == "deepseek":
            body: dict[str, Any] = {
                "model": spec["model"], "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_output_tokens, "temperature": 0,
            }
            body["thinking"] = {"type": "enabled" if (spec.get("thinking") if thinking_override is None else thinking_override) else "disabled"}
        else:
            content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
            if image_data_url:
                content.append({"type": "input_image", "image_url": image_data_url})
            body = {"model": spec["model"], "input": [{"role": "user", "content": content}], "max_output_tokens": max_output_tokens}

        attempt_id=str(uuid4())
        request_sha=hashlib.sha256(json.dumps(body).encode()).hexdigest()
        self.store.connection.execute('CREATE TABLE IF NOT EXISTS model_request_claims(attempt_id TEXT PRIMARY KEY,request_sha256 TEXT,prompt_sha256 TEXT,feature TEXT,model TEXT,created_at TEXT)')
        with self.store.connection:self.store.connection.execute('INSERT INTO model_request_claims VALUES(?,?,?,?,?,?)',(attempt_id,request_sha,hashlib.sha256(prompt.encode()).hexdigest(),feature,spec['model'],datetime.now(UTC).isoformat()))
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
            finish_reason = ((payload.get('choices') or [{}])[0]).get('finish_reason') if provider=='deepseek' else payload.get('status')
            success = bool(output_text.strip()) and (finish_reason=='stop' if provider=='deepseek' else finish_reason=='completed')
            if not success:error_class='IncompleteOutput'

        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            error_class = type(exc).__name__
        latency = round((time.monotonic() - started) * 1000)
        input_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        output_tokens = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        now=datetime.now(UTC)
        peak=now.weekday()<5 and any(a<=now.hour<b for a,b in spec.get('peak_utc_hours',[[0,24]]))
        multiplier=1 if peak else float(spec.get('off_peak_multiplier',1))
        cache_hit=min(input_tokens,int(usage.get('prompt_cache_hit_tokens',(usage.get('input_tokens_details') or usage.get('prompt_tokens_details') or {}).get('cached_tokens',0)) or 0))
        cost = ((input_tokens-cache_hit) * float(spec["input_usd_per_million"]) + cache_hit*float(spec.get('cache_hit_usd_per_million',spec['input_usd_per_million'])) + output_tokens * float(spec["output_usd_per_million"])) * multiplier / 1_000_000
        usage_known=bool(usage) and any(k in usage for k in ('prompt_tokens','input_tokens'))
        self.store.connection.execute('CREATE TABLE IF NOT EXISTS model_attempts(attempt_id TEXT PRIMARY KEY,feature TEXT,provider TEXT,model TEXT,usage_known INTEGER,status TEXT,created_at TEXT)')
        with self.store.connection:self.store.connection.execute('INSERT INTO model_attempts VALUES(?,?,?,?,?,?,?)',(attempt_id,feature,provider,spec['model'],int(usage_known),'completed' if success else (error_class or 'unknown'),now.isoformat()))

        self.store.record_usage(
            provider=provider, model=spec["model"], feature=feature, context_id="synthetic" if feature.startswith("route-smoke") else None,
            input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost, latency_ms=latency, success=success,
        )
        return {**asdict(SmokeResult(route, provider, spec["model"], success, latency, input_tokens, output_tokens, cost, received, error_class)), "text": output_text, "cached_input_tokens":cache_hit if ("prompt_cache_hit_tokens" in usage or "cached_tokens" in (usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {})) else None, "model_attempt_id":attempt_id, "request_sha256":hashlib.sha256(json.dumps(body).encode()).hexdigest(), "prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(), "usage_known":usage_known, "estimated_cost_usd":cost if usage_known else None}

    def smoke(self, route: str, *, image_data_url: str | None = None) -> dict[str, Any]:
        result = self.generate(
            route, "Reply with exactly HERMES_ROUTE_OK. This is a synthetic connectivity test.",
            image_data_url=image_data_url, feature=f"route-smoke:{route}", max_output_tokens=64,
        )
        result.pop("text", None)
        return result
