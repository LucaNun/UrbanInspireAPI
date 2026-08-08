from passlib.context import CryptContext
from fastapi_mail import ConnectionConfig
from datetime import datetime
import secret

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto",)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PRODUCTION = True
MIN_VERSION = "1.0.2"
MAINTENANCE_MODE = False
MAINTENANCE_MESSAGE = "The API is currently undergoing maintenance. Please try again later."
MAINTENANCE_RETRY_AFTER = 300
MAINTENANCE_END = None  # optional datetime.datetime, e.g. datetime(2026, 8, 8, 14, 30)
PASSWORD_RESET_TOKEN_TTL_MINUTES = 60

API_DOMAIN = "https://urban.sbln.dev"


mail_conf = ConnectionConfig(
    MAIL_USERNAME = secret.MAIL_USERNAME,
    MAIL_PASSWORD = secret.MAIL_PASSWORD,
    MAIL_FROM = secret.MAIL_FROM,
    MAIL_PORT = secret.MAIL_PORT,
    MAIL_SERVER = secret.MAIL_SERVER,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
    #TEMPLATE_FOLDER = Path(file).parent / 'templates',

    # if no indicated SUPPRESS_SEND defaults to 0 (false) as below
    # SUPPRESS_SEND=1
)
