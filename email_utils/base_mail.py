import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string

from utils import auth_utils

admin_email = config("ADMIN_EMAIL")
email_password = config("EMAIL_PASSWORD")


def send_email(subject: str, template: str, data: dict, attachment_list: list = []):

    html_body = render_to_string(template, data)

    msg = MIMEMultipart()
    msg.set_unixfrom("author")
    msg["From"] = config("EMAIL_COMPANY_NAME") + "<" + config("ADMIN_EMAIL") + ">"  # type: ignore
    msg["To"] = data["email"]
    msg["Subject"] = subject
    part2 = MIMEText(html_body, "html")
    msg.attach(part2)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    url = os.path.join(BASE_DIR, "static/images/alux_logo.png")
    img_data = open(url, "rb").read()
    msImage = MIMEImage(img_data)
    msImage.add_header("Content-ID", "<image1>")
    msg.attach(msImage)

    img_cnt = 1
    for attachment in attachment_list:
        if attachment["type"] == "image":
            img_cnt += 1
            url = os.path.join(BASE_DIR, f"static/images/{attachment['file']}")
            img_data1 = open(url, "rb").read()
            msImage1 = MIMEImage(img_data1)
            msImage1.add_header("Content-ID", f"<image{img_cnt}>")
            msg.attach(msImage1)

    mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    mail_server.ehlo()

    mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))  # type: ignore

    mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"], msg.as_string())  # type: ignore

    mail_server.quit()
    return HttpResponse("Mail Send", status=200)


def new_user_registeration(user):
    try:
        subject = "New User Registration"
        template = "register-success.html"
        data = {}
        data["login_url"] = config("APP_URL") + "login"  # type: ignore
        data["verify_link"] = config("APP_URL") + "verify-success/"  # type: ignore
        data["token"] = auth_utils.generate_token(user.email, 30)
        data["name"] = user.first_name if user.first_name else "User"
        data["email"] = user.email

        send_email(subject=subject, template=template, data=data)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
