import os
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock, AsyncMock
from app.auth.dependencies import get_current_user, require_role
from app.db import User


@pytest.fixture(autouse=True)
def _enforce_auth():
    # get_current_user short-circuits to a dummy system user when auth is not
    # enforced; these tests exercise the real header/JWT path, so force it on.
    prev = os.environ.get("AUTH_ENFORCED")
    os.environ["AUTH_ENFORCED"] = "true"
    yield
    if prev is None:
        os.environ.pop("AUTH_ENFORCED", None)
    else:
        os.environ["AUTH_ENFORCED"] = prev


@pytest.mark.asyncio
async def test_get_current_user_no_bearer():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=MagicMock(), authorization="InvalidToken", db=MagicMock())
    assert exc_info.value.status_code == 401
    assert "Invalid authorization header format" in exc_info.value.detail

@pytest.mark.asyncio
@patch("app.auth.dependencies.verify_jwt")
async def test_get_current_user_success(mock_verify_jwt):
    mock_verify_jwt.return_value = {"sub": "user_123"}
    
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_user = User(clerk_user_id="user_123", email="test@example.com")
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await get_current_user(request=MagicMock(), authorization="Bearer validtoken", db=mock_db)
    
    assert user.clerk_user_id == "user_123"
    assert user.email == "test@example.com"
    mock_verify_jwt.assert_called_once_with("validtoken")

@pytest.mark.asyncio
@patch("app.auth.dependencies.verify_jwt")
async def test_get_current_user_not_found(mock_verify_jwt):
    mock_verify_jwt.return_value = {"sub": "user_404"}
    
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=MagicMock(), authorization="Bearer validtoken", db=mock_db)
    
    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_require_role_admin():
    admin_user = User(role="admin")
    standard_user = User(role="standard")
    
    checker = require_role("admin")
    
    # Admin passes
    result = await checker(user=admin_user)
    assert result == admin_user
    
    # Standard fails
    with pytest.raises(HTTPException) as exc_info:
        await checker(user=standard_user)
    assert exc_info.value.status_code == 403
    assert "Insufficient permissions" in exc_info.value.detail
