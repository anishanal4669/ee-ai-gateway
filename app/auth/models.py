"""
Gateway request permissions and RBAC
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TokenClaims(BaseModel):
    """Token claims structure"""
    sub: str
    oid: Optional[str] = None
    preferred_username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    scp: Optional[str] = None
    aud: Optional[str] = None  # Made optional for test tokens
    iss: Optional[str] = None  # Made optional for test tokens
    exp: int
    iat: int
    nbf: Optional[int] = None

    # Custom Claims
    organization: Optional[str] = None
    organization_id: Optional[str] = None
    organization_user_id: Optional[str] = None
    # Additional custom claims that may be present in test tokens
    models: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    lob: Optional[str] = None
    rate_limit: Optional[int] = None
    
    @property
    def user_id(self) -> str:
        """Get user ID from token claims"""
        return self.oid or self.sub
    
    @property
    def username(self) -> Optional[str]:
        """Get username from token claims"""
        return self.preferred_username or self.email or self.user_id
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        now = datetime.utcnow().timestamp()
        return now >= self.exp
    
class AuthContext(BaseModel):
    """Authentication context for requests"""
    claims: TokenClaims
    token: str
    user_id: str
    username: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    groups: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    lob: Optional[str] = None
    rate_limit: int = 100

    @classmethod
    def from_claims(cls, claims: TokenClaims, token: str) -> "AuthContext":
        """Create AuthContext from TokenClaims"""
        # Extract additional fields from claims if they exist
        additional_data = claims.dict()
        
        return cls(
            claims=claims,
            token=token,
            user_id=claims.user_id,
            username=claims.username,
            roles=claims.roles,
            groups=claims.groups,
            permissions=additional_data.get('permissions', []),
            models=additional_data.get('models', []),
            lob=additional_data.get('lob'),
            rate_limit=additional_data.get('rate_limit', 100)
        )
