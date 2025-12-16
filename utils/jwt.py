from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from decouple import config
import google.auth.transport.requests
from google.oauth2 import id_token
import logging
import bcrypt

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = config("SECRET_KEY", default="your_secret_key_here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# Simpler password hashing setup
def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    try:
        # Convert to bytes if it's a string
        password_bytes = password.encode('utf-8')
        # Truncate to 72 bytes if necessary
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise ValueError(f"Password hashing error: {str(e)}")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against a provided password."""
    try:
        # Convert to bytes
        plain_password_bytes = plain_password.encode('utf-8')
        # Truncate to 72 bytes if necessary
        if len(plain_password_bytes) > 72:
            plain_password_bytes = plain_password_bytes[:72]
            
        # Convert stored hash to bytes if it's not already
        if isinstance(hashed_password, str):
            hashed_password_bytes = hashed_password.encode('utf-8')
        else:
            hashed_password_bytes = hashed_password
            
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_google_token(token: str):
    try:
        CLIENT_ID = config("GOOGLE_CLIENT_ID", default="")
        request = google.auth.transport.requests.Request()
        id_info = id_token.verify_oauth2_token(token, request, CLIENT_ID)
        
        if id_info["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer"
            )
            
        return id_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )