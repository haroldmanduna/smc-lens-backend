# SMC Lens — Complete Deployment Guide

---

## STEP 1 — GITHUB SETUP

Create two repositories on GitHub:
- `smclens-backend`
- `smclens-frontend`

Push the respective folders to each repo.

```bash
# Backend
cd smclens-backend
git init
git add .
git commit -m "Initial backend"
git remote add origin https://github.com/YOUR_USERNAME/smclens-backend.git
git push -u origin main

# Frontend
cd smclens-frontend
git init
git add .
git commit -m "Initial frontend"
git remote add origin https://github.com/YOUR_USERNAME/smclens-frontend.git
git push -u origin main
```

---

## STEP 2 — SUPABASE SETUP

1. Go to https://supabase.com → New Project
2. Name it: `smclens`
3. Choose a strong database password (save it)
4. Region: choose closest to Africa (EU West is fine)
5. Once created → go to SQL Editor
6. Paste the entire contents of `schema.sql` → Run
7. Go to Settings → API → copy:
   - `Project URL` → this is your `SUPABASE_URL`
   - `anon public` key → this is your `SUPABASE_ANON_KEY`
   - `service_role` key → this is your `SUPABASE_SERVICE_KEY` (keep secret)
8. Go to Authentication → Settings → confirm email enabled

---

## STEP 3 — RAILWAY BACKEND DEPLOYMENT

1. Go to https://railway.app → New Project
2. Deploy from GitHub repo → select `smclens-backend`
3. Railway auto-detects Python → click Deploy
4. Once deployed → go to Variables tab → add ALL of these:

```
TWELVEDATA_API_KEY=your_key
GROQ_API_KEY=your_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SUPER_ADMIN_EMAIL=haroldmanduna388@gmail.com
JWT_SECRET=generate_random_64_chars
FRONTEND_URL=https://smclens.netlify.app
```

5. Go to Settings → Networking → Generate Domain
6. Copy your Railway URL (e.g. `https://smclens-backend.railway.app`)
7. Test it: open `https://YOUR_RAILWAY_URL/health` → should return `{"status":"healthy"}`

---

## STEP 4 — NETLIFY FRONTEND DEPLOYMENT

1. Go to https://netlify.com → Add New Site → Import from Git
2. Select `smclens-frontend` repo
3. Build command: `npm run build`
4. Publish directory: `dist`
5. Go to Site Configuration → Environment Variables → add:

```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=https://YOUR_RAILWAY_URL
```

6. Deploy → Netlify gives you a URL like `smclens.netlify.app`
7. Go back to Railway → update `FRONTEND_URL` to your Netlify URL

---

## STEP 5 — SET YOURSELF AS SUPER ADMIN

After you create your account on the app:

1. Go to Supabase → Table Editor → users table
2. Find your row (haroldmanduna388@gmail.com)
3. If not already set: edit → role = `super_admin`, plan = `pro`
4. Save

OR run this in Supabase SQL Editor:
```sql
UPDATE users 
SET role = 'super_admin', plan = 'pro' 
WHERE email = 'haroldmanduna388@gmail.com';
```

---

## STEP 6 — CONNECT CUSTOM DOMAIN (when ready)

1. Buy domain on Namecheap (smclens.com or smclens.app)
2. In Netlify → Domain Management → Add Custom Domain
3. Follow Netlify's DNS instructions
4. SSL auto-configured by Netlify

---

## STEP 7 — TEST EVERYTHING

Go through this checklist:

- [ ] Sign up with a test email
- [ ] Verify email
- [ ] Login works
- [ ] Select EUR/USD, 1H → click Analyse
- [ ] Signal card displays with real prices (not 0.00000)
- [ ] Confluence score shows (not 10/10 always)
- [ ] SL is not too tight
- [ ] AI narrative is 5 sentences
- [ ] Top-down card shows for Pro, blurred for Trial
- [ ] Submit EcoCash payment reference
- [ ] Login as super admin → approve payment
- [ ] User plan upgrades to Pro
- [ ] Admin panel stats load
- [ ] Feature flags visible to super admin only

---

## FILE STRUCTURE SUMMARY

```
smclens-backend/
├── main.py                    ← FastAPI app entry
├── requirements.txt           ← Python dependencies
├── railway.toml               ← Railway deployment config
├── schema.sql                 ← Run this in Supabase
├── .env.example               ← Copy to .env locally
├── middleware/
│   └── auth.py                ← JWT verification + role checks
├── routers/
│   ├── auth.py                ← Register, login, profile
│   ├── analysis.py            ← Run analysis, history
│   ├── payments.py            ← EcoCash payment flow
│   └── admin.py               ← Full admin panel endpoints
└── services/
    ├── twelvedata.py          ← Candle data fetching + caching
    ├── structure.py           ← Swing high/low + bias detection
    ├── orderblock.py          ← OB + FVG + liquidity detection
    ├── entry.py               ← Entry / SL / TP calculation
    ├── candlestick.py         ← Pattern detection + volume
    ├── confluence.py          ← Scoring (out of 13)
    ├── groq_ai.py             ← Narrative writer only
    └── analyzer.py            ← Orchestrates all services

smclens-frontend/
├── index.html                 ← HTML entry
├── package.json               ← Dependencies
├── vite.config.js             ← Vite config
├── netlify.toml               ← Netlify deployment config
├── .env.example               ← Copy to .env locally
└── src/
    ├── main.jsx               ← React entry
    └── App.jsx                ← Full application
```

---

## API KEYS YOU NEED

| Key | Where to get |
|-----|-------------|
| TWELVEDATA_API_KEY | https://twelvedata.com → dashboard |
| GROQ_API_KEY | https://console.groq.com |
| SUPABASE_URL | Supabase → Settings → API |
| SUPABASE_ANON_KEY | Supabase → Settings → API |
| SUPABASE_SERVICE_KEY | Supabase → Settings → API |

---

## LOCAL DEVELOPMENT (optional)

```bash
# Backend
cd smclens-backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your .env values
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd smclens-frontend
npm install
cp .env.example .env
# Fill in .env: VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000

---

## IMPORTANT SECURITY NOTES

1. NEVER commit .env files to GitHub
2. Add .env to .gitignore before first push
3. SUPABASE_SERVICE_KEY has full DB access — backend only, never frontend
4. Your admin login password is set privately through Supabase auth — never shared
5. Rotate JWT_SECRET if you suspect it was exposed
