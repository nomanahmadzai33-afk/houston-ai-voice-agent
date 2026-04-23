from __future__ import annotations

import json
import os
import base64
from collections import Counter
from datetime import datetime, timedelta

from app.config import settings
from app.store import LEADS_PATH, RESERVATIONS_PATH, TRANSFERS_PATH, append_record, load_records, utc_timestamp


TOOLS = [
    {
        "type": "function",
        "name": "check_reservation_availability",
        "description": "Check whether the requested reservation slot is available before making any promise to the caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Reservation date in YYYY-MM-DD format."},
                "time": {"type": "string", "description": "Reservation time in HH:MM format."},
                "party_size": {"type": "integer", "description": "Number of guests."}
            },
            "required": ["date", "time", "party_size"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "create_reservation",
        "description": "Create a reservation after availability has been confirmed.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "party_size": {"type": "integer"},
                "guest_name": {"type": "string"},
                "phone_number": {"type": "string"},
                "special_requests": {"type": "string"}
            },
            "required": ["date", "time", "party_size", "guest_name", "phone_number"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "capture_lead",
        "description": "Capture large-party, catering, or callback requests for staff follow-up.",
        "parameters": {
            "type": "object",
            "properties": {
                "guest_name": {"type": "string"},
                "phone_number": {"type": "string"},
                "reason": {"type": "string"},
                "details": {"type": "string"}
            },
            "required": ["guest_name", "phone_number", "reason"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "transfer_to_staff",
        "description": "Capture a request that should be transferred or escalated to restaurant staff.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "summary": {"type": "string"}
            },
            "required": ["reason", "summary"],
            "additionalProperties": False
        }
    }
]


def _validate_datetime(date_value: str, time_value: str) -> None:
    datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")


def _slot_count(date_value: str, time_value: str) -> int:
    reservations = load_records(RESERVATIONS_PATH)
    booked = [r for r in reservations if r["date"] == date_value and r["time"] == time_value]
    return len(booked)


def _suggest_alternatives(date_value: str, time_value: str) -> list[str]:
    hour, minute = [int(part) for part in time_value.split(":")]
    candidates = []
    for delta in (-30, 30, 60):
        total_minutes = hour * 60 + minute + delta
        if total_minutes <= 0:
            continue
        alt_hour = total_minutes // 60
        alt_minute = total_minutes % 60
        candidates.append(f"{alt_hour:02d}:{alt_minute:02d}")
    counts = Counter({candidate: _slot_count(date_value, candidate) for candidate in candidates})
    return [candidate for candidate, count in counts.items() if count < settings.reservation_slot_capacity][:2]


def add_to_google_calendar(record: dict) -> None:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        token_data = os.environ.get('GOOGLE_CALENDAR_TOKEN')
        if not token_data:
            print("No GOOGLE_CALENDAR_TOKEN found, skipping Calendar.")
            return

        creds = service_account.Credentials.from_service_account_info(
            json.loads(base64.b64decode(token_data).decode()),
            ['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)

        start_dt = datetime.strptime(f"{record['date']} {record['time']}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1, minutes=30)

        event = {
            'summary': f"Reservation - {record['guest_name']} (Party of {record['party_size']})",
            'description': (
                f"Guest: {record['guest_name']}\n"
                f"Phone: {record['phone_number']}\n"
                f"Party size: {record['party_size']}\n"
                f"Special requests: {record.get('special_requests', 'None')}\n"
                f"Booked via: AI Voice Agent"
            ),
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'UTC'},
        }

        service.events().insert(calendarId='nomanahmadzai33@gmail.com', body=event).execute()
        print(f"✅ Calendar event created for {record['guest_name']}")

    except Exception as e:
        print(f"Calendar error (non-fatal): {e}")


def check_reservation_availability(arguments: dict) -> dict:
    date_value = arguments["date"]
    time_value = arguments["time"]
    party_size = int(arguments["party_size"])
    _validate_datetime(date_value, time_value)

    if party_size > settings.reservation_party_limit:
        return {
            "available": False,
            "reason": "party_size_limit",
            "message": (
                f"Parties above {settings.reservation_party_limit} guests need staff approval. "
                "Please capture a lead for follow-up."
            )
        }

    booked_count = _slot_count(date_value, time_value)
    if booked_count >= settings.reservation_slot_capacity:
        return {
            "available": False,
            "reason": "slot_full",
            "message": "That slot is currently full.",
            "alternatives": _suggest_alternatives(date_value, time_value)
        }

    return {
        "available": True,
        "message": "The slot is currently available."
    }


def create_reservation(arguments: dict) -> dict:
    availability = check_reservation_availability(arguments)
    if not availability["available"]:
        return {
            "created": False,
            "reason": availability["reason"],
            "message": "Reservation was not created because the slot is unavailable.",
            "availability": availability
        }

    record = {
        "id": f"res_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "date": arguments["date"],
        "time": arguments["time"],
        "party_size": int(arguments["party_size"]),
        "guest_name": arguments["guest_name"].strip(),
        "phone_number": arguments["phone_number"].strip(),
        "special_requests": arguments.get("special_requests", "").strip(),
        "created_at": utc_timestamp()
    }
    append_record(RESERVATIONS_PATH, record)
    add_to_google_calendar(record)
    return {
        "created": True,
        "reservation": record,
        "message": "Reservation successfully created and saved to Google Calendar."
    }


def capture_lead(arguments: dict) -> dict:
    record = {
        "id": f"lead_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "guest_name": arguments["guest_name"].strip(),
        "phone_number": arguments["phone_number"].strip(),
        "reason": arguments["reason"].strip(),
        "details": arguments.get("details", "").strip(),
        "created_at": utc_timestamp()
    }
    append_record(LEADS_PATH, record)
    return {
        "captured": True,
        "lead": record,
        "message": "Lead captured for staff follow-up."
    }


def transfer_to_staff(arguments: dict) -> dict:
    record = {
        "id": f"transfer_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "reason": arguments["reason"].strip(),
        "summary": arguments["summary"].strip(),
        "staff_transfer_number": settings.staff_transfer_number,
        "created_at": utc_timestamp()
    }
    append_record(TRANSFERS_PATH, record)
    return {
        "captured": True,
        "live_transfer_configured": bool(settings.staff_transfer_number),
        "message": "Escalation request captured.",
        "transfer": record
    }


TOOL_HANDLERS = {
    "check_reservation_availability": check_reservation_availability,
    "create_reservation": create_reservation,
    "capture_lead": capture_lead,
    "transfer_to_staff": transfer_to_staff,
}


def run_tool(tool_name: str, arguments_json: str) -> str:
    handler = TOOL_HANDLERS[tool_name]
    arguments = json.loads(arguments_json or "{}")
    result = handler(arguments)
    return json.dumps(result)
