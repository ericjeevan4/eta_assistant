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

def get_spike_api_url():

    today = get_utc_now()

    current_date = today.strftime("%Y-%m-%d")

    start_time = f"{current_date}T00:00:00.000Z"

    end_time = f"{current_date}T23:55:00.000Z"

    return (
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
