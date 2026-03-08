# Week 1-2: Foundation & Quick Win

## Educational Content Generator AI Agent Development Project - Dual Track Version - EduCator

EduCator is a study assistant that turns uploaded content into MCQs, flashcards, and a concise summary, with optional text-to-speech and audio generation.

## Current Workflow
1. User logs in (Google or email/password).
2. User uploads a file (`.txt`, `.pdf`, `.docx`, `.pptx`) or pastes text.
3. Backend extracts text and generates:
   - 10 MCQs
   - 10 flashcards
   - Summary
4. User answers MCQs and gets instant validation.
5. AI Guide answers text or voice questions grounded in the uploaded source.
6. User can:
   - Regenerate results for the same source
   - Generate for a new source
   - Save results to history
7. History can be viewed, expanded, and items deleted.
8. Summary can be spoken (browser TTS) or converted to an audio file (server TTS).
9. Download outputs (PDF/CSV/Text) from MCQ or Flashcard pages.

## Features Implemented
- Multi-format input: TXT, PDF, DOCX, PPTX
- MCQ generation + answer verification
- Flashcard generation
- Summary generation (separate summary page)
- AI Guide (text and voice toggle)
- Voice assistant: speech input + spoken answers
- Browser TTS playback
- Server audio generation (MP3)
- OpenRouter integration
  - MCQs: OpenRouter (google/gemini-2.5-flash)
  - Flashcards: OpenRouter (google/gemini-2.5-flash)
  - Voice assistant: OpenRouter (google/gemini-2.5-flash)
- Temporary file storage for uploads (fileId restore on return)
- History storage in Firestore
- History list with per-item details + delete + clear all
- Export/download (PDF, CSV, Text) on MCQ/Flashcard pages
- More MCQs/Flashcards: backend refill endpoint exists (UI button not added yet)
- Voice options: language selector available 


## Tech Stack
- Frontend: React
- Backend: FastAPI (Python)
- AI: OpenRouter + Gemini (fallback)
- Database: Firebase Firestore

