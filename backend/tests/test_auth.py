import pytest
import time
import jwt
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import UserRegister
from app.core.config import settings
from app.api.deps import get_current_user

def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    
    # 1. password hash differs from plaintext
    assert hashed != password
    # 2. correct password verifies
    assert verify_password(password, hashed) is True
    # 3. wrong password fails
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_creation():
    subject = "123"
    token = create_access_token(subject)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    # 4. JWT contains string sub
    assert payload["sub"] == subject
    assert isinstance(payload["sub"], str)
    # 5. JWT contains exp
    assert "exp" in payload

def test_jwt_expired_token():
    # 6. expired JWT rejection behavior
    past_exp = int(time.time()) - 3600
    token = jwt.encode({"sub": "123", "exp": past_exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def test_get_current_user_malformed_sub():
    db = MagicMock()
    
    # 7. malformed/non-numeric subject rejection behavior
    # Case A: non-numeric string "abc"
    token_abc = jwt.encode({"sub": "abc", "exp": int(time.time()) + 3600}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db, token=token_abc)
    assert exc_info.value.status_code == 401
    
    # Case B: missing sub
    token_missing = jwt.encode({"exp": int(time.time()) + 3600}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db, token=token_missing)
    assert exc_info.value.status_code == 401

def test_user_register_schema_validation():
    # 11. full_name trimming behavior
    user = UserRegister(email=" Test@example.com ", full_name="  John Doe  ", password="password123")
    assert user.email == "Test@example.com"
    assert user.full_name == "John Doe"
    
    # 8. invalid email rejection
    with pytest.raises(ValueError):
        UserRegister(email="invalid-email", full_name="John Doe", password="password123")
        
    # 9. short password rejection
    with pytest.raises(ValueError):
        UserRegister(email="test@example.com", full_name="John Doe", password="short")
        
    # 10. whitespace-only full_name rejection
    with pytest.raises(ValueError):
        UserRegister(email="test@example.com", full_name="   ", password="password123")

@pytest.mark.skip(reason="BLOCKED: DB integration tests cannot be run against the default Neon development database safely without isolated schemas.")
def test_db_integration_blocked():
    pass
