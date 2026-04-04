from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    staff_transfer_number: str = os.getenv("STAFF_TRANSFER_NUMBER", "")
    restaurant_phone_number: str = os.getenv("RESTAURANT_PHONE_NUMBER", "")
    openai_realtime_model: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-1.5")
    openai_voice: str = os.getenv("OPENAI_VOICE", "marin")
    reservation_party_limit: int = int(os.getenv("RESERVATION_PARTY_LIMIT", "8"))
    reservation_slot_capacity: int = int(os.getenv("RESERVATION_SLOT_CAPACITY", "6"))


settings = Settings()
