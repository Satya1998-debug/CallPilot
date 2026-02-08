# CallPilot Technical Report 
**Audience:** Investors and internal stakeholders  
**Date:** February 8, 2026  
**Project:** CallPilot — Agentic Voice AI for Autonomous Appointment Scheduling

## Executive Summary
CallPilot is a working prototype that runs a text‑driven appointment‑scheduling workflow end‑to‑end. It finds nearby providers using Google Places/Maps when configured, checks calendar conflicts via Google Calendar, and records a booking. The flow is orchestrated as a multi‑step state machine with transcript logging and explainable scoring. There are **no live phone calls or negotiation** in the current build.

## Problem
Scheduling appointments by phone is slow and inefficient. Users must contact multiple offices, compare availability, and resolve conflicts with their calendars.

## What Works Today (Repository‑Backed)
- **Orchestrated workflow:** A LangGraph state machine runs the full flow from request to booking.
- **Provider discovery (live):** Google Places search for nearby providers with Google Maps distance calculation (when `USE_GOOGLE_APIS=true` and API keys are configured).
- **Provider matching:** Results are filtered by specialty and distance and ranked.
- **Opening hours metadata:** Google Places opening hours are retrieved and attached to provider data (not yet used for filtering).
- **Calendar conflict checks (live):** Google Calendar is used for availability checks when configured; otherwise a local stub is used.
- **Booking:** Google Calendar event creation is used when configured; otherwise a demo event ID is returned.
- **Scoring & explainability:** Provider rating and distance contribute to an explicit score explanation.

## System Snapshot (Current Implementation)
- **Core flow:** `pick provider → choose slot → reserve → book → score`
- **Data layer:** Google Places/Maps results (live) with local JSON fallback
- **Outputs:** Provider choice, selected slot, score explanation, transcript, and calendar event ID

## Tech Stacks
- **Workflow** orchestration using LangGraph, & Langchain.
- **Language**: Python
- **External API**: Google Places/Maps APIs, Google Calendar API, ElevenLabs SDK (Speech-to-text only), and local JSON datasets for fallback.
- **Tool calling** & Agentic Frameworks: Model-context-Protocol (MCP)

## Demonstrable Capabilities
- Runs a full appointment‑scheduling flow end‑to‑end in a local environment.
- Produces reproducible results for demos and testing.
- Provides an audit trail through transcripts and scoring rationale.

## Not Yet Implemented (Explicitly Out of Scope for This Report)
- Real phone calls or live negotiation.
- Use of opening‑hours data to filter or constrain scheduling.

---
This report reflects only functionality currently implemented in the repository.
