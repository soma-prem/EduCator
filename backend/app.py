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

from flask import Flask  # noqa: E402
from flask_cors import CORS  # noqa: E402

from routes.diag import diag_bp  # noqa: E402
from routes.generate import generate_bp  # noqa: E402
from routes.history import history_bp  # noqa: E402
from routes.misc import misc_bp  # noqa: E402
from routes.tts import tts_bp  # noqa: E402
from routes.verify import verify_bp  # noqa: E402
app = Flask(__name__)
CORS(app)

app.register_blueprint(misc_bp)
app.register_blueprint(generate_bp)
app.register_blueprint(verify_bp)
app.register_blueprint(history_bp)
app.register_blueprint(tts_bp)
app.register_blueprint(diag_bp)

if __name__ == "__main__":
    app.run(debug=True)
