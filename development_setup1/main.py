from fastapi import FastAPI
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta
import random

app = FastAPI()

# ---------------- REQUEST MODEL ----------------

class QuestionRequest(BaseModel):
    question: str
    clientId: str

# ---------------- LOGIN DETAILS ----------------

POST_URL = "https://test.energyeta.ai/user/login"
GET_URL = "https://test.energyeta.ai/alert/getAllAlerts"

LOGIN_DATA = {
    "email": "development@thermelgy.com",
    "password": "admin@123"
}

# ---------------- KEYWORDS ----------------

SENSOR_KEYWORDS = [
    "sensor",
    "meter",
    "health",
    "energy meter",
    "sensor health",
    "anomaly",
    "alarm",
    "alert",
    "ea reset",
    "failure",
    "meters",
    "sensors"
]

# ---------------- MAIN API ----------------

@app.post("/sensor-health")
def sensor_health(request: QuestionRequest):

    try:

        # ---------------- LOGIN API ----------------

        login_response = requests.post(
            POST_URL,
            json=LOGIN_DATA
        )

        login_result = login_response.json()

        token = login_result["data"]["accessToken"]

        # ---------------- LAST 12 HOURS ----------------

        now = datetime.utcnow()
        last_12_hours = now - timedelta(hours=12)

        # ---------------- ALERT API BODY ----------------

        body = {
            "page": 1,
            "limit": 50,
            "clientId": request.clientId,
            "search": "",
            "alertType": "alarm"
        }

        headers = {
            "Authorization": token
        }

        # ---------------- GET ALERT DATA ----------------

        response = requests.post(
            GET_URL,
            json=body,
            headers=headers
        )

        result = response.json()

        alerts = result["data"]["data"]

        latest_alerts = []

        # ---------------- FILTER LAST 12 HOURS ----------------

        for alert in alerts:

            alert_time = alert.get("alertTimestamp")

            if alert_time:

                alert_datetime = datetime.fromisoformat(
                    alert_time.replace("Z", "")
                )

                if alert_datetime >= last_12_hours:

                    latest_alerts.append(alert)

        # ---------------- SORT IN DESCENDING ORDER ----------------

        latest_alerts.sort(
            key=lambda x: x.get("alertTimestamp", ""),
            reverse=True
        )

        # ---------------- ONLY TOP 3 ALERTS ----------------

        latest_alerts = latest_alerts[:3]
        

        # ---------------- QUESTION CHECK ----------------

        question_lower = request.question.lower()

        matched = any(
            keyword in question_lower
            for keyword in SENSOR_KEYWORDS
        )

        # ---------------- ANSWER GENERATION ----------------

        if matched:

            # ---------- NO ALERTS ----------

            if len(latest_alerts) == 0:

                healthy_sentences = [

                    "All energy meters and sensors reported data correctly in the last 12 hours.",

                    "No sensor failures or EA reset anomalies were detected in the last 12 hours.",

                    "Sensor health status is normal. All devices are communicating properly.",

                    "Energy meter and sensor monitoring indicates stable operation with no anomalies.",

                    "All monitored sensors and energy meters are functioning correctly without alerts."
                ]

                answer = random.choice(healthy_sentences)

            # ---------- ALERTS FOUND ----------

            else:

                bullet_points = []

                for alert_obj in latest_alerts:

                    machine_name = alert_obj["machine"]["machineName"]

                    trigger = alert_obj.get("trigger", {})

                    metric = trigger.get(
                        "displayName",
                        "sensor"
                    )

                    field_value = trigger.get(
                        "fieldValue",
                        0
                    )

                    trigger_point = trigger.get(
                        "triggerPoint",
                        [0]
                    )[0]

                    # ---------------- HUMAN EXPLANATION ----------------

                    explanation = ""

                    # ---------- POWER / HIGH VALUE ALERT ----------

                    if (
                        field_value > trigger_point
                        and field_value > 10
                    ):

                        difference = round(
                            field_value - trigger_point,
                            2
                        )

                        templates = [

                            f"• {machine_name} reported high {metric.lower()} readings of {field_value}, exceeding the threshold limit of {trigger_point}.",

                            f"• {machine_name} recorded abnormal {metric.lower()} values. Current reading reached {field_value} against the limit of {trigger_point}.",

                            f"• Monitoring detected elevated {metric.lower()} in {machine_name}. The recorded value was {field_value}, above the configured limit.",

                            f"• {machine_name} crossed the permitted {metric.lower()} threshold with a recorded value of {field_value}.",

                            f"• Sensor analysis found excessive {metric.lower()} levels in {machine_name}, reaching {field_value}."
                        ]

                        explanation = random.choice(
                            templates
                        )

                    # ---------- SENSOR FAILURE / RESET ----------

                    else:

                        templates = [

                            f"• {machine_name} generated a sensor alert for {metric} with a recorded value of {field_value}.",

                            f"• An abnormal sensor event was detected in {machine_name}. {metric} reported a value of {field_value}.",

                            f"• Monitoring identified unusual activity in {machine_name}, where {metric} triggered an alert value of {field_value}.",

                            f"• {machine_name} reported irregular sensor behavior related to {metric} with a value of {field_value}.",

                            f"• Sensor health monitoring detected an anomaly in {machine_name} for {metric} with a recorded value of {field_value}."
                        ]

                        explanation = random.choice(
                            templates
                        )

                    bullet_points.append(
                        explanation
                    )

                # ---------------- INTRO SENTENCE ----------------

                intro_sentences = [

                    "The following sensor and energy meter anomalies were detected in the last 12 hours:\n",

                    "Recent monitoring identified these abnormal operating conditions:\n",

                    "Sensor health analysis detected the following critical alerts:\n",

                    "Energy monitoring systems reported these anomaly events:\n",

                    "The latest health check identified the following issues:\n"
                ]

                answer = (
                    random.choice(intro_sentences)
                    + "\n\n"
                    + "\n\n".join(bullet_points)
                )

        # ---------------- QUESTION NOT MATCHED ----------------

        else:

            answer = (
                "Question not related to sensor health check, "
                "energy meters, anomalies, or alert monitoring."
            )

        # ---------------- FINAL RESPONSE ----------------

        return {
            "statusCode": 200,
            "data": {
                "question": request.question,
                "answer": answer
            },
            "msg": "Success"
        }

    # ---------------- ERROR HANDLING ----------------

    except Exception as e:

        return {
            "statusCode": 500,
            "data": {
                "question": request.question,
                "answer": str(e)
            },
            "msg": "Failed"
        }
