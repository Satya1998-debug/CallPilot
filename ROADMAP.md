# CallPilot Implementation Roadmap

**ElevenLabs Hackathon Challenge: Agentic Voice AI for Autonomous Appointment Scheduling**

## Project Overview

CallPilot is an AI-driven system that autonomously calls service providers, negotiates appointment slots, and selects optimal matches based on user preferences and availability.

## Current Status

✅ **Completed:**
- Basic project structure
- Provider data model with JSON storage
- Simulated receptionist adapter
- Provider matching and scoring algorithms
- Calendar availability checking
- LangGraph workflow skeleton

🔄 **In Progress:**
- ElevenLabs integration
- Real phone call capability

❌ **Not Started:**
- Google Calendar integration
- Google Maps/Places integration
- Parallel call orchestration (swarm mode)
- Real-time user dashboard

---

## Phase 1: Core MVP (Priority 1)

### 1.1 ElevenLabs Conversational AI Integration
**File:** `src/callpilot/adapters/elevenlabs_adapter.py`

```python
# Key Tasks:
- Set up ElevenLabs WebSocket connection
- Implement voice streaming
- Handle agent-to-receptionist conversation flow
- Add interruption handling
- Maintain <1s latency
```

**Dependencies:**
- `elevenlabs` SDK
- `ELEVENLABS_API_KEY` in `.env`

### 1.2 Agentic Functions (Tool Calling)
**File:** `src/callpilot/tools/agent_tools.py`

Implement ElevenLabs tool calling for:
- ✅ `check_calendar_availability(date, time)`
- ✅ `search_providers(specialty, insurance, distance)`
- ✅ `calculate_match_score(provider, preferences)`
- ❌ `get_travel_time(origin, destination)` - needs Google Maps API
- ❌ `book_calendar_slot(date, time, provider)` - needs Google Calendar API

### 1.3 Google Calendar Integration
**File:** `src/callpilot/integrations/google_calendar.py`

```python
# Key Tasks:
- OAuth2 authentication flow
- Read available time slots
- Create calendar events
- Check for conflicts
- Send calendar invites
```

**Dependencies:**
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- `GOOGLE_CALENDAR_CREDENTIALS` JSON file

### 1.4 Update LangGraph Workflow
**File:** `src/callpilot/graph.py`

Enhance nodes to use real integrations:
- `gather_patient_info` → Use conversational AI
- `match_provider` → Use scoring + Google Places rating
- `check_availability` → Use real calendar API
- `call_provider` → Use ElevenLabs voice agent
- `confirm_appointment` → Update calendar + send confirmation

---

## Phase 2: Swarm Mode (Priority 2)

### 2.1 Parallel Call Orchestration
**File:** `src/callpilot/swarm/orchestrator.py`

```python
# Key Tasks:
- Spawn up to 15 concurrent ElevenLabs agent instances
- Manage call state for each provider
- Handle failures and retries
- Aggregate results in real-time
```

**Implementation:**
```python
async def parallel_call_campaign(
    providers: List[Provider],
    patient_info: PatientInfo
) -> List[CallResult]:
    tasks = [
        call_provider(provider, patient_info)
        for provider in providers
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return rank_results(results)
```

### 2.2 Result Aggregation & Ranking
**File:** `src/callpilot/swarm/aggregator.py`

Scoring function combining:
- Earliest availability (40% weight)
- Google rating (25% weight)
- Travel distance (20% weight)
- Insurance match (15% weight)

---

## Phase 3: Google APIs Integration (Priority 2)

### 3.1 Google Places API
**File:** `src/callpilot/integrations/google_places.py`

```python
# Key Tasks:
- Search providers by specialty and location
- Get provider ratings and reviews
- Extract phone numbers and addresses
- Cache results for performance
```

### 3.2 Google Maps Distance Matrix
**File:** `src/callpilot/integrations/google_maps.py`

```python
# Key Tasks:
- Calculate travel time from user location
- Support multiple origins/destinations
- Factor in traffic conditions
- Return duration in minutes
```

---

## Phase 4: User Interface (Priority 3)

### 4.1 Streamlit Dashboard
**File:** `app.py`

Features:
- Input form: specialty, insurance, preferred dates
- Real-time call status for each provider
- Live transcript streaming
- Final recommendation with map view
- One-click booking confirmation

### 4.2 Real-Time Updates
Use WebSockets to push:
- Call progress updates
- Transcript snippets
- Availability found
- Final rankings

---

## Phase 5: Stretch Goals (Optional)

### 5.1 Multilingual Support
- Detect provider language from Places API
- Switch ElevenLabs voice model dynamically
- Support: English, Spanish, German, Mandarin

