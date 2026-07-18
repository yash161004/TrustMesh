from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_org_id(request: Request) -> str:
    """
    Extract the org_id from the authenticated user to use as the rate limit key.
    If the user is not authenticated (e.g. some public endpoint), fall back to IP address.
    """
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user.org_id
    return get_remote_address(request)

# [KNOWN LIMITATION] MemoryStorage works correctly ONLY with a single process/worker.
# If TrustMesh is deployed with multiple workers or horizontally scaled across nodes, 
# these limits will silently multiply (each worker maintains its own bucket).
# Before moving to a multi-worker deployment (Phase 6), this must be swapped 
# to a distributed backend like Redis (e.g., limits.storage.RedisStorage).
limiter = Limiter(key_func=get_org_id, headers_enabled=False)
