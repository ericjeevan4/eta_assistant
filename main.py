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
HLP_ALERT_URL = "https://test.energyeta.ai/alert/getAllDigiOpsAlerts"
EA_CHECK_URL = "https://api.energyeta.ai/clients/isEA"

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

HLP_KEYWORDS = [
    "hlp",
    "hlp data",
    "hlp anomalies",
    "hlp anomaly"
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

def get_daily_energy_data(token, client_id):

    headers = {
        "Authorization": token
    }

    today = get_utc_now()

    end_time = today.strftime("%Y-%m-%dT23:55:00.000Z")

    start_time = (
        today - timedelta(days=14)
    ).strftime("%Y-%m-%dT00:00:00.000Z")

    url = (
        "https://test.energyeta.ai/machine/"
        "getTopEnergyContributedMachines/"
        f"{client_id}"
        f"?startTime={start_time}"
        f"&endTime={end_time}"
        "&table=DailyPrimary"
    )

    response = requests.get(
        url,
        headers=headers
    )

    if response.status_code == 200:

        return response.json().get(
            "data",
            {}
        )

    return {}
    
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
# FETCH HLP ANOMALIES
# =========================================================

def fetch_hlp_alerts(
    token,
    client_id
):

    headers = {
        "Authorization": token
    }

    payload = {
        "page": 1,
        "limit": 50,
        "clientId": client_id,
        "search": "",
        "alertType": "digiOps"
    }

    response = requests.post(
        HLP_ALERT_URL,
        json=payload,
        headers=headers
    )

    if response.status_code == 200:

        return response.json().get(
            "data",
            {}
        ).get(
            "data",
            []
        )

    return []

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

            critical_alerts = []

            for alert in alerts:

                trigger = alert.get("trigger", {})

                try:

                    field_value = float(
                        trigger.get("fieldValue", 0)
                    )

                    trigger_points = trigger.get(
                        "triggerPoint",
                        [0]
                    )

                    trigger_point = float(
                        trigger_points[0]
                    )

                    if field_value > trigger_point:

                        critical_alerts.append(alert)

                except (ValueError, TypeError, IndexError):

                    continue


            sorted_alerts = sorted(
                critical_alerts,
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
                "data"
            )

            latest_alerts = filter_alerts_by_hours(
                alerts,
                12
            )

            sensor_issue_alerts = []

            for alert in latest_alerts:

                display_text = alert.get(
                    "displayText",
                    ""
                )

                if "data connectivity issue" in display_text.lower():

                    sensor_issue_alerts.append(
                        alert
                    )

            latest_devices = {}

            for alert in sensor_issue_alerts:

                alert_time = datetime.fromisoformat(
                    (
                        alert.get("createdAt")
                        or alert.get("alertTimestamp")
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )

                machine_name = (
                    alert.get("machine", {})
                    .get(
                        "machineName",
                        "Unknown Machine"
                    )
                )

                if (
                    machine_name not in latest_devices
                    or alert_time > latest_devices[machine_name]
                ):
                    latest_devices[machine_name] = alert_time

            sorted_machines = sorted(
                latest_devices.items(),
                key=lambda x: x[1],
                reverse=True
            )

            top_3_machines = sorted_machines[:3]

            if len(top_3_machines) == 0:

                healthy_sentences = [

                    "All energy meters and sensors reported data correctly in the last 12 hours.",

                    "No sensor health issues were detected in the last 12 hours.",

                    "Sensor health status is normal across all monitored devices.",

                    "All monitored sensors communicated successfully during the last 12 hours.",

                    "No data connectivity issues were identified recently.",

                    "The latest health check found all monitored devices operating normally.",

                    "No abnormal sensor behaviour or communication issues were detected."

                ]

                final_answer = random.choice(
                    healthy_sentences
                )

            else:

                intro_sentences = [

                    "The following sensor health issues were detected in the last 12 hours:\n",

                    "Recent monitoring identified the following data connectivity issues:\n",

                    "Sensor health analysis detected the following communication problems:\n",

                    "The latest health check identified these sensor connectivity alerts:\n",

                    "Monitoring systems reported the following sensor health issues:\n"

                ]

                issue_lines = []

                for machine_name, alert_time in top_3_machines:

                    formatted_time = alert_time.strftime(
                        "%d-%m-%Y %I:%M %p"
                    )

                    templates = [

                        f"• {machine_name} reported a data connectivity issue. Detected on {formatted_time}.",

                        f"• Communication from {machine_name} was interrupted during the monitoring period. Alert time: {formatted_time}.",

                        f"• Sensor health monitoring identified a data connectivity problem in {machine_name}. Recorded on {formatted_time}.",

                        f"• {machine_name} experienced a communication gap with the monitoring platform. Detection time: {formatted_time}.",

                        f"• A data transmission issue was detected for {machine_name}. Reported on {formatted_time}.",

                        f"• Monitoring systems detected a loss of data communication from {machine_name}. Event time: {formatted_time}.",

                        f"• Sensor connectivity checks flagged {machine_name} for missing data updates. Detected on {formatted_time}."

                    ]

                    issue_lines.append(
                        random.choice(
                            templates
                        )
                    )

                final_answer = (
                    random.choice(
                        intro_sentences
                    )
                    + "\n"
                    + "\n".join(
                        issue_lines
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
                "dataHang"
            )

            latest_alerts = filter_alerts_by_hours(
                alerts,
                24
            )

            communication_alerts = []

            for alert in latest_alerts:

                display_text = alert.get(
                    "displayText",
                    ""
                )

                if "HDFC Pilot" in display_text:

                    communication_alerts.append(
                        alert
                    )

            latest_devices = {}

            for alert in communication_alerts:

                alert_time = datetime.fromisoformat(
                    (
                        alert.get("createdAt")
                        or alert.get("alertTimestamp")
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )

                device_id = (
                    alert.get("machine", {})
                    .get(
                        "deviceId",
                        "Unknown Device"
                    )
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

                device_ids = [
                    device_id
                    for device_id, _
                    in top_3_devices
                ]

                response_templates = [
            
                    "Communication failures were identified within the last 24 hours for Device IDs: {}.",
            
                    "Recent data communication gaps were observed in the following devices during the past 24 hours: {}.",
            
                    "The monitoring system detected communication loss events for these devices in the last 24 hours: {}.",
            
                    "Network communication interruptions were recorded recently for Device IDs: {}.",
            
                    "Data logging failures have been identified in the last 24 hours for the following devices: {}.",
            
                    "The latest communication-related alerts were triggered for these Device IDs: {}.",
            
                    "Communication gap alerts were found recently for the following devices: {}."
            
                ]

                final_answer = random.choice(
                    response_templates
                ).format(
                    ", ".join(device_ids)
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
        # HLP DATA ANOMALIES
        # LAST 7 DAYS
        # =====================================================

        elif any(
            keyword in question_lower
            for keyword in HLP_KEYWORDS
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

            if not token:

                return {
                    "statusCode": 500,
                    "data": {
                        "question": request.question,
                        "answer": "Token generation failed."
                    },
                    "msg": "Failed"
                }

            alerts = fetch_hlp_alerts(
                token,
                request.clientId
            )

            now = datetime.now(timezone.utc)

            today_start = datetime(
                now.year,
                now.month,
                now.day,
                tzinfo=timezone.utc
            )

            start_date = today_start - timedelta(days=7)

            end_date = today_start

            anomaly_alerts = []

            for alert in alerts:

                try:

                    created_at = datetime.fromisoformat(
                        alert.get(
                            "createdAt"
                        ).replace(
                            "Z",
                            "+00:00"
                        )
                    )

                    if not (
                        start_date <= created_at < end_date
                    ):
                        continue

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

                    trigger_point = float(
                        trigger.get(
                            "triggerPoint",
                            [0]
                        )[0]
                    )

                    if field_value > trigger_point:

                        anomaly_alerts.append(
                            alert
                        )

                except:
                    continue

            anomaly_alerts.sort(
                key=lambda x: x.get(
                    "createdAt",
                    ""
                ),
                reverse=True
            )

            latest_alerts = anomaly_alerts[:3]

            if len(latest_alerts) == 0:

                no_anomaly_messages = [

                    "No HLP data anomalies were detected during the last 7 days.",

                    "The monitoring system did not identify any HLP anomalies in the previous 7 days.",

                    "No unusual HLP data patterns were found during the recent 7-day period.",

                    "All monitored HLP parameters remained within expected limits over the last week.",

                    "No HLP anomaly alerts were generated in the past 7 days.",

                    "The latest HLP analysis found no abnormal data conditions.",

                    "No HLP data exceptions were reported during the previous week."

                ]

                final_answer = random.choice(
                    no_anomaly_messages
                )

            else:

                intro_messages = [

                    "Recent HLP data anomalies were detected during the last 7 days:",

                    "The monitoring system identified the following HLP anomalies:",

                    "HLP anomaly analysis detected the following unusual data conditions:",

                    "The latest HLP review highlighted these anomaly events:",

                    "Recent HLP data exception alerts were observed:",

                    "The following HLP anomaly records require attention:",

                    "Monitoring analysis found these HLP data anomalies:"
                ]

                lines = [
                    random.choice(
                        intro_messages
                    )
                ]

                for alert in latest_alerts:

                    display_text = alert.get(
                        "displayText",
                        "Unknown anomaly"
                    )

                    created_at = alert.get(
                        "createdAt"
                    )

                    formatted_time = datetime.fromisoformat(
                        created_at.replace(
                            "Z",
                            "+00:00"
                        )
                    ).strftime(
                        "%d-%m-%Y %I:%M %p"
                    )

                    templates = [

                        f"• {display_text}. Detected on {formatted_time}.",

                        f"• An HLP anomaly was observed: {display_text}. Recorded on {formatted_time}.",

                        f"• Monitoring detected unusual HLP activity: {display_text}. Time: {formatted_time}.",

                        f"• The system flagged the following HLP anomaly: {display_text}. Detected on {formatted_time}.",

                        f"• HLP data analysis identified {display_text}. Event time: {formatted_time}.",

                        f"• An anomaly alert was generated for {display_text}. Recorded on {formatted_time}.",

                        f"• The latest monitoring review detected {display_text}. Logged on {formatted_time}."

                    ]

                    lines.append(
                        random.choice(
                            templates
                        )
                    )

                final_answer = "\n\n".join(
                    lines
                )
                
        # =====================================================
        # ENERGY API
        # LAST 24 + PREVIOUS WEEK
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

            energy_data = get_daily_energy_data(
                token,
                request.clientId
            )

            yesterday_date = (
                get_utc_now() - timedelta(days=1)
            ).date()

            previous_week_date = (
                yesterday_date - timedelta(days=7)
            )

            yesterday_kwh = 0

            last_week_kwh = 0

            total_main_incomer_found = False

            for date_key, machines in energy_data.items():

                try:

                    current_date = datetime.fromisoformat(
                        date_key.replace("Z", "+00:00")
                    ).date()

                    for machine in machines:

                        if machine.get(
                            "groupName"
                        ) == "Tot_Main_Incomer":

                            total_main_incomer_found = True

                        else:

                             continue

                        kwh = float(
                            machine.get(
                                "kwh",
                                0
                            )
                        )

                        if current_date == yesterday_date:

                            yesterday_kwh = kwh

                        elif current_date == previous_week_date:

                            last_week_kwh = kwh

                except:

                    continue
            if not total_main_incomer_found:

                final_answer = (
                    "There is no Total Main Incomer data available."
                )

            else:
                if last_week_kwh == 0:

                    difference_percent = 0

                else:

                    difference_percent = (
                        (
                            yesterday_kwh
                            - last_week_kwh
                        )
                        / last_week_kwh
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
    
                target_day_name = yesterday_date.strftime(
                    "%A"
                )
    
                target_date_str = yesterday_date.strftime(
                    "%d-%m-%Y"
                )
    
                previous_week_date_str = (
                    previous_week_date.strftime(
                        "%d-%m-%Y"
                    )
                )
    
                response_templates = [

    f"""
Energy Consumption Comparison
The facility consumed {yesterday_kwh} kWh on {target_day_name} ({target_date_str}).
For the same day in the previous week ({previous_week_date_str}), the recorded energy consumption was {last_week_kwh} kWh.
Overall energy usage has {trend_sentence} by {abs(difference_percent):.2f}% compared to the same day last week.
""",

    f"""
Building Energy Analysis
On {target_day_name} ({target_date_str}), the building recorded a total energy consumption of {yesterday_kwh} kWh.
During the previous week's {target_day_name} ({previous_week_date_str}), the total energy consumption was {last_week_kwh} kWh.
This indicates a {abs(difference_percent):.2f}% {trend_word} in energy usage.
""",

    f"""
Energy Monitoring Report
The total energy consumed on {target_day_name} ({target_date_str}) was {yesterday_kwh} kWh.
For comparison, the same weekday in the previous week ({previous_week_date_str}) recorded {last_week_kwh} kWh.
Energy consumption has {trend_sentence} by {abs(difference_percent):.2f}% over the corresponding day last week.
""",

    f"""
Facility Energy Summary
Energy consumption for {target_day_name} ({target_date_str}) reached {yesterday_kwh} kWh.
The previous week's {target_day_name} ({previous_week_date_str}) reported a total consumption of {last_week_kwh} kWh.
Compared with the previous week, energy usage shows a {abs(difference_percent):.2f}% {trend_word}.
""",

    f"""
Weekly Energy Comparison
The monitored facility used {yesterday_kwh} kWh on {target_day_name} ({target_date_str}).
On the corresponding day of the previous week ({previous_week_date_str}), energy consumption was {last_week_kwh} kWh.
This reflects an overall {trend_sentence} of {abs(difference_percent):.2f}% in energy consumption.
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

            runtime_breach_alerts = []

            for alert in alerts:

                try:

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

                    trigger_point = float(
                        trigger.get(
                            "triggerPoint",
                            [0]
                        )[0]
                    )

                    if field_value > trigger_point:

                        runtime_breach_alerts.append(
                            alert
                        )

                except:
                    continue

            runtime_breach_alerts.sort(
                key=lambda x: (
                    x.get("alertTimestamp")
                    or x.get("createdAt", "")
                ),
                reverse=True
            )

            alerts = runtime_breach_alerts[:3]

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

            if len(alerts) == 0:

                final_answer = random.choice(
                    NO_ALERT_MESSAGES
                )

            else:

                lines = []

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
