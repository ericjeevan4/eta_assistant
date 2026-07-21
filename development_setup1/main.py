#7
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

def get_utc_now():
    return datetime.now(timezone.utc)

def get_spike_api_url(client_id):

    today = get_utc_now()

    current_date = today.strftime("%Y-%m-%d")

    start_time = f"{current_date}T00:00:00.000Z"

    end_time = f"{current_date}T23:55:00.000Z"

    return (
        "https://test.energyeta.ai/machine/"
        "getTopEnergyContributedMachines/"
        f"{client_id}"
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
    "meters",
    "sensors"
]

COMMUNICATION_KEYWORDS = [
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

RUNTIME_KEYWORDS = [

    "unusual",
    "operating",
    "breach",
    "operational",
    "unplanned",
    "schedule",
    "scheduled",
    "runtime breach",
    "operating hours"
]

# =========================================================
# RANDOM NO ALERT RESPONSES
# =========================================================

NO_ALERT_MESSAGES = [

    "No unusual operating hours were identified in the last 24 hours.",

    "All monitored machines operated within expected schedules during the last 24 hours.",

    "No runtime breach alerts were reported in the previous 24 hours.",

    "No potential unplanned operational activity was detected recently.",

    "Machines appear to be functioning within scheduled operating timelines.",

    "No abnormal operational hour patterns were observed in the last 24 hours.",

    "System analysis shows no unusual runtime activity.",

    "No unexpected machine runtime behavior was detected during the monitoring period.",

    "The monitoring system did not identify any operational schedule deviations."
]

# =========================================================
# RANDOM INTRO SENTENCES
# =========================================================

INTRO_MESSAGES = [

    "Potential unplanned operational activity was detected for the following machines:",

    "Runtime breach alerts were observed for these machines:",

    "The following machines showed unusual operating patterns:",

    "Detected operational hour deviations for the machines below:",

    "The following machines exceeded expected runtime schedules:",

    "Monitoring analysis identified unusual operational activity for these machines:",

    "The system detected runtime anomalies for the following machines:"
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
# EA CLIENT OR NOT
# =========================================================

EA_CHECK_URL = "https://api.energyeta.ai/clients/isEA"

def is_ea_client(client_id):

    try:

        payload = {
            "clientId": client_id
        }

        response = requests.get(
            EA_CHECK_URL,
            json=payload
        )

        if response.status_code == 200:

            result = response.json()

            data = result.get("data", {})

            if data.get("isEaClient") is True:
                return True

            if data.get("sEaClient") is False:
                return False

        return False

    except Exception as e:

        print(f"EA API Error: {e}")

        return False
        
# =========================================================
# FETCH SPIKE DATA
# =========================================================

def fetch_api_data(
    token,
    client_id
):

    try:

        headers = {
            "Authorization": token
        }

        spike_api_url = get_spike_api_url(
            client_id
        )

        print(
            f"SPIKE API URL: {spike_api_url}"
        )

        response = requests.get(
            spike_api_url,
            headers=headers
        )
        print("CLIENT:", client_id)
        print("SPIKE URL:", spike_api_url)
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        if response.status_code == 200:

            return response.json().get(
                "data",
                {}
            )

        print(
            f"SPIKE API FAILED: {response.status_code}"
        )

        return None

    except Exception as e:

        print(
            f"SPIKE API ERROR: {str(e)}"
        )

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
            
        history.sort(
            key=lambda x: x["timestamp"]
        )

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
# FILTER ALERTS BY HOURS
# =========================================================

def filter_alerts_by_hours(alerts, hours):

    now = get_utc_now()

    target_time = now - timedelta(hours=hours)

    filtered_alerts = []

    for alert in alerts:

        alert_time = (
            alert.get("alertTimestamp")
            or alert.get("createdAt")
        )

        if alert_time:

            try:

                alert_datetime = datetime.fromisoformat(
                    alert_time.replace("Z", "+00:00")
                )

                if alert_datetime >= target_time:

                    filtered_alerts.append(alert)

            except:
                continue

    filtered_alerts.sort(
        key=lambda x: (
            x.get("alertTimestamp")
            or x.get("createdAt", "")
        ),
        reverse=True
    )

    return filtered_alerts

# =========================================================
# FILTER LAST 24 HOURS
# =========================================================

def filter_last_24_hours(alerts):

    now = datetime.now(timezone.utc)

    last_24 = now - timedelta(hours=24)

    filtered = []

    for item in alerts:

        alert_time = item.get("alertTimestamp")

        if alert_time:

            try:

                alert_datetime = datetime.fromisoformat(
                    alert_time.replace("Z", "+00:00")
                )

                if alert_datetime >= last_24:
                    filtered.append(item)

            except:
                pass

    return filtered

# =========================================================
# QUESTION VALIDATION
# =========================================================

def is_valid_question(question):

    question = question.lower()

    for keyword in RUNTIME_KEYWORDS:

        if keyword in question:
            return True

    return False

# =========================================================
# FORMAT DATE TIME
# =========================================================

def format_datetime(timestamp):

    try:

        dt = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        return dt.strftime(
            "%d-%m-%Y %I:%M:%S %p UTC"
        )

    except:
        return timestamp

# =========================================================
# FETCH ALERTS
# =========================================================

def fetch_alerts(
    token,
    client_id,
    alert_type="alarm"
):

    headers = {
        "Authorization": token
    }

    payload = {
        "page": 1,
        "limit": 50,
        "clientId": client_id,
        "search": "",
        "alertType": alert_type
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

            # ==========================================
            # CLIENT ID REQUIRED
            # ==========================================

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }

            # ==========================================
            # EA CLIENT VALIDATION
            # ==========================================

            if not is_ea_client(
                request.clientId
            ):

                return {
                    "statusCode": 200,
                    "data": {
                        "question": request.question,
                        "answer": "This is NON-EA client."
                    },
                    "msg": "Success"
                }

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
                token,
                request.clientId
            )

            if not api_data:

                return {
                    "statusCode": 200,
                    "data": {
                        "question": request.question,
                        "answer": "No energy spike data available for this client."
                    },
                    "msg": "Success"
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
        # LAST 6 HOURS
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in CRITICAL_KEYWORDS
        ):

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }


            token = get_access_token()

            alerts = fetch_alerts(
                token,
                request.clientId,
                "alarm"
            )

            alerts = filter_alerts_by_hours(
                alerts,
                6
            )

            sorted_alerts = sorted(
                alerts,
                key=lambda x: float(
                    x.get("trigger", {})
                     .get("fieldValue", 0)
                ),
                reverse=True
            )

            latest_alerts = sorted_alerts[:3]

            if len(latest_alerts) == 0:

                final_answer = (
                    "No critical alerts were detected in the last 6 hours."
                )

            else:

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
        # LAST 12 HOURS
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in SENSOR_KEYWORDS
        ):

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }

            
            # ==========================================
            # EA CLIENT VALIDATION
            # ==========================================
            
            if not is_ea_client(
                request.clientId
            ):

                return {
                    "statusCode": 200,
                    "data": {
                        "question": request.question,
                        "answer": "This is NON-EA client."
                    },
                    "msg": "Success"
                }

            token = get_access_token()

            alerts = fetch_alerts(
                token,
                request.clientId,
                "alarm"
            )

            latest_alerts = filter_alerts_by_hours(
                alerts,
                12
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

                    trigger = alert_obj.get(
                        "trigger",
                        {}
                    )

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

                    if (
                        field_value > trigger_point
                        and field_value > 10
                    ):

                        templates = [

                            f"• {machine_name} reported high {metric.lower()} readings of {field_value}, exceeding the threshold limit of {trigger_point}.",

                            f"• {machine_name} recorded abnormal {metric.lower()} values. Current reading reached {field_value} against the limit of {trigger_point}.",

                            f"• Monitoring detected elevated {metric.lower()} in {machine_name}. The recorded value was {field_value}, above the configured limit.",

                            f"• {machine_name} crossed the permitted {metric.lower()} threshold with a recorded value of {field_value}.",

                            f"• Sensor analysis found excessive {metric.lower()} levels in {machine_name}, reaching {field_value}."

                        ]

                    else:

                        templates = [

                            f"• {machine_name} generated a sensor alert for {metric} with a recorded value of {field_value}.",

                            f"• An abnormal sensor event was detected in {machine_name}. {metric} reported a value of {field_value}.",

                            f"• Monitoring identified unusual activity in {machine_name}, where {metric} triggered an alert value of {field_value}.",

                            f"• {machine_name} reported irregular sensor behavior related to {metric} with a value of {field_value}.",

                            f"• Sensor health monitoring detected an anomaly in {machine_name} for {metric} with a recorded value of {field_value}."

                        ]

                    bullet_points.append(
                        random.choice(
                            templates
                        )
                    )

                intro_sentences = [

                    "The following sensor and energy meter anomalies were detected in the last 12 hours:\n",

                    "Recent monitoring identified these abnormal operating conditions:\n",

                    "Sensor health analysis detected the following critical alerts:\n",

                    "Energy monitoring systems reported these anomaly events:\n",

                    "The latest health check identified the following issues:\n"

                ]

                final_answer = (
                    random.choice(
                        intro_sentences
                    )
                    + "\n\n"
                    + "\n\n".join(
                        bullet_points
                    )
                )

        # =====================================================
        # COMMUNICATION FAILURE API
        # LAST 24 HOURS
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in COMMUNICATION_KEYWORDS
        ):

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }

            token = get_access_token()

            alerts = fetch_alerts(
                token,
                request.clientId,
                "data"
            )

            latest_alerts = filter_alerts_by_hours(
                alerts,
                24
            )

            latest_devices = {}

            for alert in latest_alerts:

                alert_time = datetime.fromisoformat(
                    (
                        alert.get("createdAt")
                        or alert.get("alertTimestamp")
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )

                machine = alert.get(
                    "machine",
                    {}
                )

                device_id = machine.get(
                    "deviceId",
                    "Unknown Device"
                )

                if (
                    device_id not in latest_devices
                    or alert_time > latest_devices[device_id]
                ):
                    latest_devices[device_id] = alert_time

            sorted_devices = sorted(
                latest_devices.items(),
                key=lambda x: x[1],
                reverse=True
            )

            top_3_devices = sorted_devices[:3]

            if len(top_3_devices) > 0:

                device_details = []

                for device_id, timestamp in top_3_devices:

                    formatted_time = timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    )

                    device_details.append(
                        f"{device_id} ({formatted_time})"
                    )

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

                final_answer = selected_response.format(
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

                final_answer = random.choice(
                    no_issue_templates
                )

        # =====================================================
        # ENERGY API
        # LAST 24-48 HOURS + PREVIOUS WEEK
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in ENERGY_KEYWORDS
        ):

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": "Client ID is required."
                    },
                    "msg": "Client validation failed"
                }


            token = get_access_token()

            alerts = fetch_alerts(
                token,
                request.clientId,
                "alarm"
            )

            now = get_utc_now()

            last_48_hours = now - timedelta(hours=48)

            previous_week_start = now - timedelta(days=8)

            previous_week_end = now - timedelta(days=7)

            current_period_alerts = []

            previous_week_alerts = []

            for alert in alerts:

                alert_time = (
                    alert.get("alertTimestamp")
                    or alert.get("createdAt")
                )

                if alert_time:

                    try:

                        alert_datetime = datetime.fromisoformat(
                            alert_time.replace("Z", "+00:00")
                        )

                        trigger = alert.get(
                            "trigger",
                            {}
                        )

                        field_value = float(
                            trigger.get(
                                "fieldValue",
                                0
                            )
                        )

                        if alert_datetime >= last_48_hours:

                            current_period_alerts.append(
                                field_value
                            )

                        elif (
                            previous_week_start
                            <= alert_datetime
                            <= previous_week_end
                        ):

                            previous_week_alerts.append(
                                field_value
                            )

                    except:
                        continue

            yesterday_energy = round(
                sum(current_period_alerts),
                2
            )

            last_week_energy = round(
                sum(previous_week_alerts),
                2
            )

            if last_week_energy == 0:

                difference_percent = 0

            else:

                difference_percent = (
                    (
                        yesterday_energy
                        - last_week_energy
                    )
                    / last_week_energy
                ) * 100

            trend_sentence = (
                "increased"
                if difference_percent >= 0
                else "decreased"
            )

            trend_word = (
                "increase"
                if difference_percent >= 0
                else "decrease"
            )

            response_templates = [

                f"""
Total Energy Consumption Analysis
Yesterday's facility energy consumption was {yesterday_energy} kWh.
During the same day last week, the recorded consumption was {last_week_energy} kWh.
Overall energy usage has {trend_sentence} by {abs(difference_percent):.2f}%.
""",

                f"""
Building Energy Monitoring Report
The facility consumed {yesterday_energy} kWh yesterday.
Compared to {last_week_energy} kWh on the same day last week, the energy usage has {trend_sentence} by {abs(difference_percent):.2f}%.
""",

                f"""
Main Incomer Energy Summary
Yesterday's energy consumption reached {yesterday_energy} kWh.
Last week's same-day consumption was {last_week_energy} kWh.
This indicates a {abs(difference_percent):.2f}% {trend_word} in total energy usage.
""",

                f"""
Total Building Energy Overview
The total facility energy usage yesterday was {yesterday_energy} kWh.
For comparison, the same day last week recorded {last_week_energy} kWh.
Energy consumption has {trend_sentence} by {abs(difference_percent):.2f}%.
""",

                f"""
Energy Trend Comparison
Building energy monitoring shows yesterday's consumption at {yesterday_energy} kWh.
Last week's equivalent day reported {last_week_energy} kWh.
This represents a {abs(difference_percent):.2f}% {trend_word} in energy consumption.
"""

            ]

            final_answer = random.choice(
                response_templates
            )

        # =====================================================
        # RUNTIME BREACH API
        # LAST 24 HOURS
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in RUNTIME_KEYWORDS
        ):

            if not request.clientId:

                return {
                    "statusCode": 400,
                    "msg": "clientId is required"
                }

            if not is_valid_question(request.question):

                return {
                    "statusCode": 400,
                    "data": {
                        "question": request.question,
                        "answer": (
                            "Please ask questions related "
                            "to unusual operating hours "
                            "or runtime breach."
                        )
                    },
                    "msg": "Invalid question"
                }

            token = get_access_token()

            if not token:

                return {
                    "statusCode": 500,
                    "msg": "Login failed"
                }

            alerts = fetch_alerts(
                token,
                request.clientId,
                "schedule"
            )

            alerts = filter_last_24_hours(
                alerts
            )

            alerts = alerts[:3]

            if len(alerts) == 0:

                final_answer = random.choice(
                    NO_ALERT_MESSAGES
                )

            else:

                lines = []

                lines.append(
                    random.choice(
                        INTRO_MESSAGES
                    )
                )

                lines.append(
                    "The analysis below is based on the last 24 hours of runtime breach monitoring data."
                )

                lines.append(
                    "Only the top 3 affected machines are included in this response."
                )

                for index, item in enumerate(alerts, start=1):

                    machine = item.get(
                        "machine",
                        {}
                    )

                    machine_name = machine.get(
                        "machineName",
                        "Unknown"
                    )

                    timestamp = item.get(
                        "alertTimestamp",
                        "Unknown"
                    )

                    formatted_time = format_datetime(
                        timestamp
                    )

                    incidents = item.get(
                        "incidents",
                        []
                    )

                    runtime = "Unknown"

                    if len(incidents) > 0:

                        runtime = incidents[0].get(
                            "fieldValue",
                            "Unknown"
                        )

                    lines.append(

                        f"{index}. Machine Name: {machine_name}\n"
                        f"   Runtime Breach: {runtime} hrs\n"
                        f"   Detected Time: {formatted_time}"
                    )

                final_answer = "\n\n".join(
                    lines
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
