## Week 1-2: Foundation & Quick Win

# Educational Content Generator AI Agent Development Project – Dual Track Version

##EduCator

EduCator is a study assistant that turns uploaded content into MCQs, flashcards, and a concise summary, with optional text‑to‑speech and audio generation.

## Current Workflow
1. User logs in (Google or email/password).
2. User uploads a file (`.txt`, `.pdf`, `.docx`, `.pptx`) or pastes text.
3. Backend extracts text and generates:
   - 10 MCQs
   - 10 flashcards
   - Summary
4. User answers MCQs and gets instant validation.
5. User can:
   - Regenerate results for the same source
   - Generate for a new source
   - Save results to history
6. History can be viewed, expanded, and items deleted.
7. Summary can be spoken (browser TTS) or converted to an audio file (server TTS).

## Features Implemented
- Multi‑format input: TXT, PDF, DOCX, PPTX
- MCQ generation + answer verification
- Flashcard generation
- Summary generation
- Browser TTS playback
- Server audio generation (MP3)
- History storage in Firestore
- History list with per‑item details + delete + clear all
- UI improvements (professional layout, animated navbar rain, moving boat)

## Tech Stack
- Frontend: React
- Backend: Flask
- AI: OpenRouter
- Database: Firebase Firestore

## Setup (Local)
### Backend
1. Create and activate a Python venv.
2. Install dependencies (example):
   ```bash
   pip install -r requirements.txt
   ```
3. Create `backend/.env` and set:
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`
   - `FIREBASE_PROJECT_ID`
   - `FIREBASE_SERVICE_ACCOUNT_PATH`
4. Start:
   ```bash
   python backend/app.py
   ```

### Frontend
1. Install dependencies:
   ```bash
   npm install
   ```
2. Start:
   ```bash
   npm start
   ```

## Notes
- **Do not commit** `.env` files or Firebase service account JSON.
- If deploying, configure environment variables in your hosting provider.
