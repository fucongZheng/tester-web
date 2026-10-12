"""鉴权：密码哈希 + JWT + 登录密码 RSA 解密"""
import base64
from datetime import datetime, timedelta

import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# 登录传输加密用密钥对：进程启动时生成，重启换钥（前端每次进登录页都重新拉公钥，无影响）
_rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def public_key_pem() -> str:
    return _rsa_private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def rsa_decrypt(b64_ciphertext) -> str | None:
    """解密前端 RSA(PKCS1v15) 加密的密码，失败返回 None。"""
    try:
        raw = base64.b64decode(b64_ciphertext or "")
        return _rsa_private.decrypt(raw, padding.PKCS1v15()).decode("utf-8")
    except Exception:
        return None


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None
