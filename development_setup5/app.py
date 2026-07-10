from fastapi import FastAPI
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta, timezone
import random

app = FastAPI()

# ---------------- LOGIN DETAILS ----------------

LOGIN_URL = "https://test.energyeta.ai/user/login"
ALERT_URL = "https://test.energyeta.ai/alert/getAllAlerts"

LOGIN_DATA = {
    "email": "development@thermelgy.com",
    "password": "admin@123"
}

# ---------------- KEYWORDS ----------------

KEYWORDS = [
    "communication failures",
    "data logging failure",
    "data logging failures",
    "gaps",
    "communication loss",
    "data communication loss",
    "communication gap",
    "network issue",
    "network failure"
]

# ---------------- REQUEST BODY ----------------

class QuestionRequest(BaseModel):
    question: str
    clientId: str


# ---------------- API ENDPOINT ----------------

@app.post("/communication-failures")
def communication_failures(request: QuestionRequest):

    try:

        # ---------------- QUESTION VALIDATION ----------------

        question_lower = request.question.lower()

        if not any(
            keyword in question_lower
            for keyword in KEYWORDS
        ):

            return {
                "statusCode": 400,
                "data": {
                    "question": request.question,
                    "answer": (
                        "Question does not match "
                        "communication failure category."
                    )
                },
                "msg": "Failed"
            }

        # ---------------- LOGIN API ----------------

        login_response = requests.post(
            LOGIN_URL,
            json=LOGIN_DATA
        )

        login_result = login_response.json()

        token = login_result["data"]["accessToken"]

        # ---------------- HEADERS ----------------

        headers = {
            "Authorization": token
        }

        # ---------------- ALERT PAYLOAD ----------------

        alert_payload = {
            "page": 1,
            "limit": 50,
            "clientId": request.clientId,
            "search": "",
            "alertType": "alarm"
        }

        # ---------------- ALERT API ----------------

        alert_response = requests.post(
            ALERT_URL,
            json=alert_payload,
            headers=headers
        )

        alert_result = alert_response.json()

        alerts = alert_result["data"]["data"]

        # ---------------- LAST 24 HOURS ----------------

        now = datetime.now(timezone.utc)

        last_24_hours = now - timedelta(hours=24)

        latest_devices = {}

        for alert in alerts:

            alert_time = datetime.fromisoformat(
                alert["alertTimestamp"].replace(
                    "Z",
                    "+00:00"
                )
            )

            # Only last 24 hours
            if alert_time >= last_24_hours:

                device_id = alert["machine"]["deviceId"]

                # Store latest timestamp
                if (
                    device_id not in latest_devices
                    or alert_time > latest_devices[device_id]
                ):
                    latest_devices[device_id] = alert_time

        # ---------------- SORT LATEST FIRST ----------------

        sorted_devices = sorted(
            latest_devices.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Only latest 3 device IDs
        top_3_devices = sorted_devices[:3]

        # ---------------- FINAL ANSWER ----------------

        if len(top_3_devices) > 0:

            device_details = []

            for device_id, timestamp in top_3_devices:

                formatted_time = timestamp.strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )

                device_details.append(
                    f"{device_id} ({formatted_time})"
                )

            # 7 dynamic response templates
            response_templates = [

                "Communication failures were identified within the last 24 hours for Device IDs: {}.",

                "Recent data communication gaps were observed in the following devices during the past 24 hours: {}.",

                "The monitoring system detected communication loss events for these devices in the last 24 hours: {}.",

                "Network communication interruptions were recorded recently for Device IDs: {}.",

                "Data logging failures have been identified in the last 24 hours for the following devices: {}.",

                "The latest communication-related alerts were triggered for these Device IDs: {}.",

                "Communication gap alerts were found recently for the following devices: {}."
            ]

            selected_response = random.choice(
                response_templates
            )

            answer_text = selected_response.format(
                ", ".join(device_details)
            )

        else:

            no_issue_templates = [

                "No communication failures were detected in the last 24 hours.",

                "No recent data logging gaps were identified during the last 24 hours.",

                "All monitored devices communicated successfully in the past 24 hours.",

                "No communication loss events were found recently.",

                "The system did not record any communication interruptions in the last 24 hours.",

                "No network communication alerts were triggered recently.",

                "No data communication issues were observed in the monitored devices."
            ]

            answer_text = random.choice(
                no_issue_templates
            )

        # ---------------- FINAL RESPONSE ----------------

        return {
            "statusCode": 200,
            "data": {
                "question": request.question,
                "answer": answer_text
            },
            "msg": "Success"
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "data": {
                "question": request.question,
                "answer": str(e)
            },
            "msg": "Failed"
        }