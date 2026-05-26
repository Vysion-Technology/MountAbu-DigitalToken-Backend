from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto import Random
from jose import jwt, JWTError
from fastapi import HTTPException

from backend.config import settings

# RSA Key Management
_private_key = None
_public_key_pem = None

def get_rsa_public_key() -> str:
    """Returns the public key in PEM format."""
    global _private_key, _public_key_pem
    if _public_key_pem is None:
        # In a real production app, you might load these from a file or env
        # For now, we generate them on startup if not present
        random_generator = Random.new().read
        _private_key = RSA.generate(2048, random_generator)
        _public_key_pem = _private_key.publickey().export_key().decode("utf-8")
    return _public_key_pem

def decrypt_credentials(encrypted_text: str) -> str:
    """
    Decrypt credentials encrypted with RSA Public Key.
    Expects base64 encoded ciphertext.
    """
    global _private_key
    if _private_key is None:
        get_rsa_public_key() # Ensure keys are generated

    try:
        # Decode base64
        ciphertext = base64.b64decode(encrypted_text)
        
        # Decrypt using PKCS1_v1_5
        sentinel = Random.new().read(16)
        cipher = PKCS1_v1_5.new(_private_key)
        plain_text = cipher.decrypt(ciphertext, sentinel)
        
        if plain_text == sentinel:
            raise ValueError("RSA Decryption failed")
            
        return plain_text.decode("utf-8")
    except Exception as e:
        if settings.ENFORCE_RSA_ENCRYPTION:
            print(f"Decryption error (Enforced): {e}")
            raise ValueError("Invalid encrypted credentials format")
        
        # If not enforced, fallback to plain text (development mode)
        return encrypted_text

def decrypt_and_verify_payload(encrypted_text: str) -> Tuple[str, Optional[str]]:
    """
    Decrypts RSA payload and verifies timestamp expiry (30 seconds).
    Returns (value, nonce).
    """
    decrypted_text = decrypt_credentials(encrypted_text)
    
    try:
        data = json.loads(decrypted_text)
        if isinstance(data, dict):
            value = data.get("value")
            nonce = data.get("nonce")
            timestamp = data.get("timestamp")
            
            if timestamp:
                # Handle both ms and s
                if timestamp > 1e11: # Likely milliseconds (e.g., Date.now() in JS)
                    timestamp = timestamp / 1000.0
                
                now = datetime.utcnow().timestamp()
                if abs(now - timestamp) > 30:
                    raise HTTPException(
                        status_code=401, 
                        detail="Request expired or clock out of sync. Please try again."
                    )
            
            # If value is present, return it. Otherwise, return the whole JSON as string (fallback)
            return value if value is not None else decrypted_text, nonce
    except (json.JSONDecodeError, TypeError):
        pass
    
    return decrypted_text, None


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


def create_tokens(user_id: int, role: str, token_version: int = 1, nonce: Optional[str] = None) -> Tuple[str, str]:
    """Create both access and refresh tokens for a user."""
    token_data = {"sub": str(user_id), "role": role, "version": token_version}
    if nonce:
        token_data["nonce"] = nonce
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
