from passlib.context import CryptContext
from fastapi_mail import ConnectionConfig
import secret

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto",)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PRODUCTION = True
PASSWORD_RESET_TOKEN_TTL_MINUTES = 60


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
