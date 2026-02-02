"""
JWT token handling and validation
"""
from jose import jwt, JWTError
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException, status
from functools import lru_cache
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
import base64

from app.auth.models import TokenClaims, AuthContext
from app.config import get_settings



class JWTHandler:
    """JWT token handler for validation - supports both Azure AD and local HS256 tokens for testing"""
    
    def __init__(self):
        self.settings = get_settings()
        self._jwks_cache = None
        self._jwks_cache_time = 0
        self._jwks_cache_ttl = 3600  # 1 hour TTL

    def _is_local_token(self, token: str) -> bool:
        """Check if token is a local HS256 token (for testing)"""
        try:
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get("alg", "")
            return algorithm == "HS256"
        except:
            return False

    async def _fetch_jwks(self) -> dict:
        """Get JSON Web Key Set (JWKS) from Azure AD with caching"""
        current_time = time.time()

        if self._jwks_cache and (current_time - self._jwks_cache_time) < self._jwks_cache_ttl:
            return self._jwks_cache

        jwks_url = f"https://login.microsoftonline.com/{self.settings.tenant_id}/discovery/v2.0/keys"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = current_time
            return self._jwks_cache
        
    def get_signing_key(self, token: str, jwks: dict) -> Optional[str]:
        """Get the signing key from JWKS matching the token's kid"""
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                return None

            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    x5c = key.get("x5c")
                    if x5c:
                        cert_str = "-----BEGIN CERTIFICATE-----\n" + x5c[0] + "\n-----END CERTIFICATE-----"
                        cert = load_pem_x509_certificate(cert_str.encode(), default_backend())
                        public_key = cert.public_key()
                        pem = public_key.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        return pem.decode('utf-8')
            return None
        except JWTError:
            return None
        
    async def validate_token(self, token: str) -> TokenClaims:
        """Validate JWT token and return claims"""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            # Check if this is a local HS256 token (for testing)
            if self._is_local_token(token):
                payload = jwt.decode(
                    token,
                    self.settings.jwt_secret_key,
                    algorithms=["HS256"],
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                    }
                )
                claims = TokenClaims(**payload)
                return claims

            # Otherwise, validate as Azure AD token (RS256)
            jwks = await self._fetch_jwks()
            signing_key = self.get_signing_key(token, jwks)

            if not signing_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: signing key not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                }
            )
            claims = TokenClaims(**payload)
            return claims
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTClaimsError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token claims: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation error: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error during token validation: {str(e)}",
            )
    
    async def get_auth_context(self, token: str) -> AuthContext:
        """Get AuthContext from JWT token"""
        claims = await self.validate_token(token)
        return AuthContext.from_claims(claims, token)
    
@lru_cache()
def get_jwt_handler() -> JWTHandler:
    """Get cached JWTHandler instance"""
    return JWTHandler()