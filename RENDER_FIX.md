# Fix "Optimization failed" on Render

The app now uses a **pure NumPy optimizer** that doesn't require Qiskit. This fixes OOM and timeout issues on Render's free tier.

## 1. Update Build Command in Render Dashboard

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Select your **quantum-playground** (or quantum-portfolio-optimizer) service
3. Go to **Settings** → **Build & Deploy**
4. Set **Build Command** to:
   ```
   pip install -r requirements-light.txt
   ```
5. Set **Start Command** to:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
   ```
6. Click **Save Changes** and trigger a **Manual Deploy**

## 2. What Changed

- **requirements-light.txt**: No Qiskit (saves ~500MB RAM). Uses NumPy only.
- **classical_optimizer.py**: Exact brute-force portfolio optimization. Always works.
- **Demo mode** (default): Uses static data. No network calls. Instant.

## 3. Alternative Hosts

If Render still has issues, try:

- **Koyeb** (free tier): Connect your GitHub repo, use the provided `Dockerfile`
- **Railway**: $5 credit for new users; may run full `requirements.txt` with Qiskit
