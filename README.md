# Tolo Kabab House AI Receptionist Starter

This folder is a quick starter for a restaurant phone agent focused on `Tolo Kabab House`.

## Included

- `index.html`
  A simple demo page your friend can show to the restaurant.
- `styles.css`
  Visual styling for the prototype page.
- `agent-config/tolo-kabab-house.json`
  A practical agent spec with prompt, tools, and guardrails.
- `app/`
  A Python backend starter for `Twilio Voice + OpenAI Realtime`.
- `data/`
  Local JSON storage for reservations, leads, and escalations.
- `requirements.txt`
  Python dependencies for the backend.
- `.env.example`
  Environment variables to configure the voice agent.

## What is already customized

- Restaurant name: `Tolo Kabab House`
- Use case: restaurant call answering and reservations
- Basic voice behavior and escalation logic
- Reservation intake flow

## What still needs real restaurant data

Before going live, replace placeholders with verified business information:

- exact address
- phone number
- opening hours
- reservation rules
- maximum party size
- waitlist policy
- large-party policy
- menu FAQ
- allergy and dietary guidance approved by the restaurant
- staff transfer number

## Backend architecture

This starter now implements the first real backend step:

1. `Twilio` receives the phone call.
2. Twilio hits `/incoming-call` and is told to open a media stream.
3. The FastAPI backend accepts the Twilio media stream at `/media-stream`.
4. The backend opens an `OpenAI Realtime` WebSocket session.
5. The model uses tools to check availability, create reservations, and capture escalations.
6. Reservation and follow-up records are stored locally in `data/*.json`.

## Quick start

1. Create a virtual environment:
   `python3 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install dependencies:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in the keys.
5. Run the server:
   `uvicorn app.main:app --reload`
6. Expose it publicly for Twilio with a tunnel such as `ngrok`.
7. In Twilio, point the voice webhook to:
   `https://your-public-url/incoming-call`

## Current limitations

- Live staff transfer is captured as a follow-up record, not a warm transfer yet.
- Reservation availability is using a local dev capacity rule, not a real booking system.
- Restaurant facts still need verified real-world data before launch.
- I could not run the full server here because this machine does not have the Python dependencies installed yet.

## Suggested next step

If you want, the next iteration can be one of these:

1. Connect the reservation tool to `Google Sheets` or `Airtable`
2. Add live SMS confirmations after booking
3. Add a manager dashboard for reservations and missed-call leads
