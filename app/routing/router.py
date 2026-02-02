import httpx
import structlog
import hashlib


def _mask_key(key: str) -> str:
    """Return a masked version of a secret keeping only last 4 chars visible.

    Example: 'sk-xxxxx-1234' -> '****1234'
    If key is shorter than 8 chars, mask all but last 2.
    """
    if not key:
        return ""
    try:
        k = str(key)
        if len(k) <= 6:
            visible = 2
        else:
            visible = 4
        return "*" * (len(k) - visible) + k[-visible:]
    except Exception:
        return "****"
from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any
import time
import json

from app.routing.models import ChatCompletionRequest, ChatCompletionResponse
from app.config import get_model_config
from app.auth.models import AuthContext

logger = structlog.get_logger("model_router")

class ModelRouter:
    """Route requests to appropriate models AI based on user permissions"""

    def __init__(self):
        self.model_config = get_model_config()
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP or create HTTP client instance"""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0, verify=False)
        return self._http_client

    def check_access(self, auth_context: AuthContext, model_name: str) -> bool:
        """Check if user has access to the requested model"""
        access_control = self.model_config.get_access_control(model_name)
        # If no access_control is defined for the model, allow by default
        if not access_control:
            return True

        # If the user explicitly has the model in their allowed models, permit it
        if getattr(auth_context, "models", None) and model_name in auth_context.models:
            return True

        # Normalize roles and groups comparison to be case-insensitive
        user_roles = {r.lower() for r in (auth_context.roles or [])}
        user_groups = {g.lower() for g in (auth_context.groups or [])}

        required_roles = [r.lower() for r in access_control.get("roles", [])]
        if required_roles:
            # If roles are required, user must have at least one of them
            if not any(r in user_roles for r in required_roles):
                return False

        required_groups = [g.lower() for g in access_control.get("groups", [])]
        if required_groups:
            # If groups are required, user must be in at least one
            if not any(g in user_groups for g in required_groups):
                return False

        return True
    
    async def route_request(
            self,
            request: ChatCompletionRequest,
            auth_context: AuthContext
    ) -> ChatCompletionResponse:
        """
        Route chat completion request to appropriate model
        
        Args:
            request: ChatCompletionRequest object
            auth_context: AuthContext object with user info

        Returns:
            ChatCompletionResponse object

        Raises:
            HTTPException: If access is forbidden or model not found
        
        """
        model_name = request.model

        model_config = self.model_config.get_model_config(model_name)
        if not model_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found"
            )
        if not self.check_access(auth_context, model_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to model '{model_name}' is forbidden"
            )
        endpoint = model_config.get("endpoint")
        api_key = model_config.get("api_key")

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model '{model_name}' endpoint not configured"
            )
        
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            auth_header = model_config.get("auth_header", "Authorization")
            auth_prefix = model_config.get("auth_prefix", "") or ""
            # Normalize prefix formatting: ensure a single space between prefix and key
            if auth_prefix:
                if auth_prefix.endswith(" "):
                    header_value = f"{auth_prefix}{api_key}"
                else:
                    header_value = f"{auth_prefix} {api_key}"
            else:
                header_value = api_key
            # Always overwrite Authorization (do not forward incoming JWT)
            headers[auth_header] = header_value
            # Log which API key was used (source may be set in model_config by endpoints)
            try:
                source = model_config.get("api_key_source") if isinstance(model_config, dict) else None
            except Exception:
                source = None
            # For safety do NOT log the full secret. Log a masked version and a short hash prefix
            try:
                api_key_str = str(api_key)
                api_key_masked = _mask_key(api_key_str)
                api_key_hash_prefix = hashlib.sha256(api_key_str.encode()).hexdigest()[:8]
            except Exception:
                api_key_masked = ""
                api_key_hash_prefix = ""

            logger.info(
                "upstream_api_key_used",
                model=model_name,
                auth_header=auth_header,
                source=source or "unknown",
                api_key_mask=api_key_masked,
                api_key_hash_prefix=api_key_hash_prefix,
            )

        try:
            client = await self.get_http_client()
            request_payload = request.model_dump(exclude_none=True)

            # Remove any Authorization-like headers before logging to avoid leaking JWTs
            headers_for_log = dict(headers)
            try:
                # Remove the configured auth header (case-sensitive as set earlier) if present
                if auth_header in headers_for_log:
                    headers_for_log.pop(auth_header, None)
                # Also defensively remove standard Authorization header if present
                headers_for_log.pop("Authorization", None)
            except Exception:
                pass

            logger.info("routing_request", model=model_name, endpoint=endpoint)
            logger.debug("request_payload", payload=request_payload)
            logger.info("request_headers", headers=headers_for_log)
            response = await client.post(
                endpoint,
                json=request_payload,
                headers=headers
            )
            logger.info("response_status", status_code=response.status_code)
            # response.text may be large; debug-level it
            logger.debug("response_body", body=response.text)
            response.raise_for_status()
            response_data = response.json()
            # Normalize usage fields: ChatCompletionResponse expects usage values to be integers.
            try:
                usage = response_data.get("usage") or {}
                # Extract canonical integer fields if present, fallback to 0
                prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                completion_tokens = int(usage.get("completion_tokens", 0) or 0)
                total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens))
                response_data["usage"] = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                }
            except Exception:
                # If anything goes wrong, ensure usage is either None or minimal ints
                response_data["usage"] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }

            return ChatCompletionResponse(**response_data)
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", str(e))
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=error_message
                )
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=str(e)
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()


_router: ModelRouter = None

def _get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router