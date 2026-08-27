import copy
import json
from typing import Union

import requests
from decouple import config


def cleaned_payload(d):
    if not isinstance(d, dict):
        return d
    return {
        k: cleaned_payload(v)
        for k, v in d.items()
        if v is not None and (not isinstance(v, dict) or cleaned_payload(v))
    }


def extract_message_from_response(response):
    # Helper function to extract the 'message' from the response content.
    try:
        res_content = json.loads(response.content.decode("utf-8"))
        return res_content.get("message", "")
    except (json.JSONDecodeError, AttributeError):
        return response.content


# wp_message_failed_email_id = config("WHATSAPP_MESSAGE_FAILED_EMAIL")


class WhatsappMessages:
    _base_url = (
        f"https://msgbot.io/api/{config('META_VENDOR_ID')}/"
        "contact/send-template-message"
    )
    _headers = {
        "Authorization": f"Bearer {config('META_WHATSAPP_TOKEN')}",
        "Content-Type": "application/json",
    }
    _template_list = [
        "rfq_approval",
        "employee_deactivated",
        "password_change_successfull",
        "register_success",
        "reset_password",
        "login_with_otp",
        "approve_rfq",
        "approved_rfq",
        "rfq_email_vendor",
        "bid_rfq",
    ]

    _initialised = None

    _payload = {
        "phone_number": None,
        "template_name": None,
        "template_language": "en",
        "field_1": "Nirav",
        "field_2": None,
        "field_3": None,
        "field_4": None,
        "field_5": None,
        "field_6": None,
        "field_7": None,
        "field_8": None,
        "button_0": None,
        "button_1": None,
        "copy_code": None,
        "contact": {
            "first_name": None,
            "last_name": None,
            "email": None,
            "country": None,
            "language_code": None,
        },
    }

    def __init__(
        self,
        template_name: str,
        contact: str,
        first_name: Union[None, str] = None,
        last_name: Union[None, str] = None,
        email: Union[None, str] = None,
        country: Union[None, str] = None,
    ) -> None:

        if template_name not in self._template_list:
            template_name = ""

        if template_name and contact:
            self._first_name = first_name
            self._last_name = last_name
            self._email = email
            self._country = country
            self._payload.update(
                {
                    "phone_number": contact,
                    "template_name": template_name,
                    "template_language": "en",
                }
            )
            self._initialised = True
        else:
            self._initialised = False
            raise ValueError("Template name and contact is required")

    @staticmethod
    def find_empty_parameter(params: list):
        for index, param in enumerate(params):
            if param == "":
                return index
        return None

    def send_password_change_successfull(self, to: str):
        if not to:
            raise ValueError("to is required")

        payload = copy.deepcopy(self._payload)
        payload = payload.update({"field_1": to})
        payload = cleaned_payload(payload)
        res = requests.post(url=self._base_url, headers=self._headers, json=payload)
        if res.status_code == 200:
            return "Message Send successfully"
        else:
            return f"Message sending failed {res.content}"
