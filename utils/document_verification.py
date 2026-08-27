import json
import uuid

import requests
from decouple import config


class GovernmentDocVerification:
    _group_id = str(uuid.uuid4())

    _payload = {"task_id": str(uuid.uuid4()), "group_id": _group_id, "data": {}}
    _headers = {
        "api-key": config("GOVT_DOC_API_KEY"),
        "account-id": config("GOVT_DOC_ACCOUNT_ID"),
        "Content-Type": "application/json",
    }

    _url_list = {
        "request_data_url": "https://eve.idfy.com/v3/tasks?request_id=",
        "udhyam": "https://eve.idfy.com/v3/tasks/async/verify_with_source/udyam_aadhaar",
        "gstn": "https://eve.idfy.com/v3/tasks/async/verify_with_source/ind_gst_certificate",
        "pan": "https://eve.idfy.com/v3/tasks/async/verify_with_source/ind_pan",
    }

    # Udhyan Verification
    def verify_udhyam(self, uam_number: str) -> dict:
        URL = self._url_list["udhyam"]
        self._payload.update({"data": {"uam_number": uam_number}})

        try:
            response = requests.post(URL, headers=self._headers, json=self._payload)  # type: ignore

            res = json.loads(response.content)
            request_id = res.get("request_id", None)  # type: ignore

            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=self._headers)

                res = json.loads(response.content)
                verified_data = res[0].get("result", {}).get("source_output")
                data = {}
                data["company"] = verified_data.get("enterprise_name", "")
                data["major_activity"] = verified_data.get("major_activity", "")
                address = verified_data.get("unit_details", "")

                data["building"] = address[0].get("building", "")
                data["village"] = address[0].get("village", "")
                data["state"] = address[0].get("state", "")
                data["city"] = address[0].get("city", "")
                data["district"] = address[0].get("district", "")
                data["pin"] = address[0].get("pin", "")
                return data  # type: ignore
            else:
                return {"error": "Detail not found."}  # type: ignore
        except Exception:
            return {"error": "Verification failed"}

    # GSTN Verification
    def verify_gst(self, gst_no: str) -> dict:
        URL = self._url_list["gstn"]

        self._payload.update({"data": {"gstin": gst_no, "filing_status": True}})

        try:
            response = requests.post(URL, headers=self._headers, json=self._payload)  # type: ignore
            res = json.loads(response.content)
            request_id = res.get("request_id", None)  # type: ignore
            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=self._headers)

                res = json.loads(response.content)
                verified_data = res[0].get("result", {}).get("source_output")
                data = {}
                if verified_data.get("gstin_status").lower() == "active":
                    data["company"] = verified_data.get("trade_name", "")
                    data["legal_name"] = verified_data.get("legal_name", "")
                    address = verified_data.get(
                        "principal_place_of_business_fields", {}
                    ).get("principal_place_of_business_address")
                    data["building_name"] = address.get("building_name", "")
                    data["floor_number"] = address.get("floor_number", "")
                    data["door_name"] = address.get("door_number")
                    data["city"] = address.get("location", "")
                    data["pincode"] = address.get("pincode", "")
                    data["street"] = address.get("street", "")
                    data["status"] = verified_data.get("gstin_status", "")
                    data["state"] = verified_data.get("state_jurisdiction_code", "")
                    data["business_activity"] = verified_data.get(
                        "nature_of_business_activity", ""
                    )
                else:
                    data["error"] = "GSTN Status is not active"
                return data  # type: ignore
            else:
                return {"error": "Detail not Found"}  # type: ignore
        except Exception:
            return {"error": "Verification Failed"}

    # PAN Verification
    def verify_pan(self, pan_no: str, full_name: str, dob: str) -> dict:
        URL = self._url_list["pan"]

        self._payload.update(
            {"data": {"id_number": pan_no, "full_name": full_name, "dob": dob}}
        )

        try:
            response = requests.post(URL, headers=self._headers, json=self._payload)  # type: ignore
            res = json.loads(response.content)
            request_id = res.get("request_id", None)  # type: ignore
            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=self._headers)

                res = json.loads(response.content)
                verified_data = res[0].get("result", {}).get("source_output")
                data = {}
                data["aadhaar_seeding_status"] = verified_data.get(
                    "aadhaar_seeding_status", ""
                )
                data["pan_status"] = verified_data.get("pan_status", "")
                data["name_match"] = verified_data.get("name_match", "")
                data["dob_match"] = verified_data.get("dob_match", "")
                data["status"] = verified_data.get("status", "")
                return data  # type: ignore
            else:
                return {"error": "Detail not Found"}  # type: ignore
        except Exception:
            return {"error": "Verification Failed"}


def run():
    while True:
        print("1. Udhyam Verification")
        print("2. GSTIN Verification")
        print("3. PAN Verification")
        print("3. Exit")
        option = int(input("What you want to verify: "))
        if option == 1:
            udhyam_no = input("Enter Udhyam Number: ")
            GovernmentDocVerification().verify_udhyam(udhyam_no)
        elif option == 2:
            gst_no = input("Enter GSTIN: ")
            GovernmentDocVerification().verify_gst(gst_no)
        elif option == 3:
            pan_no = input("Enter PAN: ")
            full_name = input("Enter Full Name")
            dob = input("Enter DOB")
            GovernmentDocVerification().verify_pan(pan_no, full_name, dob)
        elif option == 4:
            print("Thank you")
            break
        else:
            continue


if __name__ == "__main__":
    run()
