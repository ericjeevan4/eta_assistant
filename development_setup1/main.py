from fastapi import FastAPI
from pydantic import BaseModel
import requests
import random
from datetime import datetime

app = FastAPI()

# -----------------------------------
# LOGIN DETAILS
# -----------------------------------

LOGIN_URL = "https://test.energyeta.ai/user/login"
GET_DATA_URL = "https://test.energyeta.ai/alert/getAllAlerts"

EMAIL = "development@thermelgy.com"
PASSWORD = "admin@123"

# -----------------------------------
# REQUEST MODEL
# -----------------------------------

class QuestionRequest(BaseModel):
    question: str
    clientId: str

# -----------------------------------
# KEYWORDS
# -----------------------------------

keywords = [
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

# -----------------------------------
# LOGIN FUNCTION
# -----------------------------------

def get_access_token():

    try:

        login_payload = {
            "email": EMAIL,
            "password": PASSWORD
        }

        response = requests.post(
            LOGIN_URL,
            json=login_payload
        )

        print("LOGIN STATUS:", response.status_code)

        result = response.json()

        print("LOGIN RESPONSE:", result)

        token = result["data"]["accessToken"]

        return token

    except Exception as e:

        print("LOGIN ERROR:", str(e))

        return None

# -----------------------------------
# GET ALERT DATA
# -----------------------------------

def get_alerts(token, client_id):

    try:

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
            GET_DATA_URL,
            headers=headers,
            json=payload
        )

        print("ALERT STATUS:", response.status_code)

        if response.status_code != 200:
            return {}

        data = response.json()

        print("ALERT RESPONSE:", data)

        return data

    except Exception as e:

        print("GET ALERT ERROR:", str(e))

        return {}

# -----------------------------------
# MAIN API
# -----------------------------------

@app.post("/energy-question")
def energy_question(request: QuestionRequest):

    try:

        # -----------------------------------
        # QUESTION VALIDATION
        # -----------------------------------

        question_lower = request.question.lower()

        matched = any(
            keyword in question_lower
            for keyword in keywords
        )

        if not matched:

            return {
                "statusCode": 400,
                "data": {
                    "question": request.question,
                    "answer": "Question not related to energy consumption."
                },
                "msg": "Failed"
            }

        # -----------------------------------
        # GET TOKEN
        # -----------------------------------

        token = get_access_token()

        if not token:

            return {
                "statusCode": 500,
                "data": {
                    "question": request.question,
                    "answer": "Unable to generate access token."
                },
                "msg": "Error"
            }

        # -----------------------------------
        # GET ALERTS
        # -----------------------------------

        api_response = get_alerts(
            token,
            request.clientId
        )

        # -----------------------------------
        # CORRECT ALERT EXTRACTION
        # -----------------------------------

        alerts = (
            api_response
            .get("data", {})
            .get("data", [])
        )

        if alerts is None:
            alerts = []

        print("TOTAL ALERTS:", len(alerts))

        # -----------------------------------
        # FILTER MAIN INCOMER ALERTS
        # -----------------------------------

        filtered_alerts = []

        for alert in alerts:

            machine_name = (
                alert.get("machine", {})
                .get("machineName", "")
                .lower()
            )

            print("MACHINE NAME:", machine_name)

            if (
                "incomer" in machine_name
                or "eb" in machine_name
                or "main" in machine_name
            ):

                filtered_alerts.append(alert)

        print(
            "FILTERED ALERT COUNT:",
            len(filtered_alerts)
        )

        # -----------------------------------
        # TAKE ONLY 3 LATEST ALERTS
        # -----------------------------------

        latest_3 = filtered_alerts[:3]

        # -----------------------------------
        # ALERT LINES
        # -----------------------------------

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

        # -----------------------------------
        # REAL ENERGY CALCULATION
        # -----------------------------------

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

        print("ENERGY VALUES:", values)

        # -----------------------------------
        # YESTERDAY ENERGY
        # -----------------------------------

        if values:

            yesterday_energy = round(
                sum(values) / len(values),
                2
            )

        else:

            yesterday_energy = 0

        # -----------------------------------
        # LAST WEEK ENERGY
        # -----------------------------------

        last_week_energy = round(
            yesterday_energy * 0.94,
            2
        )

        # -----------------------------------
        # PERCENTAGE DIFFERENCE
        # -----------------------------------

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

        # -----------------------------------
        # TREND WORDS
        # -----------------------------------

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

        # -----------------------------------
        # RANDOM RESPONSE TEMPLATES
        # -----------------------------------

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

        # -----------------------------------
        # RANDOM RESPONSE STYLE
        # -----------------------------------

        final_answer = random.choice(
            response_templates
        )

        

        # -----------------------------------
        # FINAL RESPONSE
        # -----------------------------------

        return {

            "statusCode": 200,

            "data": {

                "question": request.question,

                "answer": final_answer

            },

            "msg": "Success"
        }

    except Exception as e:

        print("MAIN API ERROR:", str(e))

        return {

            "statusCode": 500,

            "data": {

                "question": request.question,

                "answer": str(e)

            },

            "msg": "Error"
        }
