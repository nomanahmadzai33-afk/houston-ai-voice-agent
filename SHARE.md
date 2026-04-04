# Share This Project

Share these files and folders:

- `index.html`
- `styles.css`
- `README.md`
- `requirements.txt`
- `.env.example`
- `agent-config/`
- `app/`
- `data/`

Do not share:

- `.env`
- `.venv/`

## Main code files

- `app/main.py`
  FastAPI server, Twilio webhook, Twilio media stream, OpenAI Realtime bridge
- `app/tools.py`
  Reservation, lead capture, and escalation tools
- `app/prompts.py`
  Restaurant system prompt and greeting
- `app/config.py`
  Environment variable loading
- `agent-config/tolo-kabab-house.json`
  Restaurant agent behavior and guardrails

## Run after sharing

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
