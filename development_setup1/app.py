from fastapi import FastAPI
from pydantic import BaseModel
import requests
import random

app = FastAPI()

# =========================
# LOGIN DETAILS
# =========================

LOGIN_URL = "https://test.energyeta.ai/user/login"

login_payload = {
    "email": "development@thermelgy.com",
    "password": "admin@123"
}

# =========================
# ALERT API
# =========================

ALERT_URL = "https://test.energyeta.ai/alert/getAllAlerts"

# =========================
# REQUEST BODY MODEL
# =========================

class AlertRequest(BaseModel):
    page: int = 1
    limit: int = 50
    clientId: str
    search: str = ""
    alertType: str = "alarm"


# =========================
# GET TOKEN FUNCTION
# =========================

def get_token():

    response = requests.post(LOGIN_URL, json=login_payload)

    data = response.json()

    token = data["data"]["accessToken"]

    return token


# =========================
# MAIN ALERT API
# =========================

@app.post("/critical-alerts")
def get_alerts(request: AlertRequest):

    token = get_token()

    headers = {
        "Authorization": token
    }

    payload = {
        "page": request.page,
        "limit": request.limit,
        "clientId": request.clientId,
        "search": request.search,
        "alertType": request.alertType
    }

    response = requests.post(
        ALERT_URL,
        json=payload,
        headers=headers
    )

    result = response.json()

    alerts = result["data"]["data"]

    # Get latest 3 alerts
    latest_alerts = alerts[:3]

    # Dynamic intro lines
    intro_lines = [
        "The system identified a few alerts that may require attention:",
        "Recent anomalies were detected in the monitoring system:",
        "The following alerts were observed from the latest machine activity:",
        "A few operational alerts were detected recently:"
    ]

    selected_intro = random.choice(intro_lines)

    bullet_points = []

    for alert in latest_alerts:

        machine_name = alert.get(
            "machine",
            {}
        ).get(
            "machineName",
            "Unknown Machine"
        )

        trigger = alert.get("trigger", {})

        display_name = trigger.get(
            "displayName",
            "Unknown Alert"
        )

        field_value = trigger.get(
            "fieldValue",
            "N/A"
        )

        bullet_templates = [

            f"• {machine_name} reported {display_name} with current value {field_value}.",

            f"• An alert was triggered in {machine_name} for {display_name} reaching {field_value}.",

            f"• {display_name} in {machine_name} is currently showing a value of {field_value}.",

            f"• Monitoring detected unusual activity in {machine_name}: {display_name} = {field_value}.",

            f"• The system observed {display_name} at {field_value} in {machine_name}.",

            f"• Alert generated from {machine_name} due to {display_name} value {field_value}."

        ]

        bullet = random.choice(bullet_templates)

        bullet_points.append(bullet)

    final_answer = (
        selected_intro +
        "\n\n" +
        "\n".join(bullet_points)
    )

    return {
        "statusCode": 200,
        "data": {
            "question": "Did the system identify any anomalies or alerts that require immediate attention?",
            "answer": final_answer
        },
        "msg": "Success"
    }
