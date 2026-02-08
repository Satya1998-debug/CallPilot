# CallPilot — AI-Powered Appointment Booking System

**ElevenLabs AI Voice Integration • LangGraph Agentic Workflow**

> An intelligent appointment booking system combining voice input, natural language processing, and agentic workflows to automatically find and book appointments with healthcare providers based on your preferences, calendar, and location.

## 🎯 Features

- 🎤 **Voice Input** - Real-time microphone recording with ElevenLabs Speech-to-Text
- 🗣️ **Text-to-Speech** - Optional voice responses using ElevenLabs TTS
- 🤖 **Agentic Workflow** - LangGraph-powered decision making with tool calling
- 📅 **Calendar Integration** - Google Calendar availability checking
- 🗺️ **Location-Based Search** - Google Places & Maps API integration
- 🏥 **Provider Matching** - Smart scoring algorithm for optimal provider selection
- 💬 **Interactive Chat** - Streamlit-based conversational UI
- 🔄 **Dual Modes** - MCP/LLM Agent mode or Local workflow mode

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- ElevenLabs API key ([Get one here](https://elevenlabs.io))
- Google Maps API key (optional, for location features)

### Installation

1. **Clone and navigate to the project**
   ```bash
   cd /path/to/CallPilot
   ```

2. **Create and activate virtual environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```bash
   # Required
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   ELEVENLABS_STT_MODEL_ID=scribe_v1
   
   # Optional - for advanced features
   ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
   ELEVENLABS_MODEL_ID=eleven_multilingual_v2
   GOOGLE_MAPS_API_KEY=your_google_maps_key
   
   # API Configuration
   CALLPILOT_API_URL=http://localhost:8001
   
   # Mode Selection
   USE_MCP=true  # Use LLM agent mode (true) or local workflow (false)
   LLM_PROVIDER=ollama  # or openai, anthropic
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:14b
   ```

5. **Install audio recording package**
   ```bash
   pip install audio-recorder-streamlit
   ```

### Running the Application

**Start the FastAPI backend (Terminal 1)**
```bash
python api.py
# Or with uvicorn:
uvicorn api:app --reload --host 0.0.0.0 --port 8001
```

**Start the Streamlit frontend (Terminal 2)**
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 📁 Project Structure

```
CallPilot/
├── api.py                      # FastAPI backend server
├── app.py                      # Streamlit frontend UI
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create this)
├── README.md                   # This file
├── ROADMAP.md                 # Development roadmap
│
├── callpilot/                 # Main package
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── state.py               # Agent state definitions
│   ├── graph.py               # LangGraph workflow orchestration
│   ├── run.py                 # Workflow execution logic
│   ├── viz.py                 # Graph visualization
│   ├── mcp_server.py          # MCP server implementation
│   ├── mcp_client.py          # MCP client
│   │
│   ├── data/
│   │   └── providers.json     # Sample provider database
│   │
│   ├── tools/                 # Agentic tools
│   │   ├── calendar.py        # Calendar availability
│   │   ├── providers.py       # Provider search & filtering
│   │   └── scoring.py         # Provider ranking algorithm
│   │
│   ├── adapters/
│   │   └── receptionist_sim.py # Simulated receptionist
│   │
│   └── integrations/          # External API integrations
│       ├── google_calendar.py
│       ├── google_maps.py
│       └── google_places.py
│
├── test_elevenlabs_stt.py     # ElevenLabs STT testing script
├── test_google_apis.py         # Google APIs testing
├── test_mcp_cache.py           # MCP cache testing
└── test_structure.py           # Package structure validation
```

---

## 🎮 How to Use

### 1. **Chat Interface (Text Input)**
- Type your appointment request in the chat input
- Example: "Book a dentist appointment this week in Berlin"
- The system searches providers, checks availability, and proposes options

### 2. **Voice Input**
- Click the 🎤 microphone button below the chat
- Speak your request (e.g., "I need a doctor appointment tomorrow afternoon")
- Click the mic again to stop recording
- Audio is transcribed automatically and processed

### 3. **Mode Selection (Sidebar)**
- **MCP/LLM Agent Mode**: Uses AI to interpret natural language and make decisions
- **Local Workflow Mode**: Structured input with specialty, time, location

### 4. **Speech Output (Optional)**
- Enable "Enable speech (STT/TTS)" in sidebar
- Assistant responses will include audio playback

---

## 🔧 Key Technologies

### Voice & AI
- **ElevenLabs**: Speech-to-Text (`scribe_v1`) and Text-to-Speech
- **LangGraph**: Agentic workflow orchestration
- **LangChain**: LLM integration and tool calling

### Backend & APIs
- **FastAPI**: REST API server with async support
- **Google Calendar API**: Availability checking
- **Google Places API**: Provider search
- **Google Maps API**: Distance calculation

### Frontend & UI
- **Streamlit**: Interactive web interface
- **audio-recorder-streamlit**: Real-time microphone recording
- **Requests**: HTTP client for backend communication

### Data & ML
- **Pandas**: Data processing
- **NumPy**: Numerical operations
- **ChromaDB**: Vector database (optional)

---

## 📡 API Endpoints

The FastAPI backend exposes these endpoints:

### Health Check
```bash
GET /health
# Returns: {"status": "ok"}
```

### Chat Interface
```bash
POST /chat
{
  "message": "Book a dentist appointment this week",
  "use_mcp": true
}
# Returns: ChatResponse with appointment proposal or confirmation
```

### Run Full Workflow
```bash
POST /run
{
  "specialty": "dentist",
  "time_window": "this week afternoons",
  "radius_km": 5.0,
  "user_location": "Berlin"
}
```

### Propose Appointment
```bash
POST /propose
# Returns: Proposed appointment with provider and slot details
```

### Confirm Booking
```bash
POST /confirm
{
  "provider": {...},
  "slot": {...}
}
# Returns: Confirmation with calendar event ID
```

### Confirm from Chat
```bash
POST /chat/confirm
# Confirms a previously proposed appointment
```

---

## 🧪 Testing

### Test ElevenLabs STT
```bash
python test_elevenlabs_stt.py

# Generate test audio and transcribe
python test_elevenlabs_stt.py --generate
```

### Test Google APIs
```bash
python test_google_apis.py
```

### Test Package Structure
```bash
python test_structure.py
```

### Test MCP Cache
```bash
python test_mcp_cache.py
```

---

## 🔍 Troubleshooting

### Voice Recording Not Working

**Issue**: Warning "Voice recording not available"

**Solution**:
```bash
# Ensure package is installed in correct Python environment
which python3  # Check your Python path
python3 -m pip install audio-recorder-streamlit

# Restart Streamlit
streamlit run app.py
```

### STT Transcription Fails

**Issue**: "Transcription error" or API errors

**Solutions**:
1. Check API key in `.env`
2. Verify model ID: `ELEVENLABS_STT_MODEL_ID=scribe_v1`
3. Test with: `python test_elevenlabs_stt.py`
4. Check available models: `scribe_v1`, `scribe_v1_experimental`, `scribe_v2`

### Backend Connection Error

**Issue**: "Backend connection error" in UI

**Solution**:
```bash
# Ensure backend is running
python api.py
# Or
uvicorn api:app --reload --host 0.0.0.0 --port 8001

# Check backend URL in .env matches
CALLPILOT_API_URL=http://localhost:8001
```

### Port Already in Use

**Solution**:
```bash
# Kill existing process
lsof -ti:8001 | xargs kill -9  # Backend
lsof -ti:8501 | xargs kill -9  # Frontend

# Or use different ports
uvicorn api:app --port 8002
streamlit run app.py --server.port 8502
```

---

## 📚 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | ✅ | - | ElevenLabs API key |
| `ELEVENLABS_STT_MODEL_ID` | ✅ | `scribe_v1` | STT model (`scribe_v1`, `scribe_v2`) |
| `ELEVENLABS_VOICE_ID` | ❌ | `JBFqnCBsd...` | TTS voice ID |
| `ELEVENLABS_MODEL_ID` | ❌ | `eleven_multilingual_v2` | TTS model |
| `GOOGLE_MAPS_API_KEY` | ❌ | - | For location features |
| `CALLPILOT_API_URL` | ✅ | `http://localhost:8001` | Backend API URL |
| `USE_MCP` | ❌ | `true` | Enable MCP/LLM agent mode |
| `LLM_PROVIDER` | ❌ | `ollama` | LLM provider (ollama/openai/anthropic) |
| `OLLAMA_BASE_URL` | ❌ | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | ❌ | `qwen2.5:14b` | Ollama model name |

---

## 🎯 Workflow Modes

### MCP/LLM Agent Mode (`USE_MCP=true`)
- Natural language understanding
- Automatic parameter extraction
- Tool calling for calendar, maps, search
- Context-aware decision making
- Direct booking without confirmation

### Local Workflow Mode (`USE_MCP=false`)
- Structured input (specialty, time, location, radius)
- Proposal-confirmation flow
- Requires explicit user confirmation
- More predictable behavior

---

## 🔐 Security Notes

- Never commit `.env` file to git
- Rotate API keys regularly
- Use environment variables for all secrets
- Google Calendar uses OAuth2 - credentials stored in `secrets/`

---

## 📈 Future Enhancements

- [ ] Multi-provider parallel calling
- [ ] Voice conversation mode (full duplex)
- [ ] Historical booking analytics
- [ ] Provider preference learning
- [ ] SMS/Email confirmations
- [ ] Rescheduling support
- [ ] Multi-language support
- [ ] Mobile app integration

---

## 📖 Documentation

- [ROADMAP.md](ROADMAP.md) - Development roadmap and features
- [setup.md](setup.md) - Detailed setup instructions
- [ElevenLabs Docs](https://elevenlabs.io/docs) - Voice AI documentation
- [LangGraph Guide](https://python.langchain.com/docs/langgraph) - Agent orchestration

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👥 Authors

Built for the MIT Global AI Hackathon 2026 - ElevenLabs Challenge

---

**Questions or issues?** Check the troubleshooting section or open an issue on GitHub.

**Ready to book your next appointment with AI? Let's go! 🚀**
