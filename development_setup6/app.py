from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta, timezone
import random
import json

app = Flask(__name__)

# =====================================
# API DETAILS
# =====================================

POST_LINK = "https://test.energyeta.ai/user/login"
GET_LINK = "https://test.energyeta.ai/alert/getAllAlerts"

EMAIL = "development@thermelgy.com"
PASSWORD = "admin@123"

# =====================================
# KEYWORDS
# =====================================

KEYWORDS = [

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

# =====================================
# RANDOM NO ALERT RESPONSES
# =====================================

NO_ALERT_MESSAGES = [

    "No unusual operating hours were identified in the last 24 hours.",

    "All monitored EA machines operated within expected schedules during the last 24 hours.",

    "No runtime breach alerts were reported for EA machines in the previous 24 hours.",

    "No potential unplanned operational activity was detected recently.",

    "EA machines appear to be functioning within scheduled operating timelines.",

    "No abnormal operational hour patterns were observed in the last 24 hours.",

    "System analysis shows no unusual runtime activity for EA machines.",

    "No unexpected machine runtime behavior was detected during the monitoring period.",

    "The monitoring system did not identify any operational schedule deviations."
]

# =====================================
# RANDOM INTRO SENTENCES
# =====================================

INTRO_MESSAGES = [

    "Potential unplanned operational activity was detected for the following EA machines:",

    "Runtime breach alerts were observed for these EA machines:",

    "The following machines showed unusual operating patterns:",

    "Detected operational hour deviations for the machines below:",

    "The following EA machines exceeded expected runtime schedules:",

    "Monitoring analysis identified unusual operational activity for these machines:",

    "The system detected runtime anomalies for the following EA machines:"
]

# =====================================
# LOGIN FUNCTION
# =====================================

def login():

    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }

    response = requests.post(
        POST_LINK,
        json=login_data
    )

    if response.status_code != 200:
        return None

    result = response.json()

    token = result["data"]["accessToken"]

    return token


# =====================================
# GET CLIENT DETAILS
# =====================================

def get_client_details(client_id):

    login_data = {
        "email": EMAIL,
        "password": PASSWORD
    }

    response = requests.post(
        POST_LINK,
        json=login_data
    )

    if response.status_code != 200:
        return None

    result = response.json()

    clients = result["data"]["user"]["clients"]

    for client in clients:

        if client.get("clientId") == client_id:
            return client

    return None


# =====================================
# EA CLIENT CHECK
# =====================================

def is_ea_client(client_data):

    try:

        configs = client_data.get(
            "userDefinedTableConfig",
            []
        )

        for config in configs:

            operations = config.get(
                "operations",
                []
            )

            for operation in operations:

                val = operation.get(
                    "val",
                    {}
                )

                category_values = val.get(
                    "categoryValue",
                    []
                )

                for item in category_values:

                    machine_type = item.get(
                        "machineType",
                        ""
                    )

                    if machine_type.upper() == "EA":

                        return True

        return False

    except:
        return False


# =====================================
# FILTER LAST 24 HOURS
# =====================================

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


# =====================================
# QUESTION VALIDATION
# =====================================

def is_valid_question(question):

    question = question.lower()

    for keyword in KEYWORDS:

        if keyword in question:
            return True

    return False


# =====================================
# FORMAT DATE TIME
# =====================================

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


# =====================================
# MAIN API
# =====================================

@app.route("/runtime-breach", methods=["POST"])
def runtime_breach():

    try:

        body = request.get_json(force=True)

        client_id = body.get("clientId")

        question = body.get(
            "question",
            ""
        )

        if not client_id:

            return jsonify({
                "statusCode": 400,
                "msg": "clientId is required"
            })

        # =====================================
        # QUESTION VALIDATION
        # =====================================

        if not is_valid_question(question):

            return jsonify({

                "statusCode": 400,

                "data": {

                    "question": question,

                    "answer": (
                        "Please ask questions related "
                        "to unusual operating hours "
                        "or runtime breach."
                    )
                },

                "msg": "Invalid question"
            })

        # =====================================
        # GET CLIENT DETAILS
        # =====================================

        client_data = get_client_details(client_id)

        if not client_data:

            return jsonify({
                "statusCode": 404,
                "msg": "Client not found"
            })

        # =====================================
        # EA CHECK
        # =====================================

        ea_client = is_ea_client(client_data)

        if not ea_client:

            final_response = {

                "statusCode": 403,

                "data": {

                    "question": question,

                    "answer": (
                        "This client is not an EA client. "
                        "Runtime breach analysis is supported "
                        "only for EA machine types."
                    )
                },

                "msg": "Only EA clients allowed"
            }

            return app.response_class(
                response=json.dumps(final_response),
                status=403,
                mimetype='application/json'
            )

        # =====================================
        # LOGIN
        # =====================================

        token = login()

        if not token:

            return jsonify({
                "statusCode": 500,
                "msg": "Login failed"
            })

        # =====================================
        # HEADERS
        # =====================================

        headers = {
            "Authorization": token
        }

        # =====================================
        # PAYLOAD
        # =====================================

        payload = {
            "page": 1,
            "limit": 50,
            "clientId": client_id,
            "search": "",
            "alertType": "schedule"
        }

        # =====================================
        # ALERT API
        # =====================================

        response = requests.post(
            GET_LINK,
            json=payload,
            headers=headers
        )

        if response.status_code != 200:

            return jsonify({
                "statusCode": 500,
                "msg": "Failed to fetch alerts"
            })

        result = response.json()

        alerts = result["data"]["data"]

        # =====================================
        # LAST 24 HOURS
        # =====================================

        alerts = filter_last_24_hours(alerts)

        # =====================================
        # ONLY 3 MACHINES
        # =====================================

        alerts = alerts[:3]

        # =====================================
        # RESPONSE
        # =====================================

        if len(alerts) == 0:

            answer = random.choice(
                NO_ALERT_MESSAGES
            )

        else:

            lines = []

            # RANDOM INTRO
            lines.append(
                random.choice(INTRO_MESSAGES)
            )

            # EXTRA SENTENCES
            lines.append(
                "The analysis below is based on the last 24 hours of runtime breach monitoring data."
            )

            lines.append(
                "Only the top 3 affected EA machines are included in this response."
            )

            # MACHINE DETAILS
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

            answer = "\n\n".join(lines)

        # =====================================
        # FINAL RESPONSE
        # =====================================


        final_response = {

            "statusCode": 200,

            "data": {

                "question": question,

                "answer": answer
            },

            "msg": "Success"
        }

        return app.response_class(
            response=json.dumps(final_response),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:

        return jsonify({
            "statusCode": 500,
            "msg": str(e)
        })


# =====================================
# HOME
# =====================================

@app.route("/")
def home():

    return "API Running Successfully"


# =====================================
# RUN
# =====================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=7860
    )