### 5.2 Rescheduling & Cancellation
- New agent mode: "reschedule" or "cancel"
- Reference existing appointment ID
- Update calendar after confirmation

### 5.3 Human-in-the-Loop
- Live transcript view with intervention button
- User can override agent decisions
- Graceful handoff when agent is uncertain

### 5.4 Hallucination Detection
- Monitor confidence scores
- Flag uncertain responses
- Transfer to human user when needed

### 5.5 Domain Expert Routing
- Health knowledge expert for medical queries
- Fitness expert for gym/therapy scheduling
- Route based on appointment type

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│              Streamlit UI (app.py)                  │
│  [Input Form] [Call Status] [Live Transcripts]     │
└───────────────────┬─────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────┐
│         LangGraph Orchestrator (graph.py)           │
│  gather_info → match → check_avail → call → confirm│
└───────┬────────────────────────┬────────────────────┘
        │                        │
        │                        │
┌───────▼────────┐      ┌────────▼────────────────────┐
│  Agent Tools   │      │   ElevenLabs Voice Agent    │
│  - calendar    │      │   - Conversational AI       │
│  - providers   │      │   - Tool calling            │
│  - scoring     │      │   - WebSocket streaming     │
└────────────────┘      └─────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────┐
│              External APIs                          │
│  - Google Calendar API                              │
│  - Google Places API                                │
│  - Google Maps Distance Matrix API                  │
└─────────────────────────────────────────────────────┘
```

---

## Required API Keys & Setup

### `.env` file:
```bash
# Core
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key  # For LangGraph logic

# Google APIs
GOOGLE_MAPS_API_KEY=your_google_maps_key
GOOGLE_CALENDAR_CREDENTIALS=/path/to/credentials.json

# Optional
TWILLIO_ACCOUNT_SID=your_twilio_sid  # If using real phone calls
TWILLIO_AUTH_TOKEN=your_twilio_token
```

---

## Next Immediate Steps

### Step 1: Test Current Structure
```bash
python test_structure.py
```

### Step 2: Set Up ElevenLabs
1. Sign up at elevenlabs.io
2. Get API key
3. Add to `.env`
4. Test voice synthesis:
   ```bash
   python example_test.py
   ```

### Step 3: Implement ElevenLabs Adapter
Create `src/callpilot/adapters/elevenlabs_adapter.py` with:
- WebSocket connection
- Conversational AI setup
- Tool calling registration

### Step 4: Test Single Call Flow
Run simulated end-to-end flow:
```bash
python -m src.callpilot.run
```

### Step 5: Add Google Calendar
Follow OAuth2 setup and integrate calendar checking

### Step 6: Build Swarm Mode
Implement parallel call orchestration

### Step 7: Create Streamlit UI
Build real-time dashboard

---

## Evaluation Checklist

Based on hackathon criteria:

- [ ] **Conversational Quality**
  - [ ] Natural interruption handling
  - [ ] <1s latency achieved
  - [ ] Smooth conversation flow

- [ ] **Use of Agentic Functions**
  - [ ] Calendar integration working
  - [ ] Provider search working
  - [ ] Distance calculations working
  - [ ] Dynamic tool calling

- [ ] **Optimal Match Quality**
  - [ ] Scoring algorithm validated
  - [ ] User preferences weighted correctly
  - [ ] Correct provider recommended

- [ ] **Parallelization**
  - [ ] 15 concurrent calls tested
  - [ ] Failure handling implemented
  - [ ] Results aggregated correctly

- [ ] **User Experience**
  - [ ] Intuitive UI
  - [ ] Clear status updates
  - [ ] One-click booking

---

## Demo Script

1. **Setup:** "I need a cardiologist appointment this week, accepting Blue Cross"
2. **Show:** System calls 15 providers in parallel
3. **Display:** Live transcripts from top 3 conversations
4. **Result:** Ranked list with Dr. Chen at top (4.9★, Monday 2pm, 3 miles away)
5. **Action:** Confirm booking → calendar updated → confirmation sent

**Demo Duration:** 3-5 minutes total
**Wow Factor:** Watch 15 calls happen simultaneously with live transcripts

---

## Resources

- [ElevenLabs Conversational AI Docs](https://elevenlabs.io/docs/conversational-ai/overview)
- [ElevenLabs Tool Calling](https://elevenlabs.io/docs/conversational-ai/customization/tool-calling)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Google Calendar API Quickstart](https://developers.google.com/calendar/api/quickstart/python)
- [Google Places API](https://developers.google.com/maps/documentation/places/web-service/overview)

---

**Last Updated:** February 7, 2026
