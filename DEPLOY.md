# Deploy Quantum Portfolio Optimizer to Render (Free)

This guide walks you through deploying the app to **Render.com** so you have a live URL to share (e.g. on LinkedIn). No credit card required.

---

## 1. Why Render?

- **Free tier** – 750 hours/month, no credit card
- **Python support** – Native `pip install` and gunicorn
- **Enough for Qiskit** – Free instance can run small VQE simulations (4–6 assets, ~100 iterations)
- **HTTPS** – Free `*.onrender.com` URL with SSL
- **Cold starts** – Free tier sleeps after ~15 min inactivity; first request may take 30–60 s (see [Cold starts](#cold-starts) below)

---

## 2. Prepare Your Repository

### 2.1 Initialize Git (if not already)

```bash
cd /path/to/quantum-portfolio-app
git init
```

### 2.2 Add and commit all files

```bash
git add .
git commit -m "Add Render deployment config and health check"
```

### 2.3 Push to GitHub

Create a new repository on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/quantum-portfolio-optimizer.git
git branch -M main
git push -u origin main
```

(Use your actual GitHub repo URL.)

---

## 3. Create a Render Account

1. Go to [render.com](https://render.com).
2. Click **Get Started for Free**.
3. Sign up with **GitHub** (easiest – one-click repo connect).
4. No credit card is required.

---

## 4. Create the Web Service

1. In the Render dashboard, click **New +** → **Web Service**.
2. Connect your **GitHub** account if prompted and select the repository that contains `quantum-portfolio-optimizer` (e.g. `quantum-portfolio-optimizer` or your repo name).
3. Configure the service:

| Field | Value |
|--------|--------|
| **Name** | `quantum-portfolio-optimizer` (or any name you like) |
| **Region** | Choose closest to you (e.g. Oregon, Frankfurt) |
| **Branch** | `main` |
| **Runtime** | **Python 3** |
| **Build Command** | `pip install -r requirements-light.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1` |
| **Plan** | **Free** |

4. (Optional) **Health Check Path**: set to `/api/health` so Render knows when the app is ready.
5. Click **Create Web Service**.

Render will clone the repo, run the build command, then start the app. With `requirements-light.txt`, the build is fast (~1–2 min) and the app uses pure NumPy for optimization—always works on free tier.

---

## 5. Get Your Live URL

When the deploy status is **Live**, Render shows a URL like:

- `https://quantum-portfolio-optimizer.onrender.com`

Open it in your browser. You should see the Quantum Portfolio Optimizer UI.

---

## 6. Verify Deployment

Replace `YOUR_RENDER_URL` with your actual URL, then run:

```bash
python verification.py https://YOUR_RENDER_URL
```

Example:

```bash
python verification.py https://quantum-portfolio-optimizer.onrender.com
```

You should see:

- `OK /`
- `OK /api/health`
- `OK /api/symbols`
- `OK /api/predefined`

---

## 7. Cold Starts (Free Tier)

On the **free** plan, the service **spins down after about 15 minutes** of no traffic. The first request after that will:

- Wake the server (often **30–60 seconds**)
- Then load the page or API as normal

**What to do:**

- The app shows a short notice when it may be waking up (see the homepage).
- For LinkedIn/demos, open the URL once a few minutes before sharing so the instance is already warm.
- If you need no cold starts, you’d need a paid plan (not required for showcasing).

---

## 8. Troubleshooting

### Build fails

- **Error about Python version**  
  Ensure `runtime.txt` contains `python-3.9.18` (or another 3.9.x Render supports). Render uses this for the build.

- **Out of memory during `pip install`**  
  The free instance has limited RAM. If the build fails at install, try:
  - Slightly relaxing version pins in `requirements.txt` (e.g. `qiskit>=1.0.0` is already flexible).
  - Removing any unused dependencies.

- **Qiskit / qiskit-aer install very slow**  
  Normal on first build. Subsequent deploys use cache and are faster.

### App crashes after deploy

- Open the **Logs** tab for your service on Render. Look for Python tracebacks.
- Typical causes:
  - Missing env var: the app uses `PORT` from the environment; Render sets this automatically.
  - Import error: ensure all imports in `app.py`, `data_fetcher.py`, `quantum_optimizer.py` are used in the code paths that run at startup.

### yfinance / market data not loading

- The app already uses in-memory caching (e.g. 5 min TTL) to reduce rate limits.
- If you see “Could not load market data”, wait a minute and try again, or refresh. If it persists, check Render logs for errors from `yfinance`.

### Quantum optimization very slow or timeout

- Free tier has limited CPU. Keep **4–6 assets** and default iterations; the app is tuned for that.
- If a request times out, reduce the number of selected stocks or use “Use quantum (VQE)” unchecked to run classical-only and confirm the rest of the app works.

### Static files (CSS/JS) not loading

- The app serves static files from `/static/` (Flask `static_folder="static"`). No extra config is needed on Render.
- If something 404s, check that the file exists under `static/` and the path in your HTML (e.g. `/static/js/script.js`) is correct.

---

## 9. Updating the App Later

1. Push changes to the same branch (e.g. `main`) on GitHub:
   ```bash
   git add .
   git commit -m "Describe your change"
   git push
   ```
2. Render will **auto-deploy** if “Auto-Deploy” is on (default for the connected branch).
3. Or use the **Manual Deploy** button in the Render dashboard.

---

## 10. Files Used for This Deployment

| File | Purpose |
|------|--------|
| `requirements.txt` | Python dependencies (Flask, gunicorn, Qiskit, yfinance, etc.) |
| `runtime.txt` | Python version for Render (e.g. 3.9.18) |
| `Procfile` | Start command for the web process (`gunicorn app:app ...`) |
| `render.yaml` | Optional Blueprint; same settings as “New Web Service” |
| `.gitignore` | Keeps venv, cache, and secrets out of the repo |
| `app.py` | Uses `PORT` from env and `/api/health` for health checks |
| `verification.py` | Script to test your live URL after deploy |

---

## 11. LinkedIn-Ready Checklist

- **Live URL** – Use your `https://....onrender.com` link in your post.
- **Share button** – The app already has “Generate LinkedIn post” and “Download screenshot” for sharing results.
- **Cold start** – Open the app once before recording or sharing so the first view is fast.
- **Hashtags** – e.g. `#QuantumComputing` `#FinTech` `#PortfolioOptimization` `#Qiskit`

You’re done. You now have a free, public deployment of the Quantum Portfolio Optimizer on Render.
