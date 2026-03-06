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
4. In **Build & Development Settings**: set **Framework Preset** to `Next.js` and leave **Output Directory** empty (do not set it to `public` — that's for static sites).
5. Add **Environment Variable**:
   - Name: `NEXT_PUBLIC_API_URL`
   - Value: your Railway backend URL (e.g. `https://xxx.up.railway.app`) — no trailing slash.
6. Deploy. Vercel will build and host the Next.js app.

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

No code changes required if you've already pushed the repo.

---

## Troubleshooting: No grants / frontend not linked

If the live site shows no data or errors, check these in order.

### 1. Frontend → Backend (Vercel)

The frontend calls the backend using `NEXT_PUBLIC_API_URL`. This is **baked in at build time**.

- In **Vercel** → your project → **Settings** → **Environment Variables**:
  - Add (or fix): **Name** `NEXT_PUBLIC_API_URL`, **Value** = your **Railway backend URL** (e.g. `https://pre-procurement-signal-engine-production-xxxx.up.railway.app`) — **no trailing slash**.
- **Redeploy** the frontend after changing it (Deployments → ⋮ → Redeploy). Changing the variable alone is not enough; the app must be rebuilt.

Quick check: open your Vercel site, then in the browser open DevTools → Network. Reload and look for requests to your Railway URL. If you see requests to `localhost:8000` or they fail, the env var is missing or the app wasn't redeployed after setting it.

### 2. Backend → Database (Railway)

The backend reads from Supabase. If Railway has no DB env vars, the API will fail when loading grants.

- In **Railway** → your backend service → **Variables** (or Settings → Variables), ensure you have:
  - `SUPABASE_URL` = your Supabase project URL
  - `SUPABASE_SERVICE_KEY` = your Supabase service role key
  - (Optional) `SUPABASE_ANON_KEY` if you use it
- Restart/redeploy the backend after adding or changing variables.

Quick check: open `https://YOUR-RAILWAY-URL/health` in the browser. If that works, open `https://YOUR-RAILWAY-URL/api/overview`. If you get 500 or an error, the backend likely can't reach the database (check Variables and Supabase).

### 3. Database has no data

If the API returns empty lists or zeros, the database may have no grants yet.

- Run the pipeline once to ingest data (e.g. from the app's pipeline/run UI, or by calling `POST /api/pipeline/run` with your sources).
- Or ensure the same Supabase project and schema are used: run the SQL migrations and seed data (see README) in the Supabase project that the backend is pointing to.
