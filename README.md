# Week 8 : Final Complete Project

## EduCator — Content-to-Learning Materials Converter & Smart Study Assistant
EduCator turns uploaded study content into practice material (MCQs, flashcards, fill-in-the-blanks, true/false, and summaries) and adds retention tools like spaced repetition, revision, and mock exams.

## Current Workflow
1. User logs in (Google or email/password).
2. User adds one or more sources into a single session (text + files: `.txt`, `.pdf`, `.docx`, `.pptx`).
3. From the Upload page, user generates study tools (UI defaults to **12** items per tool where applicable):
  - MCQs
  - Flashcards (optionally with images)
  - Summary
  - Fill-in-the-Blanks (Premium)
  - True/False (Premium)
4. User practices on the respective pages, gets scoring/progress, and can export results.
5. On the Study Set page, the app builds a spaced-repetition plan and can run Knowledge Gap + Smart Revision analysis.
6. AI Guide answers questions grounded in the uploaded sources (text + optional voice answer).
7. Sessions are saved to History (Firestore) and can be restored later.
8. Premium tools can be unlocked via Stripe test-mode checkout (feature-gated in UI + backend).

## Features Implemented 
- Multi-format ingestion:
  Supports TXT, PDF, DOCX, PPTX text extraction with temporary upload storage (fileId restore)

- Multi-source sessions:
  Content generation uses all added sources within a session

- MCQ System:
  MCQ generation, verification (/api/verify/mcq), scoring and progress tracking in UI

- Flashcards:
  AI-generated flashcards with image enrichment via Unsplash/Pexels APIs and review marking

- Difficulty Control:
  Easy, Medium, Hard levels with instant regeneration

- Topic Extraction:
  Key topics extraction via /api/analyze/topics

- Spaced Repetition:
  Leitner-based scheduling via /api/spaced/schedule with Firestore save/load

- Smart Revision:
  Prioritizes weak topics and due cards, generates focused revision quiz (/api/revision/start)

- Knowledge Gap Analyzer (Premium):
  Weak topic detection and grounded revision notes via /api/recommend/knowledge-gaps

- AI Guide (RAG-based):
  Context-aware Q&A grounded in uploaded sources via /api/qa/source

- Voice Features:
  Speech-to-text (Web Speech API)
  Voice Q&A (/api/qa/voice)
  Audio summaries via /api/tts (Premium: audio_summary)

- Translation:
  Text and summary translation via /api/translate

- Mock Exam Generator (Premium):
  Full-length exam generation via /api/exam/mock

- YouTube Guide (Premium):
  Video recommendations via /api/youtube/recommend (YouTube Data API)

- Export Options:
  PDF, CSV, and quiz format via /api/export/study-set/{pdf|csv|quiz}

- Billing:
  Stripe Checkout, webhook integration, server-side entitlements (/api/billing/*)

- Diagnostics:
  Firebase connectivity check via /api/diag/firebase

## Recent Changes / Project Status (Week 8)
- Provider migration: removed OpenRouter usage and now use Google Gemini via a single service client (`backend/services/gemini_service.py`).
- Per-tool API keys: the backend supports dedicated environment variables for each tool to limit blast radius and monitor usage:
  - `GEMINI_API_KEY` (global fallback)
  - `GEMINI_MCQ_API_KEY`
  - `GEMINI_FLASHCARD_API_KEY`
  - `GEMINI_TRUEANDFALSE_API_KEY`
  - `GEMINI_VOICE_API_KEY`
  - `GEMINI_FILLIN_API_KEY`
  - `GEMINI_SUMMARY_API_KEY`
  - `GEMINI_TEXTAI_API_KEY`
  - `GEMINI_MOCKTEST_API_KEY`

- No silent fallbacks to OpenRouter: endpoints now fail fast if a required GEMINI_* key is missing, making misconfiguration visible in production.
- Quota mitigation: `call_gemini()` now attempts a single fallback to the global `GEMINI_API_KEY` when a per-tool key hits a quota/429, then surfaces a clear error if quota remains exhausted.
- Session reuse: MCQ generation flow (`/api/tools/generate`) reuses an existing MCQ session when `mcqSetId` is present and `regenerate` is false, avoiding unnecessary regenerations and saving quota.
- UI cleanup: removed the "Start Smart Revision" and "Start Voice Tutor" buttons from the Study Set page to simplify the MCQ view. Smart Revision and Voice Tutor UI remain available as contextual sections when data or actions are present.

## Known Issues / Next Actions
- Gemini free-tier quotas can still be exhausted. Recommended actions:
  - Provide a paid/Pro `GEMINI_API_KEY` in the Render environment.
  - Set sensible per-tool limits and reuse cached sessions where possible.
  - Consider server-side queuing or exponential backoff for heavy generation workloads.
- Build: after UI changes, rebuild the frontend (`npm install && npm run build`) and redeploy static assets to Vercel.

## Deployment Checklist (Render / Vercel)
- Remove any legacy `OPENROUTER_*` env variables from Render (they can cause accidental provider usage).
- Set the required `GEMINI_*` env variables on Render and verify they are paid/provisioned if production traffic is expected.
- Redeploy backend on Render and frontend on Vercel.

## How to Build & Run Locally
Backend (Python):
```
python -m venv .venv
source .venv/Scripts/activate    # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
cd backend
uvicorn app:app --reload
```

Frontend (React):
```
cd frontend
npm install
npm run start     # dev
npm run build     # production bundle
```

## Contact / Troubleshooting
- If you see unexpected provider errors (OpenRouter 402 or Gemini quota messages), verify the Render environment variables and redeploy. Check backend logs for clear errors when keys are missing or quota is exceeded.

---
Updated: Week 8 status and deployment notes.


## TECH STACK

Frontend:
- React (Create React App)
- React Router
- CSS
- Firebase JS SDK
- react-toastify

Backend:
- FastAPI
- Uvicorn
- PyPDF2 (PDF processing)
- gTTS (Text-to-Speech)
- Firebase Admin SDK
- Stripe SDK

Database and Storage:
- Firebase Firestore (user history and spaced repetition data)