import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional

# WARNING: FOR LOCAL DEVELOPMENT ONLY
# Production must use an enterprise IdP (e.g., SAML, OAuth2, Active Directory)
SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("JWT_SECRET_KEY", "dummy-dev-secret-key-never-use-in-prod"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# "password123" hashed
DUMMY_PASSWORD_HASH = "$2b$12$rqsGRqHDC6QKTRWCiRtSbeHajAhm36vLdpYWq0Gm1B9foKz5W6kzm" 

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
