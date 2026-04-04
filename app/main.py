from __future__ import annotations

import asyncio
import json
from contextlib import suppress

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, Response
import websockets

from app.config import settings
from app.prompts import build_greeting_instruction, build_system_prompt
from app.store import LEADS_PATH, RESERVATIONS_PATH, TRANSFERS_PATH, load_records
from app.tools import TOOLS, run_tool


app = FastAPI(title="Tolo Kabab House AI Receptionist")


OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


def build_twiml_stream_response() -> str:
    stream_url = settings.public_base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}/media-stream" />
  </Connect>
</Response>"""


async def initialize_openai_session(openai_ws) -> None:
    session_update = {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "instructions": build_system_prompt(),
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                        "create_response": True,
                        "interrupt_response": True
                    }
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": settings.openai_voice,
                    "speed": 1
                }
            },
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_output_tokens": 512
        }
    }
    await openai_ws.send(json.dumps(session_update))
    await openai_ws.send(
        json.dumps(
            {
                "type": "response.create",
                "response": {
                    "instructions": build_greeting_instruction()
                }
            }
        )
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/debug/store")
async def debug_store() -> dict:
    return {
        "reservations": load_records(RESERVATIONS_PATH),
        "leads": load_records(LEADS_PATH),
        "transfers": load_records(TRANSFERS_PATH),
    }


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(_: Request) -> Response:
    return Response(content=build_twiml_stream_response(), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()

    if not settings.openai_api_key:
        await websocket.close(code=1011, reason="Missing OPENAI_API_KEY")
        return

    stream_sid = None

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "OpenAI-Beta": "realtime=v1"
    }
    openai_url = f"{OPENAI_REALTIME_URL}?model={settings.openai_realtime_model}"

    async with websockets.connect(openai_url, additional_headers=headers) as openai_ws:
        await initialize_openai_session(openai_ws)

        async def receive_from_twilio() -> None:
            nonlocal stream_sid
            try:
                while True:
                    message_text = await websocket.receive_text()
                    payload = json.loads(message_text)
                    event_type = payload.get("event")

                    if event_type == "start":
                        stream_sid = payload["start"]["streamSid"]
                    elif event_type == "media":
                        await openai_ws.send(
                            json.dumps(
                                {
                                    "type": "input_audio_buffer.append",
                                    "audio": payload["media"]["payload"]
                                }
                            )
                        )
                    elif event_type == "stop":
                        break
            except WebSocketDisconnect:
                pass

        async def send_to_twilio() -> None:
            nonlocal stream_sid
            async for raw_event in openai_ws:
                event = json.loads(raw_event)
                event_type = event.get("type")

                if event_type == "response.output_audio.delta" and stream_sid:
                    await websocket.send_json(
                        {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": event["delta"]
                            },
                        }
                    )
                elif event_type == "input_audio_buffer.speech_started" and stream_sid:
                    await websocket.send_json(
                        {
                            "event": "clear",
                            "streamSid": stream_sid
                        }
                    )
                elif event_type == "response.function_call_arguments.done":
                    tool_name = event["name"]
                    tool_output = run_tool(tool_name, event["arguments"])
                    await openai_ws.send(
                        json.dumps(
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": event["call_id"],
                                    "output": tool_output
                                }
                            }
                        )
                    )
                    await openai_ws.send(json.dumps({"type": "response.create"}))
                elif event_type == "error":
                    print("OpenAI Realtime error:", event)

        receiver = asyncio.create_task(receive_from_twilio())
        sender = asyncio.create_task(send_to_twilio())
        done, pending = await asyncio.wait(
            {receiver, sender},
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        for task in done:
            with suppress(Exception):
                await task


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/")
async def root() -> PlainTextResponse:
    return PlainTextResponse(
        "Tolo Kabab House AI receptionist backend is running. Use /incoming-call for Twilio and /debug/store for local records."
    )
