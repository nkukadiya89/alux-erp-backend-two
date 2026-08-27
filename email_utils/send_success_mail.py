import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string

from user.models import User


def send_confirm_mail(subject, template, data):
    context = {"name": data["name"], "email": data["email"]}

    html_body = render_to_string(template, context)
    recipient_email = data["email"]

    msg = MIMEMultipart()
    msg["From"] = "ALUX-Erp <" + config("ADMIN_EMAIL") + ">"  # type: ignore
    msg["To"] = recipient_email
    msg["Subject"] = subject

    part2 = MIMEText(html_body, "html")
    msg.attach(part2)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    url = os.path.join(BASE_DIR, "static/images/alux_logo.png")
    with open(url, "rb") as image_file:
        img_data = image_file.read()
    msImage = MIMEImage(img_data)
    msImage.add_header("Content-ID", "<image1>")
    msg.attach(msImage)

    if template == "password-changed-confirmation.html":
        # Attach additional image if needed
        url = os.path.join(BASE_DIR, "static/images/alux_logo.png")
        img_data1 = open(url, "rb").read()
        msImage1 = MIMEImage(img_data1)
        msImage1.add_header("Content-ID", "<image2>")

    try:
        mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        mail_server.ehlo()
        mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))  # type: ignore
        mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"], msg.as_string())  # type: ignore
        mail_server.quit()
        return HttpResponse("Mail Sent", status=200)
    except Exception as e:
        return HttpResponse(f"Mail could not be sent: {str(e)}", status=500)


def send_success_mail(subject, template, data):
    name = data.get("name", "")
    email = data.get("email", "")
    company = data.get("company", "")
    vendor = data.get("vendor", "")
    employee = data.get("employee", "")

    user = User.objects.filter(email=email).first()

    context = {
        "name": name,
        "email": user.email,  # type: ignore
        "company": company,
        "vendor": vendor,
        "employee": employee,
    }

    html_body = render_to_string(template, context)
    recipient_email = data["email"]
    super_admin_email = config("INIT_EMAIL")

    to_emails = [
        super_admin_email,
        recipient_email,
    ]
    to_emails = [email for email in to_emails if email is not None]

    msg = MIMEMultipart()
    msg["From"] = "ALUX_Erp <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    part2 = MIMEText(html_body, "html")
    msg.attach(part2)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    url = os.path.join(BASE_DIR, "static/images/alux_logo.png")
    with open(url, "rb") as image_file:
        img_data = image_file.read()
    msImage = MIMEImage(img_data)
    msImage.add_header("Content-ID", "<image1>")
    msg.attach(msImage)

    if template == "register-success.html":
        # Attach additional image if needed
        url = os.path.join(BASE_DIR, "static/images/checked.png")
        img_data1 = open(url, "rb").read()
        msImage1 = MIMEImage(img_data1)
        msImage1.add_header("Content-ID", "<image2>")

    try:
        mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        mail_server.ehlo()
        mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))  # type: ignore

        mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"].split(", "), msg.as_string())  # type: ignore

        mail_server.quit()

        return HttpResponse("Mail Sent", status=200)

    except Exception as e:
        return HttpResponse(f"Mail could not be sent: {str(e)}", status=500)
