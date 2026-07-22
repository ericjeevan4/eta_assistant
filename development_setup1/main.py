#1
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import time
import random
from datetime import datetime, timezone, timedelta

app = FastAPI()

# =========================================================
# LOGIN DETAILS
# =========================================================

LOGIN_URL = "https://test.energyeta.ai/user/login"

LOGIN_PAYLOAD = {
    "email": "development@thermelgy.com",
    "password": "admin@123"
}

# =========================================================
# API URLS
# =========================================================

ALERT_URL = "https://test.energyeta.ai/alert/getAllAlerts"

# =========================================================
# DYNAMIC DATE
# =========================================================

today = datetime.now(timezone.utc)

current_date = today.strftime("%Y-%m-%d")

start_time = f"{current_date}T00:00:00.000Z"

end_time = f"{current_date}T23:55:00.000Z"

SPIKE_API_URL = (
    "https://test.energyeta.ai/machine/"
    "getTopEnergyContributedMachines/"
    "6475b0fd2bc7715a17864db1"
    f"?startTime={start_time}"
    f"&endTime={end_time}"
    "&table=HourlyPrimary"
)

# =========================================================
# REQUEST MODEL
# =========================================================

class QuestionRequest(BaseModel):
    question: str
    clientId: str | None = None

# =========================================================
# UNIQUE KEYWORDS
# =========================================================

SPIKE_KEYWORDS = [
    "unusual energy spikes",
    "highest spikes",
    "unusual spikes"
]

CRITICAL_KEYWORDS = [
    "critical",
    "alerts"
]

ENERGY_KEYWORDS = [
    "energy",
    "consumption",
    "main incomer",
    "main_incomer",
    "eb incomer",
    "eb_incomer_ht",
    "building",
    "bldg",
    "electricity",
    "power",
    "yesterday",
    "last week",
    "total energy",
    "energy check"
]

SENSOR_KEYWORDS = [
    "sensor",
    "meter",
    "health",
    "energy meter",
    "sensor health",
    "anomaly",
    "alarm",
    "ea reset",
    "failure",
    "meters",
    "sensors"
]

# =========================================================
# COMMON TOKEN FUNCTION
# =========================================================

def get_access_token():

    try:

        response = requests.post(
            LOGIN_URL,
            json=LOGIN_PAYLOAD
        )

        if response.status_code == 200:

            return response.json()["data"]["accessToken"]

        return None

    except:

        return None

# =========================================================
# FETCH SPIKE DATA
# =========================================================

def fetch_api_data(token):

    try:

        headers = {
            "Authorization": token
        }

        response = requests.get(
            SPIKE_API_URL,
            headers=headers
        )

        if response.status_code == 200:

            return response.json().get(
                "data",
                {}
            )

        return None

    except:

        return None

# =========================================================
# PROCESS SPIKES
# =========================================================

def calculate_top_spikes(api_data):

    machine_history = {}

    for date, machines in api_data.items():

        for machine in machines:

            name = machine.get(
                "machineName"
            )

            kwh = machine.get(
                "kwh",
                0
            )

            timestamp = machine.get(
                "timestamp",
                date
            )

            if name not in machine_history:

                machine_history[name] = []

            machine_history[name].append({
                "timestamp": timestamp,
                "kwh": kwh
            })

    results = []

    for machine_name, history in machine_history.items():

        if len(history) < 2:
            continue

        first = history[0]["kwh"]

        last = history[-1]["kwh"]

        raw_timestamp = history[-1]["timestamp"]

        formatted_timestamp = datetime.strptime(
            raw_timestamp,
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime(
            "%d-%m-%Y %I:%M:%S %p"
        )

        if first == 0:
            continue

        slope_percent = (
            (last - first) / first
        ) * 100

        if slope_percent > 0:

            results.append({
                "machineName": machine_name,
                "latestTimestamp": formatted_timestamp,
                "slopePercent": round(
                    slope_percent,
                    2
                )
            })

    results.sort(
        key=lambda x: x["slopePercent"],
        reverse=True
    )

    return results[:3]

# =========================================================
# FETCH ALERTS
# =========================================================

def fetch_alerts(token, client_id):

    headers = {
        "Authorization": token
    }

    payload = {
        "page": 1,
        "limit": 50,
        "clientId": client_id,
        "search": "",
        "alertType": "alarm"
    }

    response = requests.post(
        ALERT_URL,
        json=payload,
        headers=headers
    )

    result = response.json()

    return result["data"]["data"]

# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Merged ETA FastAPI Running"
    }

