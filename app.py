from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st

from callpilot.graph import run_local_proposal, confirm_local_booking

st.set_page_config(page_title="CallPilot", page_icon="📞", layout="wide")

st.title("CallPilot")
st.caption("Agentic appointment booking demo")


def _elevenlabs_tts(text: str) -> Optional[bytes]:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
            model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            output_format=os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128"),
        )
        if isinstance(audio, (bytes, bytearray)):
            return bytes(audio)
        # Stream/generator fallback
        return b"".join(audio)
    except Exception:
        return None


def _elevenlabs_stt(audio_bytes: bytes, mime_type: str) -> Optional[str]:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        # Best-effort: API may differ; handle missing gracefully.
        stt = getattr(client, "speech_to_text", None)
        if stt and hasattr(stt, "convert"):
            result = stt.convert(audio=audio_bytes, mime_type=mime_type)
            if isinstance(result, dict) and "text" in result:
                return result["text"]
            if hasattr(result, "text"):
                return result.text
        return None
    except Exception:
        return None


def _render_proposal(proposal: Dict[str, Any]) -> None:
    if proposal.get("error"):
        st.error(proposal["error"])
        return
    provider = proposal.get("provider") or {}
    slot = proposal.get("slot") or {}
    st.markdown("**Proposed appointment**")
    st.write(
        {
            "provider": provider.get("name"),
            "address": provider.get("address"),
            "rating": provider.get("rating"),
            "distance_km": provider.get("distance_km"),
            "start": slot.get("start"),
            "end": slot.get("end"),
            "calendar_ok": proposal.get("calendar_ok"),
        }
    )


with st.sidebar:
    st.header("Run Mode")
    use_api = st.checkbox("Use FastAPI backend", value=False)
    api_url = st.text_input("API URL", value=os.getenv("CALLPILOT_API_URL", "http://localhost:8000"))
    st.divider()
    st.header("Inputs")
    input_mode = st.selectbox("Input mode", ["Text", "Speech"])
    enable_speech = st.checkbox("Enable speech (STT/TTS)", value=False)
    specialty = st.text_input("Specialty", value="dentist")
    time_window = st.text_input("Time window", value="this week afternoons")
    radius_km = st.number_input("Radius (km)", min_value=1.0, max_value=50.0, value=5.0, step=1.0)
    user_location = st.text_input("Location", value="Berlin")
    user_text = st.text_area("Natural language request (optional)", value="")


audio_blob: Optional[Tuple[bytes, str]] = None
if input_mode == "Speech":
    st.subheader("Speech Input")
    audio_file = st.file_uploader("Upload audio (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])
    if audio_file is not None:
        audio_blob = (audio_file.read(), audio_file.type or "audio/wav")
        st.audio(audio_blob[0], format=audio_blob[1])


payload: Dict[str, Any] = {
    "specialty": specialty,
    "time_window": time_window,
    "radius_km": float(radius_km),
    "user_location": user_location,
    "user_text": user_text.strip() or None,
}

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "proposal_state" not in st.session_state:
    st.session_state.proposal_state = None
if "proposal" not in st.session_state:
    st.session_state.proposal = None
if "final_result" not in st.session_state:
    st.session_state.final_result = None

st.subheader("Chat")
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

text_prompt = st.chat_input("Tell me what you want to book")
if text_prompt:
    st.session_state.chat_messages.append({"role": "user", "content": text_prompt})
    payload["user_text"] = text_prompt

run = st.button("Find Appointment", type="primary")

if run:
    with st.spinner("Running workflow..."):
        if input_mode == "Speech" and enable_speech and audio_blob:
            transcript = _elevenlabs_stt(audio_blob[0], audio_blob[1])
            if transcript:
                payload["user_text"] = transcript
                st.session_state.chat_messages.append({"role": "user", "content": transcript})
                st.info(f"Transcribed: {transcript}")
            else:
                st.warning("Speech transcription unavailable; using structured inputs.")

        if use_api:
            try:
                resp = requests.post(f"{api_url.rstrip('/')}/propose", json=payload, timeout=120)
                resp.raise_for_status()
                body = resp.json()
                proposal = body.get("proposal", {})
                st.session_state.proposal = proposal
                st.session_state.proposal_state = body.get("state", {})
            except Exception as e:
                st.error(f"API error: {e}")
                st.stop()
        else:
            init_state: Dict[str, Any] = {
                "specialty": payload["specialty"],
                "time_window": payload["time_window"],
                "radius_km": payload["radius_km"],
                "user_location": payload["user_location"],
                "transcript": [],
                "use_speech": False,
                "user_text": payload["user_text"],
            }
            state = run_local_proposal(init_state)
            st.session_state.proposal = state.get("proposal", {})
            st.session_state.proposal_state = {
                "provider": state.get("provider"),
                "chosen_slot": state.get("chosen_slot"),
                "specialty": state.get("specialty"),
                "transcript": state.get("transcript", []),
            }

        st.session_state.final_result = None

if st.session_state.proposal:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Proposal")
        _render_proposal(st.session_state.proposal)
    with col2:
        st.subheader("Transcript")
        transcript = st.session_state.proposal.get("transcript", [])
        if not transcript:
            st.info("No transcript returned")
        else:
            st.code("\n".join(transcript))

    confirm = st.button("Confirm & Book", type="secondary")
    if confirm:
        with st.spinner("Confirming appointment..."):
            if use_api:
                try:
                    confirm_payload = {
                        "provider": st.session_state.proposal_state.get("provider"),
                        "slot": st.session_state.proposal_state.get("chosen_slot"),
                        "specialty": st.session_state.proposal_state.get("specialty"),
                        "transcript": st.session_state.proposal_state.get("transcript", []),
                    }
                    resp = requests.post(f"{api_url.rstrip('/')}/confirm", json=confirm_payload, timeout=120)
                    resp.raise_for_status()
                    st.session_state.final_result = resp.json().get("result", {})
                except Exception as e:
                    st.error(f"API error: {e}")
                    st.stop()
            else:
                final_state = confirm_local_booking(st.session_state.proposal_state)
                result = final_state.get("result", final_state) if isinstance(final_state, dict) else final_state
                st.session_state.final_result = result

if st.session_state.final_result:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Final Result")
        st.json(st.session_state.final_result)
    with col2:
        st.subheader("Transcript")
        transcript = st.session_state.final_result.get("transcript", []) if isinstance(st.session_state.final_result, dict) else []
        if not transcript:
            st.info("No transcript returned")
        else:
            st.code("\n".join(transcript))

    if enable_speech:
        result_text = None
        if isinstance(st.session_state.final_result, dict):
            if "result_text" in st.session_state.final_result:
                result_text = st.session_state.final_result["result_text"]
            elif "provider" in st.session_state.final_result and "slot" in st.session_state.final_result:
                provider = st.session_state.final_result.get("provider", {})
                slot = st.session_state.final_result.get("slot", {})
                result_text = (
                    f"Appointment booked with {provider.get('name', 'the provider')} "
                    f"at {slot.get('start', 'the selected time')}."
                )
        if result_text:
            audio = _elevenlabs_tts(result_text)
            if audio:
                st.audio(audio, format="audio/mpeg")
            else:
                st.info("Speech output unavailable (missing ElevenLabs or API key).")


st.divider()
st.markdown("""
**How to run**

1. Start API (optional):
```bash
uvicorn api:app --reload
```

2. Start UI:
```bash
streamlit run app.py
```
""")
