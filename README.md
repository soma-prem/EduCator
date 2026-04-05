# Week 5: Content-to-Learning Materials Converter and Smart Study Assistant

## Educational Content Generator AI Agent Development Project - Dual Track Version - EduCator

EduCator is a study assistant that turns uploaded content into multiple study resources (MCQs, flashcards, true/false, fill-in-the-blanks, and summaries), with optional text-to-speech and audio generation.

## Current Workflow
1. User logs in (Google or email/password).
2. User adds one or more sources (text + files like `.txt`, `.pdf`, `.docx`, `.pptx`) into a single session (auto-saved).
3. User generates study resources (default 20 items per tool where applicable):
   - MCQs
   - Flashcards
   - True/False
   - Fill-in-the-Blanks
   - Summary
4. User practices each resource type and sees scoring/progress (where applicable).
5. User analyzes Knowledge Gaps to get concept explanations based on wrong answers.
6. AI Guide answers text or voice questions grounded in the uploaded sources.
7. Sessions are automatically persisted to History and can be restored later (sources + generated content).
8. Summary can be spoken (server TTS) and the displayed summary text can be translated to the selected language.
9. Download outputs (PDF/CSV/Text) from study pages.
10. Premium tools can be unlocked via Stripe test-mode checkout (feature-gated in UI + backend).

## Features Implemented
- Multi-format input: TXT, PDF, DOCX, PPTX
- Multi-source sessions (generation uses all added sources in the session)
- MCQ generation + answer verification + scoring/progress
- Flashcard generation + review tracking
- Flashcards image enrichment (images for all flashcards) + consistent card sizing/layout
- True/False generation + scoring/progress
- Fill-in-the-Blanks generation + scoring/progress
- Summary generation (separate summary page)
- Difficulty levels (easy / medium / hard) with instant re-generation on supported pages
- Knowledge Gap Analyzer (mode-specific) with concept explanations based on wrong answers
- AI Guide (text + voice toggle)
- Voice assistant: speech input + spoken answers
- Server audio generation (MP3) via `/api/tts`
- Summary text translation via `/api/translate`
- OpenRouter integration
  - MCQs: OpenRouter (google/gemini-2.5-flash)
  - Flashcards: OpenRouter (google/gemini-2.5-flash)
  - Summary: OpenRouter via (google/gemini-2.5-flash)
  - Voice assistant: OpenRouter (google/gemini-2.5-flash)
- Temporary file storage for uploads (fileId restore on return)
- Automatic session persistence + restore from History (Firestore-backed)
- History list with per-item details + delete + clear all + continue
- Export/download (PDF, CSV, Text) on study pages
- More MCQs/Flashcards: backend refill endpoint exists (UI button not added yet)
- Voice options: language selector available
- Premium plans + server-side entitlement enforcement (Stripe test mode)
- Feature gating UX: locked tools show a crown and prompt to upgrade
- YouTube guide: recommends related videos based on the uploaded sources
- UI refresh: YouTube guide and mock test pages redesigned for a cleaner layout

## Tech Stack
- Frontend: React (Create React App) + CSS
- Backend: FastAPI (Python) + Uvicorn
- Auth: Firebase Authentication (Google + email/password)
- Database: Firebase Firestore
- AI: OpenRouter (Gemini)
- Payments: Stripe Checkout + webhooks (test mode)

