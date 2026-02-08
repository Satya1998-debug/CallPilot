from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st

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
    use_mcp = st.checkbox("Use MCP/LLM Agent Mode", value=os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"})
    api_url = st.text_input("Backend API URL", value=os.getenv("CALLPILOT_API_URL", "http://localhost:8000"))
    st.info("💡 All queries are processed through the backend API")
    st.divider()
    st.header("Inputs")
    input_mode = st.selectbox("Input mode", ["Text", "Speech"])
    enable_speech = st.checkbox("Enable speech (STT/TTS)", value=False)
    
    if use_mcp:
        # For MCP mode, only show natural language input
        st.info("🤖 MCP Mode: Using LLM agent with tool calling")
        user_text = st.text_area("Tell me what appointment you need", value="book a doctor appointment this week close to me")
        specialty = None
        time_window = None
        radius_km = None
        user_location = None
    else:
        # For local mode, show structured inputs
        st.info("📋 Local Mode: Using structured workflow")
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
    "radius_km": float(radius_km) if radius_km else 5.0,
    "user_location": user_location,
    "user_text": user_text.strip() or None,
}

# Initialize session state
if "mcp_result" not in st.session_state:
    st.session_state.mcp_result = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "proposal_state" not in st.session_state:
    st.session_state.proposal_state = None
if "proposal" not in st.session_state:
    st.session_state.proposal = None
if "final_result" not in st.session_state:
    st.session_state.final_result = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "audio_response" not in st.session_state:
    st.session_state.audio_response = None

# Chat interface
st.subheader("💬 Chat Interface")

# Add clear chat button
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        st.session_state.proposal = None
        st.session_state.proposal_state = None
        st.session_state.mcp_result = None
        st.session_state.final_result = None
        st.rerun()

# Display chat history
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        # Show audio if available
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/mpeg")
        # Show appointment details if available
        if msg.get("appointment"):
            appt = msg["appointment"]
            with st.expander("📋 Appointment Details"):
                st.json(appt)

# Handle audio input for speech mode
if input_mode == "Speech" and enable_speech:
    st.info("🎤 Speech Mode: Upload an audio file or use the chat input below")
    if audio_blob:
        with st.spinner("Transcribing audio..."):
            transcript = _elevenlabs_stt(audio_blob[0], audio_blob[1])
            if transcript:
                # Add transcribed message to chat
                st.session_state.chat_messages.append({"role": "user", "content": transcript})
                payload["user_text"] = transcript
                st.session_state.processing = True
                st.rerun()

# Chat input handling
text_prompt = st.chat_input("Tell me what you want to book..." if use_mcp else "Describe your appointment needs")

def process_user_message(user_message: str):
    """Process user message via backend API and get agent/workflow response."""
    # Add user message to chat
    st.session_state.chat_messages.append({"role": "user", "content": user_message})
    
    assistant_response = None
    appointment_data = None
    audio_data = None
    requires_confirmation = False
    
    with st.spinner("🤖 Processing your request..."):
        try:
            # Send message to backend /chat endpoint
            chat_payload = {
                "message": user_message,
                "use_mcp": use_mcp,
                "conversation_history": []  # Could track full history if needed
            }
            
            resp = requests.post(f"{api_url.rstrip('/')}/chat", json=chat_payload, timeout=120)
            resp.raise_for_status()
            result = resp.json()
            
            # Extract response
            assistant_response = result.get("message", "I've processed your request.")
            appointment_data = result.get("appointment")
            requires_confirmation = result.get("requires_confirmation", False)
            error = result.get("error")
            
            if error:
                assistant_response = f"❌ {assistant_response}"
            
            # Store proposal state for confirmation (local workflow)
            if requires_confirmation and appointment_data:
                st.session_state.proposal = appointment_data
                # Store internal state for confirmation
                if "_state" in appointment_data:
                    st.session_state.proposal_state = appointment_data["_state"]
                    # Remove internal state from display
                    appointment_data = {k: v for k, v in appointment_data.items() if k != "_state"}
            else:
                # Clear proposal state if not needed
                st.session_state.proposal = None
                st.session_state.proposal_state = None
                
        except requests.RequestException as e:
            assistant_response = f"❌ Backend connection error: {str(e)}\n\nPlease ensure the backend API is running on {api_url}"
        except Exception as e:
            assistant_response = f"❌ Error: {str(e)}"

    # Generate speech if enabled
    if enable_speech and assistant_response:
        audio_data = _elevenlabs_tts(assistant_response)
    
    # Add assistant response to chat
    msg_data = {"role": "assistant", "content": assistant_response}
    if appointment_data:
        msg_data["appointment"] = appointment_data
    if audio_data:
        msg_data["audio"] = audio_data
    
    st.session_state.chat_messages.append(msg_data)
    return True

# Process new message if provided
if text_prompt:
    success = process_user_message(text_prompt)
    if success:
        st.rerun()

# Confirmation button for local workflow proposals
if st.session_state.proposal and not use_mcp:
    st.divider()
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Waiting for your confirmation to book this appointment")
        with col2:
            if st.button("✅ Confirm & Book", type="primary", use_container_width=True):
                with st.spinner("Booking appointment..."):
                    try:
                        # Send confirmation to backend
                        confirm_payload = {
                            "provider": st.session_state.proposal_state.get("provider"),
                            "slot": st.session_state.proposal_state.get("chosen_slot"),
                            "specialty": st.session_state.proposal_state.get("specialty"),
                            "transcript": st.session_state.proposal_state.get("transcript", []),
                        }
                        resp = requests.post(f"{api_url.rstrip('/')}/chat/confirm", json=confirm_payload, timeout=120)
                        resp.raise_for_status()
                        result = resp.json()
                        
                        # Extract response
                        success_msg = result.get("message", "✅ Appointment booked successfully!")
                        appointment_result = result.get("appointment")
                        
                        # Add success message to chat
                        msg_data = {"role": "assistant", "content": success_msg}
                        if appointment_result:
                            msg_data["appointment"] = appointment_result
                        
                        if enable_speech:
                            audio = _elevenlabs_tts(success_msg)
                            if audio:
                                msg_data["audio"] = audio
                        
                        st.session_state.chat_messages.append(msg_data)
                        st.session_state.proposal = None
                        st.session_state.proposal_state = None
                        st.rerun()
                        
                    except Exception as e:
                        error_msg = f"❌ Booking failed: {str(e)}"
                        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
                        st.rerun()


st.divider()
