# CallPilot — Agentic Voice AI for Autonomous Appointment Scheduling

**MIT Global AI Hackathon 2026 • ElevenLabs Challenge**

> An AI voice agent that autonomously calls service providers, negotiates appointment slots, and finds the optimal match based on your calendar, location, and preferences.

## 🎯 Challenge Goal

Build a system that can:
- ✨ Call multiple providers simultaneously (up to 15 parallel calls)
- 🗣️ Negotiate appointments in natural conversation using ElevenLabs Voice AI
- 🧠 Use agentic tool calling to check calendars, calculate distances, and make decisions
- 📊 Rank providers by availability, rating, distance, and preferences
- ✅ Book the optimal appointment automatically

**[See Full Implementation Roadmap →](ROADMAP.md)**

---

## Platform & Setup

**Platform:** macOS (Intel/Apple Silicon)

## Quick Start with Conda

### 1. Install Conda (skip if already installed)
If you already have conda, skip to step 2. Otherwise:
```bash
# Download Miniforge (recommended for Mac, especially M1/M2)
brew install --cask miniforge

# OR download from: https://github.com/conda-forge/miniforge
```

### 2. Install System Dependencies (macOS)
```bash
# Required for audio playback (ElevenLabs, etc.)
brew install ffmpeg
```

### 3. Create Environment
```bash
conda create -n HackNation26 python=3.11 -y
conda activate HackNation26

# install core scientific packages first to avoid conflicts
conda install numpy pandas scikit-learn -y

# Install PyTorch (automatically detects MPS for M1/M2)
conda install pytorch torchvision -c pytorch -y

# Install remaining packages via pip
pip install -r requirements.txt
pip install elevenlabs python-dotenv
brew install graphviz # for visualizing LangGraph workflows
pip install pydot
conda install pygraphviz

```

**Note for M1/M2 Macs:** PyTorch will use Metal Performance Shaders (MPS) for GPU acceleration automatically.

### 4. Set Up API Keys
Create a `.env` file in the project root:
```bash
# Core (Required)
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional (for advanced features)
OPENAI_API_KEY=your_openai_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
```

Get your ElevenLabs API key: https://elevenlabs.io

### 5. Test Installation
```bash
# Test package imports
python test_structure.py

# Test CallPilot structure
python -m src.callpilot.run
```

---

## 🚀 Project Structure

```
src/callpilot/
├── __init__.py              # Package exports
├── config.py                # API key configuration
├── state.py                 # Agent state management
├── graph.py                 # LangGraph workflow orchestration
├── run.py                   # Main entry point
├── data/
│   └── providers.json       # Provider database (4 sample doctors)
├── tools/
│   ├── providers.py         # Provider search & filtering
│   ├── calendar.py          # Date/time & availability logic
│   └── scoring.py           # Provider matching & ranking
└── adapters/
    ├── receptionist_sim.py  # Simulated phone calls (demo)
    └── elevenlabs_adapter.py # (TODO) Real ElevenLabs integration
```

---

## 💡 Next Steps

1. **Test Current Demo:**
   ```bash
   python -m src.callpilot.run
   ```

2. **Implement ElevenLabs Integration:**
   - See [ROADMAP.md](ROADMAP.md) Phase 1.1
   - Create `src/callpilot/adapters/elevenlabs_adapter.py`

3. **Add Google Calendar:**
   - Follow [ROADMAP.md](ROADMAP.md) Phase 1.3
   - OAuth2 setup for calendar access

4. **Build Swarm Mode:**
   - Phase 2: Parallel call orchestration
   - Handle 15 concurrent calls

5. **Create Streamlit UI:**
   - Real-time call status dashboard
   - Live transcript streaming

**[Full Roadmap & Implementation Plan →](ROADMAP.md)**

---

## 🎮 Quick Demo

### Run Streamlit App (when implemented)
```bash
streamlit run app.py
```

### Test Single Call Flow
```bash
python -m src.callpilot.run
```

### Test Provider Matching
```bash
python -c "
from src.callpilot.tools import load_providers, rank_providers

providers = load_providers()
preferences = {
    'specialty': 'cardiology',
    'insurance': 'Blue Cross',
    'language': 'English'
}
ranked = rank_providers(providers, preferences)
print(f'Top match: {ranked[0][\"name\"]} (Score: {ranked[0][\"match_score\"]:.1f})')
"
```

## 🔧 Key Technologies

**Voice & Conversation:**
- ElevenLabs Conversational AI (WebSocket voice streaming)
- ElevenLabs Agentic Functions (tool calling)

**Agent Orchestration:**
- LangGraph (workflow state management)
- LangChain (LLM integration)

**External Integrations:**
- Google Calendar API (availability checking)
- Google Places API (provider search & ratings)
- Google Maps Distance Matrix (travel time)

**Backend & UI:**
- FastAPI (REST API)
- Streamlit (real-time dashboard)
- AsyncIO (parallel call handling)

**ML/Data:**
- NumPy, Pandas (data processing)
- Sentence-Transformers (semantic matching)
- ChromaDB (vector search for providers)

---

## 📊 Evaluation Criteria

Based on hackathon judging:

1. **Conversational Quality (30%)**
   - Natural voice interaction
   - Interruption handling
   - <1 second latency
   
2. **Agentic Functions (25%)**
   - Effective tool orchestration
   - Smart decision-making
   - Dynamic adaptation

3. **Match Quality (20%)**
   - Optimal provider recommendation
   - Accurate scoring algorithm
   
4. **Parallelization (15%)**
   - Concurrent call handling
   - Failure recovery
   
5. **User Experience (10%)**
   - Intuitive interface
   - Clear status updates
   - Seamless booking flow

---

## Troubleshooting

**Issue:** Package conflicts  
**Fix:** Use conda for core scientific packages
```bash
conda install numpy pandas scikit-learn -c conda-forge -y
pip install -r requirements.txt
```

**Issue:** Slow installation on M1/M2  
**Fix:** Use Miniforge (arm64-native conda) instead of Anaconda
```bash
brew install --cask miniforge
```

**Issue:** PyTorch not using GPU on M1/M2  
**Fix:** Check MPS availability
```bash
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

## Notes
- **Mac M1/M2:** Use Miniforge for native ARM64 support
- **Mac Intel:** Standard conda/pip works fine
- For production: Pin exact versions with `pip freeze > requirements-lock.txt`
- MPS (Metal) acceleration is automatic on M1/M2 with PyTorch 2.0+

---

## 📚 Resources

- **[Implementation Roadmap](ROADMAP.md)** — Detailed implementation plan
- **[ElevenLabs Docs](https://elevenlabs.io/docs/conversational-ai/overview)** — Conversational AI & Tool Calling
- **[LangGraph Guide](https://python.langchain.com/docs/langgraph)** — Agent orchestration
- **[Google Calendar API](https://developers.google.com/calendar/api/quickstart/python)** — Calendar integration
- **[Google Places API](https://developers.google.com/maps/documentation/places/web-service/overview)** — Provider search

---

**MIT Global AI Hackathon 2026 • ElevenLabs Challenge**  
*Building the future of autonomous appointment scheduling*
