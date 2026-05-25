# Deploy EduCator — Render (backend) + Vercel (frontend)

| Part | Platform | Folder |
|------|----------|--------|
| FastAPI API | [Render](https://render.com) | `backend/` |
| React app | [Vercel](https://vercel.com) | `frontend/` |

Deploy **backend first**, copy its public URL, then set that URL on Vercel.

---

## 0. Prerequisites

1. Code is on **GitHub** (private repo is fine).
2. You have API keys ready (Gemini, Firebase, Stripe, etc.).
3. Firebase Console → **Authentication** → **Settings** → **Authorized domains**:
   - Add your Vercel domain (e.g. `your-app.vercel.app` and custom domain if any).

---

## 1. Render — backend

### Option A — Blueprint (`render.yaml`)

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect the GitHub repo.
3. Render detects `render.yaml` and creates **educator-api**.
4. Open the service → **Environment** → fill every variable (see table below).
5. **Deploy** and wait until status is **Live**.
6. Copy the URL, e.g. `https://educator-api.onrender.com`.

### Option B — Manual Web Service

| Setting | Value |
|---------|--------|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/message` |

### Render environment variables

Set these in **Environment** (never commit real values).

| Variable | Required | Notes |
|----------|----------|--------|
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Yes (Render) | Paste **entire** service account JSON as **one line** (minified). Do not use a file path on Render. |
| `GEMINI_API_KEY` | Yes | Google Gemini |
| `FRONTEND_BASE_URL` | Yes | Your Vercel URL, e.g. `https://educator.vercel.app` (no trailing slash) |
| `STRIPE_SECRET_KEY` | If using billing | `sk_live_...` or `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | If using billing | From Stripe webhook (see below) |
| `YOUTUBE_API_KEY` | Optional | YouTube Guide feature |
| `PEXELS_API_KEY` | Optional | Flashcard images |
| `UNSPLASH_ACCESS_KEY` | Optional | Flashcard images |

**Stripe webhook on Render**

1. Stripe Dashboard → **Developers** → **Webhooks** → **Add endpoint**.
2. URL: `https://YOUR-RENDER-SERVICE.onrender.com/api/billing/webhook`
3. Events: at least `checkout.session.completed` (and any others your app uses).
4. Copy **Signing secret** → `STRIPE_WEBHOOK_SECRET` on Render.

**Smoke test**

- Open `https://YOUR-RENDER-SERVICE.onrender.com/api/message` — should return JSON.
- Open `https://YOUR-RENDER-SERVICE.onrender.com/api/diag/firebase` — should show Firebase OK when JSON is correct.

**Free tier note:** Render free services spin down after inactivity; the first request may take ~30–60s.

---

## 2. Vercel — frontend

1. [Vercel Dashboard](https://vercel.com/new) → **Import** your GitHub repo.
2. **Root Directory** → **Edit** → set to `frontend`.
3. Framework Preset: **Create React App** (auto-detected).
4. Build Command: `npm run build` (default).
5. Output Directory: `build` (default).

### Vercel environment variables

Add in **Settings** → **Environment Variables** (Production + Preview):

| Variable | Example |
|----------|---------|
| `REACT_APP_API_BASE` | `https://educator-api.onrender.com` |
| `REACT_APP_FIREBASE_API_KEY` | From Firebase web app config |
| `REACT_APP_FIREBASE_AUTH_DOMAIN` | `your-project.firebaseapp.com` |
| `REACT_APP_FIREBASE_PROJECT_ID` | Same as backend project |
| `REACT_APP_FIREBASE_STORAGE_BUCKET` | `your-project.appspot.com` |
| `REACT_APP_FIREBASE_MESSAGING_SENDER_ID` | Numeric ID |
| `REACT_APP_FIREBASE_APP_ID` | `1:...:web:...` |

6. **Deploy**.
7. Copy your Vercel URL (e.g. `https://educator.vercel.app`).

### After first Vercel deploy

1. Set `FRONTEND_BASE_URL` on Render to your **exact** Vercel URL.
2. **Redeploy** the Render service (Manual Deploy → Deploy latest).
3. Confirm Firebase **Authorized domains** includes the Vercel hostname.

`frontend/vercel.json` enables React Router (all routes serve `index.html`).

---

## 3. Order of operations (recommended)

```text
GitHub push
    → Render deploy backend (+ env vars)
    → Copy Render URL
    → Vercel deploy frontend (REACT_APP_API_BASE = Render URL)
    → Copy Vercel URL
    → Update Render FRONTEND_BASE_URL + redeploy
    → Stripe webhook → Render URL
    → Firebase authorized domain → Vercel URL
```

---

## 4. Local vs production

| | Local | Production |
|---|--------|------------|
| API | `http://127.0.0.1:5000` | `https://….onrender.com` |
| App | `http://localhost:3000` | `https://….vercel.app` |
| Firebase creds | `serviceAccountKey.json` file | `FIREBASE_SERVICE_ACCOUNT_JSON` env on Render |

Copy templates only:

```powershell
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

---

## 5. Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend calls localhost | Redeploy Vercel after setting `REACT_APP_API_BASE`; CRA bakes env at **build** time. |
| CORS errors | Backend allows `*`; check `REACT_APP_API_BASE` has no typo/trailing path. |
| Firebase auth fails on Vercel | Add Vercel domain in Firebase Authorized domains. |
| History / save not working | Set `FIREBASE_SERVICE_ACCOUNT_JSON` on Render; test `/api/diag/firebase`. |
| Stripe redirect wrong | Set `FRONTEND_BASE_URL` on Render to Vercel URL and redeploy. |
| 502 / timeout on AI | Render free tier cold start or Gemini quota; check Render logs. |

---

## 6. Custom domain (optional)

- **Vercel:** Project → **Domains** → add domain → update Firebase authorized domains.
- **Render:** Service → **Settings** → **Custom Domains** → use that host in Stripe webhook if API is on a custom domain.
- Update `REACT_APP_API_BASE` / `FRONTEND_BASE_URL` to match custom URLs and redeploy both.
