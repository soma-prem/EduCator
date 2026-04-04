# EduCator

- Ingestion + sessioning: User logs in (Firebase Auth) and adds multiple sources into a single session; uploads are temporarily stored and the session is persisted (Firestore) for restore/history.
- AI generation pipeline: Backend (FastAPI) extracts text from uploaded files, then uses LLM calls to generate structured JSON outputs for each tool (MCQs, flashcards, summary, etc.), with retry/validation logic to keep outputs usable.
- Interactive learning loop: Frontend practice pages implement attempt checking, scoring/progress, difficulty selection (easy/medium/hard), and “Knowledge Gap Analyzer” prompts based on wrong answers.
- Retention & exam simulation: Spaced repetition scheduling plus mock-exam generation/grading to mimic real test conditions.
- Multimodal helpers: Voice tutor/voice Q&A (browser SpeechRecognition + backend TTS MP3), plus translation and YouTube recommendations grounded on the uploaded content.
- Premium gating: Feature access is enforced both in UI and backend; Stripe checkout (test mode currently) + entitlement stored in Firestore.

