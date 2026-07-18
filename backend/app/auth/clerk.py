"""
TrustMesh Auth Utility — Phase 0
Clerk JWT verification utility using cached JWKS.
"""
import jwt
from typing import Dict, Any, Optional
from app.config import get_settings

# Cache the JWK client globally so it reuses the fetched keys
_jwk_client: Optional[jwt.PyJWKClient] = None

def _get_jwk_client() -> jwt.PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        settings = get_settings()
        if not settings.clerk_jwks_url:
            raise ValueError("CLERK_JWKS_URL is not configured.")
        _jwk_client = jwt.PyJWKClient(
            settings.clerk_jwks_url, 
            cache_keys=True, 
            cache_jwk_set=True
        )
    return _jwk_client

def verify_jwt(token: str) -> Dict[str, Any]:
    """
    Validates a Clerk JWT signature against the cached JWKS.
    Validates standard claims (exp, iss).
    Returns decoded claims dict on success.
    Raises ValueError on any validation failure.
    """
    settings = get_settings()
    if not token:
        raise ValueError("Token is missing")

    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Determine options based on available config
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": bool(settings.clerk_issuer),
            "verify_aud": False,  # We can tighten this later if Clerk provides aud
        }

        # Verify the token
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer if settings.clerk_issuer else None,
            options=options
        )
        return decoded
    except jwt.PyJWTError as e:
        raise ValueError(f"JWT validation failed: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Unexpected error during JWT validation: {str(e)}") from e
