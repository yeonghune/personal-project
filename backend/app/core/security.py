from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


# JWT(JSON Web Token) 액세스 토큰을 생성하는 함수
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    # 만료 시간
    expire = datetime.now(timezone.utc) + expires_delta
    # payload 생성
    # payload는 JWT 토큰의 핵심 데이터 부분으로, 실제 전소하고자 하는 정보를 담고 있는 부분
    to_encode = {"exp": expire, "sub": str(subject)}
    # payload를 SECRET_KEY로 서명하여 JWT 객체로 인코딩
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # pwd_context.verify: 검증
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # pwd_context.hash: 평문을 해싱
    return pwd_context.hash(password)
