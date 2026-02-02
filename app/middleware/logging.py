import structlog
import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from app.config import get_settings

def get_log_level(level_name: str) -> int:
    """Convert log level name to logging module level"""
    return getattr(logging, level_name.upper(), logging.INFO)


def _mask_sensitive_processor(logger, method_name, event_dict):
    """Structlog processor that masks sensitive values in the event dict.

    It looks for common secret-related keys (api_key, authorization, token, secret)
    and replaces their values with a masked string preserving only the last 4 chars
    when possible.
    """
    try:
        for k in list(event_dict.keys()):
            if not isinstance(k, str):
                continue
            kl = k.lower()
            # Look for common secret keys
            if any(s in kl for s in ("api_key", "openai_api_key", "auth", "token", "secret")) or kl == "authorization":
                # For explicit Authorization fields we remove them entirely to avoid any chance
                # of logging JWTs or bearer tokens. For other secret-like keys we replace
                # with a structured non-secret summary.
                if kl == "authorization":
                    # remove the authorization header/value from logs
                    event_dict.pop(k, None)
                    continue

                v = event_dict.get(k)
                # Determine token type heuristically
                if 'auth' in kl or 'authorization' in kl or 'token' in kl:
                    token_type = 'jwt' if 'bearer' in str(v).lower() or 'jwt' in str(v).lower() else 'auth_token'
                else:
                    token_type = 'api_key'

                try:
                    s = str(v)
                    # compute hash prefix (safe; hash doesn't reveal the secret)
                    import hashlib as _hl
                    hash_prefix = _hl.sha256(s.encode()).hexdigest()[:8]
                    if len(s) > 4:
                        mask = '*' * (len(s) - 4) + s[-4:]
                    else:
                        mask = '***'
                except Exception:
                    hash_prefix = None
                    mask = '***'

                # Try to infer a source from other keys in the event dict
                source = event_dict.get('api_key_source') or event_dict.get('source') or event_dict.get('token_source') or 'unknown'

                # Replace the raw value with a structured, non-secret summary
                event_dict[k] = {
                    'token_type': token_type,
                    'source': source,
                    'mask': mask,
                    'hash_prefix': hash_prefix,
                }
    except Exception:
        # If masking fails for any reason, avoid raising from the logging path.
        pass
    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _mask_sensitive_processor,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(get_log_level(get_settings().log_level)),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and outgoing responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        user_id = getattr(request.state, "user_id", "anonymous")

        start_time = time.time()
        
        log = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            client_ip=request.client.host if request.client else None,
        )
        log.info("Incoming request")
        try:
            response = await call_next(request)

            process_time = time.time() - start_time
            log.bind(
                status_code=response.status_code,
                process_time=process_time
            ).info("Request processed successfully")

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"
            return response
        except Exception as e:
            process_time = time.time() - start_time
            log.bind(
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2)   
            ).error("Request processing failed")
            raise e
        
class AuditLogger:
    """Audit logger for AI gateway requests and responses"""

    def __init__(self):
        self.logger = structlog.get_logger("audit")

    async def log_chat_request(
        self,
        request_id: str,
        user_id: str,
        user_name: str,
        model: str,
        prompt: str,
        roles: str,
        groups: list,
        metadata: dict = None
    ):
        """Log chat request details"""
        # Trim the prompt to a safe maximum length to avoid extremely large logs
        try:
            max_prompt_len = 1000
            prompt_str = prompt or ""
            prompt_preview = prompt_str[:200]
            prompt_trimmed = prompt_str[:max_prompt_len]
        except Exception:
            prompt_preview = ""
            prompt_trimmed = ""

        audit_log = logger.bind(
            event="CHAT_REQUEST",
            request_id=request_id,
            user_id=user_id,
            model=model,
            prompt_length=len(prompt_trimmed),
            prompt_preview=prompt_preview,
            prompt=prompt_trimmed,
            roles=roles,
            groups=groups,
            metadata=metadata or {}
        )
        audit_log.info("Chat request logged")


    async def log_chat_response(
        self,
        request_id: str,
        user_id: str,
        model: str,
        status: str,
        latency_ms: float,
        tokens_used: int,
        response_preview: str = None,
        error_code: str = None,
        metadata: dict = None
    ):
        """Log chat response details"""
        audit_log = logger.bind(
            event="CHAT_RESPONSE",
            request_id=request_id,
            user_id=user_id,
            model=model,
            status=status,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            response_preview=response_preview[:100] if response_preview else "",
            error_code=error_code,
            metadata=metadata or {}
        )
        audit_log.info("Chat response logged")

    async def log_rate_limit_exceeded(
        self,
        request_id: str,
        user_id: str,
        model: str,
        limit: int,
        window_seconds: int,
        metadata: dict = None
    ):
        """Log rate limit exceeded event"""
        audit_log = logger.bind(
            event="RATE_LIMIT_EXCEEDED",
            request_id=request_id,
            user_id=user_id,
            model=model,
            limit=limit,
            window_seconds=window_seconds,
            metadata=metadata or {}
        )
        audit_log.warning("Rate limit exceeded")

    async def log_access_denied(
        self,
        request_id: str,
        user_id: str,
        model: str,
        reason: str,
        metadata: dict = None
    ):
        """Log access denied event"""
        audit_log = logger.bind(
            event="ACCESS_DENIED",
            request_id=request_id,
            user_id=user_id,    
            model=model,
            reason=reason,
            metadata=metadata or {}
        )
        audit_log.warning("Access denied event logged")

_audit_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    """Get singleton audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger