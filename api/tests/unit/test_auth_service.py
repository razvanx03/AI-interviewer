import datetime
import pytest
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)


class TestAuthAndSecurity:
    """Unit tests for hashing, JWT token creation, verification, and expiration."""

    def test_password_hashing_and_verification(self):
        password = "SecurePassword2026!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_create_and_decode_access_token(self):
        payload = {"sub": "usr_12345", "email": "test@example.com", "role": "admin"}
        token = create_access_token(payload)

        assert isinstance(token, str)
        assert len(token) > 20

        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "usr_12345"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_expired_access_token(self):
        payload = {"sub": "usr_12345"}
        # Create token that expired 1 minute ago
        expired_delta = datetime.timedelta(minutes=-1)
        token = create_access_token(payload, expires_delta=expired_delta)

        decoded = decode_access_token(token)
        assert decoded is None

    def test_decode_invalid_token(self):
        assert decode_access_token("invalid.token.string") is None
        assert decode_access_token("") is None
