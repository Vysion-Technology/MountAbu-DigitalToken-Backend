from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from jose import jwt, JWTError

from backend.config import settings


def decrypt_credentials(encrypted_text: str) -> str:
    """
    Decrypt credentials encrypted with AES-256-CBC.
    Expects base64 encoded string containing IV + Ciphertext.
    The key is retrieved from settings.CREDENTIALS_SECRET_KEY (must be 32 bytes).
    """
    if not settings.CREDENTIALS_SECRET_KEY:
        # Fallback for development if key is not set, return as is or handle error
        return encrypted_text

    try:
        # Decode base64
        encrypted_data = base64.b64decode(encrypted_text)
        
        # AES-256-CBC uses 16 byte IV
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Key must be 32 bytes for AES-256
        key = settings.CREDENTIALS_SECRET_KEY.encode("utf-8")
        if len(key) != 32:
            raise ValueError("CREDENTIALS_SECRET_KEY must be exactly 32 bytes")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_plain_text = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        plain_text = unpadder.update(padded_plain_text) + unpadder.finalize()
        
        return plain_text.decode("utf-8")
    except Exception as e:
        print(f"Decryption error: {e}")
        # In production, you'd likely want to raise a 400 error via FastAPI
        return encrypted_text


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a long-lived refresh token (90 days by default)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_tokens(user_id: int, role: str) -> Tuple[str, str]:
    """Create both access and refresh tokens for a user."""
    token_data = {"sub": str(user_id), "role": role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return access_token, refresh_token


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
