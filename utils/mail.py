from fastapi_mail import FastMail
from config import mail_conf

fm = FastMail(mail_conf)
