# OrganXcell — Complete Hosting Guide
## Deploy Full Stack (Django + PostgreSQL + Redis + Claude AI)

---

## OPTION A — Railway (Recommended, Free, 10 minutes)

Railway gives you Django + PostgreSQL + Redis all free, with one-click deploy.

### Step 1 — Create accounts (free)
1. GitHub: https://github.com → Sign up
2. Railway: https://railway.app → Sign up with GitHub

### Step 2 — Push code to GitHub
```bash
# Install Git if you don't have it: https://git-scm.com

cd organxcell_deploy      ← the folder from this zip

git init
git add .
git commit -m "OrganXcell SIH 2025"

# Create a new repo at github.com, then:
git remote add origin https://github.com/YOURNAME/organxcell.git
git push -u origin main
```

### Step 3 — Deploy on Railway
1. Go to https://railway.app/new
2. Click **"Deploy from GitHub repo"**
3. Select your `organxcell` repo
4. Railway auto-detects Django ✓

### Step 4 — Add PostgreSQL database
1. In your Railway project, click **"+ New"**
2. Choose **"Database" → "PostgreSQL"**
3. Railway automatically sets `DATABASE_URL` for you ✓

### Step 5 — Add Redis
1. Click **"+ New"** again
2. Choose **"Database" → "Redis"**
3. Railway automatically sets `REDIS_URL` ✓

### Step 6 — Set environment variables
In Railway → your web service → **Variables** tab, add:

```
ANTHROPIC_API_KEY = sk-ant-your-key-here    ← REQUIRED for AI features
SECRET_KEY        = any-random-50-char-string
DEBUG             = False
ALLOWED_HOSTS     = *
```

Get your free Claude API key: https://console.anthropic.com

### Step 7 — Run database migrations
In Railway → your web service → **Deploy** tab:
```
Click "Run Command" and enter:
python manage.py migrate && python manage.py shell < scripts/seed_database.py
```

### Step 8 — Done!
Railway gives you a URL like: **https://organxcell-production.up.railway.app**

Your full website is now live at that URL with real AI, real database, everything. ✓

---

## OPTION B — Render.com (Also Free)

### Step 1
Push to GitHub (same as Railway Step 2)

### Step 2
1. Go to https://render.com → New → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates all services automatically

### Step 3 — Add your API key
In Render dashboard → organxcell-web → Environment:
```
ANTHROPIC_API_KEY = sk-ant-your-key-here
```

### Step 4
Click **"Deploy Blueprint"** — done in ~5 minutes.

---

## OPTION C — Local (Your Laptop, Docker)

Run the full stack on your own machine. Good for demos.

### Prerequisites
Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### Steps
```bash
cd organxcell_deploy

# Create a .env file with your API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# Start everything (first time takes ~3 minutes to download)
docker compose up --build

# In a second terminal, run once:
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell < scripts/seed_database.py

# Open: http://localhost:8000
```

To stop: `docker compose down`
To start again: `docker compose up`

---

## DEMO LOGIN CREDENTIALS

| Role      | Email                    | Password  |
|-----------|--------------------------|-----------|
| Admin     | admin@organxcell.in      | admin123  |
| Donor     | donor1@test.com          | donor123  |
| Recipient | recipient1@test.com      | recv123   |
| Hospital  | coordinator@apollo.in    | hosp123   |

---

## WHAT WORKS WITHOUT ANTHROPIC API KEY

Everything works in demo mode — all pages, login, matching simulator, live map, blood bank.
The only features that need the key:
- AI Match Explainer (Match Simulator tab → "Explain this match")
- AI Chatbot (Admin, Donor, Recipient dashboards)
- AI Route Optimizer (Live Map page)
- AI Waiting List Reorder

All of these fall back to smart pre-written demo responses when the key is missing.

---

## FILE STRUCTURE

```
organxcell_deploy/
├── templates/
│   └── index.html          ← Full frontend (served by Django)
├── accounts/               ← Users, hospitals, JWT auth
├── organs/                 ← Organ models + matching algorithms
├── transport/              ← GPS tracking, WebSocket, cold chain
├── ai_engine/              ← 6 Claude AI features
├── notifications/          ← SOS alerts, email, SMS
├── consent/                ← HOTA consent workflow
├── organxcell/             ← Django settings, URLs, ASGI
├── scripts/
│   └── seed_database.py    ← Creates 20 hospitals + demo users
├── Procfile                ← Railway/Render/Heroku process config
├── railway.toml            ← Railway config
├── render.yaml             ← Render config
├── Dockerfile              ← For Docker/custom hosting
├── docker-compose.yml      ← Local full-stack
└── requirements.txt        ← Python packages
```

---

## TROUBLESHOOTING

**"Application failed to respond"**
→ Check that `ANTHROPIC_API_KEY` is set (or leave blank — demo mode works)
→ Check that PostgreSQL is connected (DATABASE_URL is set)

**"Relation does not exist" database error**
→ Run: `python manage.py migrate`

**AI features not working**
→ Add `ANTHROPIC_API_KEY` to your environment variables
→ Get free key: https://console.anthropic.com

**Map not loading tiles**
→ The map needs internet access for OpenStreetMap tiles — no API key needed

**WebSocket live tracking not working**
→ Make sure you're running Daphne (not gunicorn) — the Procfile handles this
→ Railway and Render both support WebSockets ✓

---

*OrganXcell — Making Every Match Count 🫀*
*Built at SIH 2025*
