from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from typing import Optional
from pathlib import Path
import time
import os

from app.routing.models import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionError, HealthResponse

from app.auth.jwt_handler import JWTHandler, get_jwt_handler
from app.auth.models import AuthContext
from app.middleware.rate_limiter import get_rate_limiter, RateLimiter
from app.middleware.logging import get_audit_logger, AuditLogger
from app.routing.router import _get_model_router, ModelRouter
from app.config import get_model_config, get_settings, ModelConfig
import structlog

logger = structlog.get_logger("endpoints")


def _mask_key(key: str) -> str:
    """Mask a secret API key keeping only the last 4 characters visible.

    Returns empty string for falsy input.
    """
    if not key:
        return ""
    try:
        k = str(key)
        visible = 4 if len(k) > 6 else 2
        return "*" * (len(k) - visible) + k[-visible:]
    except Exception:
        return "****"

router = APIRouter()

async def get_auth_context(
        authorization: Optional[str] = Header(None),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
) -> AuthContext:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = parts[1]
    auth_context = await jwt_handler.get_auth_context(token)
    return auth_context

@router.post("/chat/completions", response_model=ChatCompletionResponse, responses={
    400: {"model": ChatCompletionError}, 
    401: {"model": ChatCompletionError}, 
    403: {"model": ChatCompletionError}, 
    429: {"model": ChatCompletionError}, 
    500: {"model": ChatCompletionError},
    })
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request = None,
    auth_context: AuthContext = Depends(get_auth_context),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    model_router: ModelRouter = Depends(_get_model_router),
    model_config: ModelConfig = Depends(get_model_config),
):
    """
    Handle chat completion requests
    """
    start_time = time.time()

    # Model routing and validation
    # model_router provides `check_access(auth_context, model_name)` which
    # returns a boolean indicating whether the user may access the model.
    is_allowed = model_router.check_access(auth_context, request.model)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to model '{request.model}' is forbidden"
        )

    # Get rate limit from config. Pass model name and optional group id.
    group_id = (auth_context.groups[0] if auth_context.groups else None)
    rate_limit_value = model_config.get_rate_limits(request.model, group_id)
    # ensure integer fallback
    try:
        rate_limit_value = int(rate_limit_value)
    except Exception:
        rate_limit_value = 100
    
    # Rate limiting - check after model validation
    await rate_limiter.check_rate_limit(
        auth_context, 
        request.model, 
        rate_limit_value
    )

    # Ensure we bind an API key for upstream model requests.
    # Priority: OPENAI_API_KEY header from client -> env (including .env via Settings) -> model-specific api_key
    try:
        model_cfg = model_config.get_model_config(request.model) or {}
        # Resolve placeholder values like ${OPENAI_API_KEY}
        cfg_api_key = model_cfg.get("api_key") if isinstance(model_cfg, dict) else None
        if isinstance(cfg_api_key, str) and cfg_api_key.startswith("${") and cfg_api_key.endswith("}"):
            env_var = cfg_api_key[2:-1].strip()
            # Try os.environ first, then the pydantic Settings which loads .env
            settings = get_settings()
            cfg_api_key = os.getenv(env_var, None) or getattr(settings, env_var, None) or settings.__dict__.get(env_var)
            dotenv_val = None
            # If still not found, try parsing a local .env file as a last resort
            if not cfg_api_key:
                try:
                    env_path = Path('.') / '.env'
                    if env_path.exists():
                        for line in env_path.read_text(encoding='utf-8').splitlines():
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '=' in line:
                                k, v = line.split('=', 1)
                                if k.strip() == env_var:
                                    cfg_api_key = v.strip().strip('"').strip("'")
                                    dotenv_val = cfg_api_key
                                    break
                except Exception:
                    pass
            # Log diagnostic values — mask any secrets so we don't leak keys
            try:
                os_val = os.getenv(env_var)
                settings_val = getattr(settings, env_var, None) or settings.__dict__.get(env_var)
                try:
                    dotenv_mask = _mask_key(dotenv_val) if dotenv_val else None
                except Exception:
                    dotenv_mask = None
                logger.info(
                    "api_key_resolution_check",
                    env_var=env_var,
                    os_present=bool(os_val),
                    settings_present=bool(settings_val),
                    dotenv_present=bool(dotenv_val),
                    os_mask=_mask_key(os_val) if os_val else None,
                    settings_mask=_mask_key(settings_val) if settings_val else None,
                    dotenv_mask=dotenv_mask,
                )
            except Exception:
                pass
            # If still not found, try parsing a local .env file as a last resort
            if not cfg_api_key:
                try:
                    env_path = Path('.') / '.env'
                    if env_path.exists():
                        for line in env_path.read_text(encoding='utf-8').splitlines():
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '=' in line:
                                k, v = line.split('=', 1)
                                if k.strip() == env_var:
                                    cfg_api_key = v.strip().strip('"').strip("'")
                                    break
                except Exception:
                    pass

        header_api_key = None
        if http_request is not None:
            # Check several common header names (case-insensitive) for an API key.
            for hn in ("openai-api-key", "openai_api_key", "openai-api-key", "openai_api-key", "x-api-key", "x-openai-api-key", "openai_api-key", "OPENAI_API_KEY"):
                v = http_request.headers.get(hn)
                if v:
                    header_api_key = v
                    break

        # After validating the JWT (auth_context present), prefer a client-provided
        # header key; otherwise use the gateway's environment OPENAI_API_KEY (from env or .env via Settings).
        settings = get_settings()
        env_api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None) or settings.__dict__.get("OPENAI_API_KEY")
        dot_env_val = None
        if not env_api_key:
            try:
                env_path = Path('.') / '.env'
                if env_path.exists():
                    for line in env_path.read_text(encoding='utf-8').splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == 'OPENAI_API_KEY':
                                env_api_key = v.strip().strip('"').strip("'")
                                dot_env_val = env_api_key
                                break
            except Exception:
                pass
        try:
            os_val = os.getenv('OPENAI_API_KEY')
            settings_val = getattr(settings, 'OPENAI_API_KEY', None) or settings.__dict__.get('OPENAI_API_KEY')
            logger.info(
                "env_api_key_check",
                os_present=bool(os_val),
                settings_present=bool(settings_val),
                dotenv_present=bool(dot_env_val),
                os_mask=_mask_key(os_val) if os_val else None,
                settings_mask=_mask_key(settings_val) if settings_val else None,
                dotenv_mask=_mask_key(dot_env_val) if dot_env_val else None,
            )
        except Exception:
            pass
        if not env_api_key:
            try:
                env_path = Path('.') / '.env'
                if env_path.exists():
                    for line in env_path.read_text(encoding='utf-8').splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == 'OPENAI_API_KEY':
                                env_api_key = v.strip().strip('"').strip("'")
                                break
            except Exception:
                pass
        effective_api_key = header_api_key or env_api_key or cfg_api_key

        # If we have an effective API key, inject it into the in-memory model config so
        # ModelRouter.route_request will pick it up when it builds outbound headers.
        if effective_api_key:
            # Log the resolved key source and a masked preview (do NOT log the full key)
            try:
                ek = str(effective_api_key)
                ek_mask = _mask_key(ek)
                ek_hash = None
                try:
                    import hashlib as _hashlib
                    ek_hash = _hashlib.sha256(ek.encode()).hexdigest()[:8]
                except Exception:
                    ek_hash = None
                logger.info(
                    "resolved_effective_api_key",
                    model=request.model,
                    source=("header" if header_api_key else "env" if env_api_key else "cfg"),
                    api_key_mask=ek_mask,
                    api_key_hash_prefix=ek_hash,
                )
            except Exception:
                pass
            try:
                model_config._config.setdefault("models", {})
                if request.model not in model_config._config["models"]:
                    model_config._config["models"][request.model] = {}
                model_config._config["models"][request.model]["api_key"] = effective_api_key
                # record source for logging/troubleshooting
                model_config._config["models"][request.model]["api_key_source"] = (
                    "header" if header_api_key else "env"
                )
            except Exception:
                # non-fatal; routing will fall back to whatever the model_config supplies
                pass
    except Exception:
        # non-fatal binding failure; continue without overriding api_key
        pass

    # Extract prompt from messages (get the last user message)
    # request.messages is a list of ChatMessage Pydantic models; access via attributes
    prompt = ""
    for msg in reversed(request.messages):
        role = getattr(msg, "role", None) if msg is not None else None
        if role == "user":
            prompt = getattr(msg, "content", "") or ""
            break
    
    # Log the request
    await audit_logger.log_chat_request(
        request_id=http_request.state.request_id,
        user_id=auth_context.username,
        user_name=auth_context.username,
        model=request.model,
        prompt=prompt,
        roles=",".join(auth_context.roles or []),
        groups=auth_context.groups or [],
        metadata={}
    )

    # Route the request to the configured model using ModelRouter. The
    # router returns a ChatCompletionResponse when successful. We capture
    # and log the actual upstream response so it's auditable.
    try:
        model_response = await model_router.route_request(request, auth_context)

        # Extract first choice preview and token usage if available
        choice_content = ""
        try:
            first_choice = model_response.choices[0] if model_response.choices else None
            if first_choice and isinstance(first_choice, dict):
                message = first_choice.get("message", {})
                choice_content = message.get("content", "")
            elif first_choice and hasattr(first_choice, "get") is False:
                # pydantic model-like mapping
                # attempt attribute access
                try:
                    message = getattr(first_choice, "message", None)
                    if message:
                        choice_content = getattr(message, "content", "")
                except Exception:
                    choice_content = ""
        except Exception:
            choice_content = ""

        latency_ms = (time.time() - start_time) * 1000

        # Attempt to collect usage numbers
        prompt_tokens = 0
        completion_tokens = 0
        try:
            usage = model_response.usage or {}
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
        except Exception:
            # best-effort; fallback to word counts
            prompt_tokens = len(prompt.split())
            completion_tokens = len((choice_content or "").split())

        await audit_logger.log_chat_response(
            request_id=http_request.state.request_id,
            user_id=auth_context.username,
            model=request.model,
            status="success",
            latency_ms=latency_ms,
            tokens_used=prompt_tokens + completion_tokens,
            response_preview=choice_content,
            metadata={}
        )

        return model_response
    except HTTPException as he:
        # Preserve upstream HTTP errors (4xx/5xx) so clients see the real status
        latency_ms = (time.time() - start_time) * 1000
        await audit_logger.log_chat_response(
            request_id=http_request.state.request_id,
            user_id=auth_context.username,
            model=request.model,
            status="error",
            latency_ms=latency_ms,
            tokens_used=0,
            response_preview=None,
            metadata={"error": he.detail}
        )
        raise he
    except Exception as e:
        # Log failure and return an internal server error
        latency_ms = (time.time() - start_time) * 1000
        await audit_logger.log_chat_response(
            request_id=http_request.state.request_id,
            user_id=auth_context.username,
            model=request.model,
            status="error",
            latency_ms=latency_ms,
            tokens_used=0,
            response_preview=None,
            metadata={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/health", response_model=HealthResponse)
async def health_check(rate_limiter: RateLimiter = Depends(get_rate_limiter)):
    """
    Health check endpoint
    """
    settings = get_settings()
    redis_status = "unknown"

    try:
        redis_client = await rate_limiter.get_redis()
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    return HealthResponse(
        status="healthy" if redis_status == "connected" else "unhealthy",
        redis_status=redis_status,
        version=settings.APP_VERSION,
        uptime_seconds=int(time.time() - settings.START_TIME)
    )

@router.get("/rate-limit")
async def get_rate_limit_status(
    auth_context: AuthContext = Depends(get_auth_context),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    models_config: ModelConfig = Depends(get_model_config)
):
    """
    Get current rate limit status for the authenticated user
    """
    rate_limit = models_config.get_rate_limits(auth_context.groups[0] if auth_context.groups else "default")
    # rate_limit is an integer representing the limit
    rate_status = await rate_limiter.get_rate_limit_status(
        auth_context, 
        'default',
        rate_limit if isinstance(rate_limit, int) else rate_limit.get('limit', 100)
    )
    return {
        "user_id": auth_context.username,
        "current_count": rate_status.get('used', 0),
        "limit": rate_status.get('limit', rate_limit if isinstance(rate_limit, int) else 100),
        "reset_at": rate_status.get('reset'),
        "window_seconds": 3600
    }
    