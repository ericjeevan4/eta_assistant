from fastapi import FastAPI
from pydantic import BaseModel
import requests
import time
import random

app = FastAPI()

# =========================
# VALID QUESTION KEYWORDS
# =========================

VALID_KEYWORDS = [
    "unusual energy spikes",
    "highest spikes",
    "unusual spikes"
]

# =========================
# API DETAILS
# =========================

POST_API_URL = "https://test.energyeta.ai/user/login"
GET_API_URL = "https://test.energyeta.ai/machine/getTopEnergyContributedMachines/6475b0fd2bc7715a17864db1?startTime=2025-04-01T08:13:01.177Z&endTime=2025-04-07T08:13:01.177Z"

LOGIN_PAYLOAD = {
    "email": "development@thermelgy.com",
    "password": "admin@123"
}

# =========================
# REQUEST MODEL
# =========================

class QuestionRequest(BaseModel):
    question: str

# =========================
# TOKEN
# =========================

def get_access_token():

    try:

        response = requests.post(
            POST_API_URL,
            json=LOGIN_PAYLOAD
        )

        if response.status_code == 200:

            return response.json()["data"]["accessToken"]

        return None

    except:

        return None

# =========================
# FETCH DATA
# =========================

def fetch_api_data(token):

    try:

        headers = {
            "Authorization": token
        }

        response = requests.get(
            GET_API_URL,
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

# =========================
# PROCESS DATA
# =========================

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

            if name not in machine_history:

                machine_history[name] = []

            machine_history[name].append({
                "date": date,
                "kwh": kwh
            })

    results = []

    for machine_name, history in machine_history.items():

        if len(history) < 2:
            continue

        first = history[0]["kwh"]

        last = history[-1]["kwh"]

        latest_date = history[-1]["date"]

        if first == 0:
            continue

        slope_percent = (
            (last - first) / first
        ) * 100

        if slope_percent > 0:

            results.append({
                "machineName": machine_name,
                "latestDate": latest_date,
                "slopePercent": round(
                    slope_percent,
                    2
                )
            })

    # DESCENDING ORDER
    results.sort(
        key=lambda x: x["slopePercent"],
        reverse=True
    )

    return results[:3]

# =========================
# FORMAT OUTPUT
# =========================

def format_output(top_spikes):

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

            f"• {m['machineName']} recorded a spike increase of {m['slopePercent']}% on {m['latestDate']}.",

            f"• Significant energy growth of {m['slopePercent']}% was detected in {m['machineName']} on {m['latestDate']}.",

            f"• {m['machineName']} showed an unusual energy rise of {m['slopePercent']}% during analysis on {m['latestDate']}.",

            f"• Monitoring identified a {m['slopePercent']}% spike in {m['machineName']} on {m['latestDate']}.",

            f"• {m['machineName']} experienced a notable slope increase of {m['slopePercent']}% on {m['latestDate']}."

        ]

        lines.append(
            random.choice(
                phrase_templates
            )
        )

    return "\n\n".join(lines)

# =========================
# HOME ROUTE
# =========================

@app.get("/")
def home():

    return {
        "message": "ETA FastAPI Running"
    }

# =========================
# MAIN ROUTE
# =========================

@app.post("/predict")
def predict(data: QuestionRequest):

    start = time.time()

    # =========================
    # QUESTION VALIDATION
    # =========================

    question_lower = data.question.lower()

    question_valid = any(
        keyword in question_lower
        for keyword in VALID_KEYWORDS
    )

    if not question_valid:

        return {
            "statusCode": 400,
            "data": {
                "question": data.question,
                "answer": "Unsupported question."
            },
            "msg": "Question validation failed"
        }

    # =========================
    # GET TOKEN
    # =========================

    token = get_access_token()

    if not token:

        return {
            "statusCode": 500,
            "data": {
                "question": data.question,
                "answer": "Token generation failed."
            },
            "msg": "Failed"
        }

    # =========================
    # FETCH API DATA
    # =========================

    api_data = fetch_api_data(
        token
    )

    if not api_data:

        return {
            "statusCode": 500,
            "data": {
                "question": data.question,
                "answer": "API data fetch failed."
            },
            "msg": "Failed"
        }

    # =========================
    # PROCESS TOP SPIKES
    # =========================

    top_spikes = calculate_top_spikes(
        api_data
    )

    # =========================
    # GENERATE HUMAN RESPONSE
    # =========================

    final_output = format_output(
        top_spikes
    )

    print(
        "Total Time:",
        time.time() - start
    )

    # =========================
    # FINAL RESPONSE
    # =========================

    return {
        "statusCode": 200,
        "data": {
            "question": data.question,
            "answer": final_output
        },
        "msg": "Success"
    }

# =========================
# LOCAL RUN
# =========================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860
    )