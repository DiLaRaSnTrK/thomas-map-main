import os
import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-degistir-lutfen")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

# Session'lar 8 saat sonra otomatik geçersiz olur
SESSION_MAX_AGE = 60 * 60 * 8

serializer = URLSafeTimedSerializer(SECRET_KEY)


def verify_password(plain: str, hashed: str) -> bool:
    """Girilen şifreyi hash ile karşılaştırır."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> bool:
    """Kullanıcı adı ve şifreyi doğrular."""
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, ADMIN_PASSWORD_HASH)


def create_session(username: str) -> str:
    """İmzalı ve süreli session token üretir."""
    return serializer.dumps({"username": username}, salt="session")


def verify_session(token: str):
    """Token geçerliyse kullanıcı adını döner, değilse None."""
    try:
        data = serializer.loads(token, salt="session", max_age=SESSION_MAX_AGE)
        return data.get("username")
    except (BadSignature, SignatureExpired):
        return None


async def check_login(request: Request):
    """
    Dependency: Oturum açık değilse giriş sayfasına yönlendirir.
    Admin ve Excel endpoint'lerinde kullanılır.
    """
    token = request.cookies.get("session_token")
    user = verify_session(token) if token else None
    if not user:
        return RedirectResponse(url="/yonetim-giris", status_code=302)
    return user
