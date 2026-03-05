# Launch the app (fast path)

You have a **Next.js frontend** and a **FastAPI backend**. The fastest way to go live:

- **Frontend → Vercel** (ideal for Next.js)
- **Backend → Railway** (Python/FastAPI; free tier available)

---

## 1. Deploy backend (Railway)

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project** → **Deploy from GitHub repo** → select `Pre-Procurement-Signal-Engine`.
3. When asked which service to add, choose **Backend** (or add a new service and set **Root Directory** to `backend`).
4. Set **Root Directory** to `backend` (in Settings → General).
5. Add **Environment Variables** (Settings → Variables) — same as your local `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
   - `LLM_PROVIDER` (e.g. `groq`)
   - `GROQ_API_KEY` (or `OPENAI_API_KEY`, etc.)
   - `ALLOWED_ORIGINS` = `*` or your Vercel URL later
6. Deploy. Railway will use `railway.json` + `Procfile`. Once deployed, copy your backend URL (e.g. `https://xxx.up.railway.app`).

---

## 2. Deploy frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New** → **Project** → import `Pre-Procurement-Signal-Engine`.
3. Set **Root Directory** to `frontend` (click Edit next to the repo name).
4. Add **Environment Variable**:
   - Name: `NEXT_PUBLIC_API_URL`
   - Value: your Railway backend URL (e.g. `https://xxx.up.railway.app`) — no trailing slash.
5. Deploy. Vercel will build and host the Next.js app.

Your app will be live at the Vercel URL (e.g. `https://your-project.vercel.app`).

---

## 3. (Optional) Lock CORS to your frontend

In Railway, set:

- `ALLOWED_ORIGINS` = `https://your-project.vercel.app`

So only your Vercel domain can call the API.

---

## One-repo note

Both Railway and Vercel can use the same repo:

- **Railway**: root directory = `backend`
- **Vercel**: root directory = `frontend`

No code changes required if you’ve already pushed the repo.