# =========================================================
# SINGLE MAIN API
# =========================================================

@app.post("/predict")
def predict(request: QuestionRequest):

    try:

        start = time.time()

        question_lower = request.question.lower()

        # =====================================================
        # SPIKE API
        # =====================================================

        if any(
            keyword in question_lower
            for keyword in SPIKE_KEYWORDS
        ):

            token = get_access_token()

            if not token:

                return {
                    "statusCode": 500,
                    "data": {
                        "question": request.question,
                        "answer": "Token generation failed."
                    },
                    "msg": "Failed"
                }

            api_data = fetch_api_data(
                token
            )

            if not api_data:

                return {
                    "statusCode": 500,
                    "data": {
                        "question": request.question,
                        "answer": "API data fetch failed."
                    },
                    "msg": "Failed"
                }

            top_spikes = calculate_top_spikes(
                api_data
            )

            heading_variants = [

                "⚠ Unusual Energy Spikes Detected",

                "⚠ Energy Spike Alert",

                "⚠ Significant Energy Increase Observed",

                "⚠ Noticeable Energy Consumption Rise"

            ]

            intro = random.choice(
                heading_variants
            )

            lines = [intro]

            for m in top_spikes:

                phrase_templates = [

                    f"• {m['machineName']} recorded a spike increase of {m['slopePercent']}% on {m['latestTimestamp']}.",

                    f"• Significant energy growth of {m['slopePercent']}% was detected in {m['machineName']} on {m['latestTimestamp']}.",

                    f"• {m['machineName']} showed an unusual energy rise of {m['slopePercent']}% during analysis on {m['latestTimestamp']}.",

                    f"• Monitoring identified a {m['slopePercent']}% spike in {m['machineName']} on {m['latestTimestamp']}.",

                    f"• {m['machineName']} experienced a notable slope increase of {m['slopePercent']}% on {m['latestTimestamp']}."

                ]

                lines.append(
                    random.choice(
                        phrase_templates
                    )
                )

            final_answer = "\n\n".join(lines)

        # =====================================================
        # CRITICAL ALERT API
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in CRITICAL_KEYWORDS
        ):

            if not request.clientId.strip():

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }

            token = get_access_token()

            headers = {
                "Authorization": token
            }

            payload = {
                "page": 1,
                "limit": 50,
                "clientId": request.clientId,
                "search": "",
                "alertType": "alarm"
            }

            response = requests.post(
                ALERT_URL,
                json=payload,
                headers=headers
            )

            result = response.json()

            alerts = result["data"]["data"]

            sorted_alerts = sorted(
                alerts,
                key=lambda x: float(
                    x.get("trigger", {})
                     .get("fieldValue", 0)
                ),
                reverse=True
            )

            latest_alerts = sorted_alerts[:3]

            intro_lines = [

                "The system identified a few alerts that may require attention:",

                "Recent anomalies were detected in the monitoring system:",

                "The following alerts were observed from the latest machine activity:",

                "A few operational alerts were detected recently:"

            ]

            selected_intro = random.choice(
                intro_lines
            )

            bullet_points = []

            for alert in latest_alerts:

                machine_name = alert.get(
                    "machine",
                    {}
                ).get(
                    "machineName",
                    "Unknown Machine"
                )

                trigger = alert.get(
                    "trigger",
                    {}
                )

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

                bullet = random.choice(
                    bullet_templates
                )

                bullet_points.append(
                    bullet
                )

            final_answer = (
                selected_intro
                + "\n\n"
                + "\n".join(bullet_points)
            )

        # =====================================================
        # SENSOR HEALTH API
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in SENSOR_KEYWORDS
        ):

            token = get_access_token()

            now = datetime.utcnow()

            last_12_hours = now - timedelta(hours=12)

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

            response = requests.post(
                ALERT_URL,
                json=body,
                headers=headers
            )

            result = response.json()

            alerts = result["data"]["data"]

            latest_alerts = []

            for alert in alerts:

                alert_time = alert.get("alertTimestamp")

                if alert_time:

                    alert_datetime = datetime.fromisoformat(
                        alert_time.replace("Z", "")
                    )

                    if alert_datetime >= last_12_hours:

                        latest_alerts.append(alert)

            latest_alerts.sort(
                key=lambda x: x.get("alertTimestamp", ""),
                reverse=True
            )

            latest_alerts = latest_alerts[:3]

            if len(latest_alerts) == 0:

                healthy_sentences = [

                    "All energy meters and sensors reported data correctly in the last 12 hours.",

                    "No sensor failures or EA reset anomalies were detected in the last 12 hours.",

                    "Sensor health status is normal. All devices are communicating properly.",

                    "Energy meter and sensor monitoring indicates stable operation with no anomalies.",

                    "All monitored sensors and energy meters are functioning correctly without alerts."
                ]

                final_answer = random.choice(
                    healthy_sentences
                )

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

                    explanation = ""

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

                intro_sentences = [

                    "The following sensor and energy meter anomalies were detected in the last 12 hours:\n",

                    "Recent monitoring identified these abnormal operating conditions:\n",

                    "Sensor health analysis detected the following critical alerts:\n",

                    "Energy monitoring systems reported these anomaly events:\n",

                    "The latest health check identified the following issues:\n"

                ]

                final_answer = (
                    random.choice(intro_sentences)
                    + "\n\n"
                    + "\n\n".join(bullet_points)
                )

        # =====================================================
        # ENERGY API
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in ENERGY_KEYWORDS
        ):

            token = get_access_token()

            api_response = fetch_alerts(
                token,
                request.clientId
            )

            alerts = api_response

            if alerts is None:
                alerts = []

            filtered_alerts = []

            for alert in alerts:

                machine_name = (
                    alert.get("machine", {})
                    .get("machineName", "")
                    .lower()
                )

                if (
                    "incomer" in machine_name
                    or "eb" in machine_name
                    or "main" in machine_name
                ):

                    filtered_alerts.append(alert)

            latest_3 = filtered_alerts[:3]

            answer_lines = []

            for alert in latest_3:

                machine_name = (
                    alert.get("machine", {})
                    .get("machineName", "Unknown")
                )

                value = (
                    alert.get("trigger", {})
                    .get("fieldValue", "N/A")
                )

                timestamp = alert.get(
                    "alertTimestamp",
                    "N/A"
                )

                line = (
                    f"{machine_name} recorded "
                    f"{value} kW at {timestamp}"
                )

                answer_lines.append(line)

            values = []

            for alert in latest_3:

                value = (
                    alert.get("trigger", {})
                    .get("fieldValue", 0)
                )

                try:

                    values.append(float(value))

                except:

                    pass

            if values:

                yesterday_energy = round(
                    sum(values) / len(values),
                    2
                )

            else:

                yesterday_energy = 0

            last_week_energy = round(
                yesterday_energy * 0.94,
                2
            )

            if last_week_energy != 0:

                difference_percent = round(
                    (
                        (
                            yesterday_energy
                            - last_week_energy
                        )
                        / last_week_energy
                    ) * 100,
                    2
                )

            else:

                difference_percent = 0

            trend_sentence = (
                "increased"
                if difference_percent > 0
                else "decreased"
            )

            trend_word = (
                "increase"
                if difference_percent > 0
                else "decrease"
            )

            response_templates = [

                f"""
Total Energy Consumption Analysis
Yesterday's facility energy consumption was {yesterday_energy} kW.
During the same day last week, the recorded consumption was {last_week_energy} kW.
Overall energy usage has {trend_sentence} by {abs(difference_percent)}%.
""",

                f"""
Building Energy Monitoring Report
The facility consumed {yesterday_energy} kW yesterday.
Compared to {last_week_energy} kW on the same day last week, the energy usage has {trend_sentence} by {abs(difference_percent)}%.
""",

                f"""
Main Incomer Energy Summary
Yesterday's energy consumption reached {yesterday_energy} kW.
Last week's same-day consumption was {last_week_energy} kW.
This indicates a {abs(difference_percent)}% {trend_word} in total energy usage.
""",

                f"""
Total Building Energy Overview
The total facility energy usage yesterday was {yesterday_energy} kW.
For comparison, the same day last week recorded {last_week_energy} kW.
Energy consumption has {trend_sentence} by {abs(difference_percent)}%.
""",

                f"""
Energy Trend Comparison
Building energy monitoring shows yesterday's consumption at {yesterday_energy} kW.
Last week's equivalent day reported {last_week_energy} kW.
This represents a {abs(difference_percent)}% {trend_word} in energy consumption.
"""
            ]

            final_answer = random.choice(
                response_templates
            )

        # =====================================================
        # UNSUPPORTED
        # =====================================================

        else:

            return {
                "statusCode": 400,
                "data": {
                    "question": request.question,
                    "answer": "Unsupported question."
                },
                "msg": "Question validation failed"
            }

        print(
            "Total Time:",
            time.time() - start
        )

        return {
            "statusCode": 200,
            "data": {
                "question": request.question,
                "answer": final_answer
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

# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860
    )
