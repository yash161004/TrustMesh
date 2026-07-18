import pytest
from unittest.mock import patch, MagicMock
from app.auth.clerk import verify_jwt

@pytest.fixture
def mock_settings():
    with patch("app.auth.clerk.get_settings") as mock:
        settings = MagicMock()
        settings.clerk_jwks_url = "https://clerk.example.com/.well-known/jwks.json"
        settings.clerk_issuer = "https://clerk.example.com"
        mock.return_value = settings
        yield mock

@pytest.fixture
def mock_jwk_client():
    with patch("app.auth.clerk.jwt.PyJWKClient") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance

def test_verify_jwt_valid_token(mock_settings, mock_jwk_client):
    """
    Test that a valid JWT token returns the decoded claims.
    TODO: Replace with actual Clerk test tokens.
    """
    # Mock the signing key and decode output
    mock_jwk_client.get_signing_key_from_jwt.return_value = MagicMock(key="mock_key")
    
    with patch("app.auth.clerk.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user_123", "iss": "https://clerk.example.com"}
        
        claims = verify_jwt("mock.valid.token")
        
        assert claims["sub"] == "user_123"
        mock_decode.assert_called_once()

def test_verify_jwt_expired_token(mock_settings, mock_jwk_client):
    """
    Test that an expired token raises ValueError.
    TODO: Replace with actual Clerk test tokens.
    """
    mock_jwk_client.get_signing_key_from_jwt.return_value = MagicMock(key="mock_key")
    
    from jwt.exceptions import ExpiredSignatureError
    with patch("app.auth.clerk.jwt.decode") as mock_decode:
        mock_decode.side_effect = ExpiredSignatureError("Signature has expired")
        
        with pytest.raises(ValueError, match="JWT validation failed"):
            verify_jwt("mock.expired.token")

def test_verify_jwt_bad_signature(mock_settings, mock_jwk_client):
    """
    Test that a token with a bad signature raises ValueError.
    TODO: Replace with actual Clerk test tokens.
    """
    mock_jwk_client.get_signing_key_from_jwt.return_value = MagicMock(key="mock_key")
    
    from jwt.exceptions import InvalidSignatureError
    with patch("app.auth.clerk.jwt.decode") as mock_decode:
        mock_decode.side_effect = InvalidSignatureError("Signature verification failed")
        
        with pytest.raises(ValueError, match="JWT validation failed"):
            verify_jwt("mock.bad_sig.token")

def test_verify_jwt_missing_token():
    """
    Test that an empty or missing token raises ValueError.
    """
    with pytest.raises(ValueError, match="Token is missing"):
        verify_jwt("")
