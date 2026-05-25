import os


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routes.diag import router as diag_router  # noqa: E402
from routes.export import router as export_router  # noqa: E402
from routes.generate import router as generate_router  # noqa: E402
from routes.history import router as history_router  # noqa: E402
from routes.ai import router as ai_router  # noqa: E402
from routes.misc import router as misc_router  # noqa: E402
from routes.analyze import router as analyze_router  # noqa: E402
from routes.qa import router as qa_router  # noqa: E402
from routes.recommend import router as recommend_router  # noqa: E402
from routes.tts import router as tts_router  # noqa: E402
from routes.tools import router as tools_router  # noqa: E402
from routes.translate import router as translate_router  # noqa: E402
from routes.verify import router as verify_router  # noqa: E402
from routes.voice_qa import router as voice_qa_router  # noqa: E402
from routes.spaced import router as spaced_router  # noqa: E402
from routes.revision import router as revision_router  # noqa: E402
from routes.voice_tutor import router as voice_tutor_router  # noqa: E402
from routes.exam import router as exam_router  # noqa: E402
from routes.youtube import router as youtube_router  # noqa: E402
from routes.billing import router as billing_router  # noqa: E402

app = FastAPI(title="EduCator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(misc_router)
app.include_router(analyze_router)
app.include_router(ai_router)
app.include_router(tools_router)
app.include_router(generate_router)
app.include_router(verify_router)
app.include_router(history_router)
app.include_router(tts_router)
app.include_router(diag_router)
app.include_router(export_router)
app.include_router(recommend_router)
app.include_router(translate_router)
app.include_router(qa_router)
app.include_router(voice_qa_router)
app.include_router(spaced_router)
app.include_router(revision_router)
app.include_router(voice_tutor_router)
app.include_router(exam_router)
app.include_router(youtube_router)
app.include_router(billing_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "5000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
