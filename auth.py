"""
auth.py
- Authentication helpers using pwdlib (bcrypt replacement)
- JWT issuance and verification
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pwdlib import PasswordHash
import jwt

load_dotenv()

# --- JWT設定 ---
SECRET_KEY = os.getenv("SECRET_KEY", "change_this")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))

# --- pwdlib設定 ---
pwd_context = PasswordHash.recommended()  # 自動で最適なハッシュアルゴリズム（bcrypt, argon2など）を選択


# --- パスワードのハッシュ化 ---
def hash_password(plain: str) -> str:
    """平文パスワードを安全にハッシュ化する"""
    return pwd_context.hash(plain)


# --- パスワード検証 ---
def verify_password(plain: str, hashed: str) -> bool:
    """入力パスワードとハッシュが一致するか検証"""
    return pwd_context.verify(plain, hashed)


# --- JWTトークン生成 ---
# auth.py
def create_access_token(data: dict, expires_delta: int = EXPIRE_MINUTES) -> str:
    """JWT作成"""
    to_encode = data.copy()  # これで辞書のコピーになる
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token



# --- JWTトークン検証 ---
def verify_token(token: str):
    """JWTをデコードして有効性を確認"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
