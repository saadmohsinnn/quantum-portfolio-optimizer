# Publish Your App – Quick Steps

Your code is committed locally and the GitHub remote is set. Follow these two parts.

---

## Part 1: Push to GitHub (do this once from your computer)

Open a terminal in this project folder and run:

```bash
cd /Users/saadmohsin/quantum-portfolio-app
git push -u origin main
```

- If GitHub asks for a **password**, use a **Personal Access Token** (not your account password). Create one: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (with `repo` scope).
- Or use **SSH** instead of HTTPS:  
  `git remote set-url origin git@github.com:saadsmohsin-web/quanport.git`  
  then run `git push -u origin main` again (requires SSH key set up with GitHub).

After this, your repo will be live at: **https://github.com/saadsmohsin-web/quanport**

---

## Part 2: Deploy to Render (free, live URL)

1. Go to **[render.com](https://render.com)** and sign in (e.g. with GitHub).

2. Click **New +** → **Web Service**.

3. Connect the repo **saadsmohsin-web/quanport** (authorize Render if asked).

4. Use these settings:

   | Field | Value |
   |--------|--------|
   | **Name** | `quanport` (or any name) |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |
   | **Plan** | **Free** |

5. (Optional) Under **Advanced**, set **Health Check Path** to: `/api/health`

6. Click **Create Web Service**.

7. Wait for the first deploy (about 5–10 minutes). When status is **Live**, open the URL (e.g. `https://quanport.onrender.com`).

8. Verify from your machine:
   ```bash
   python verification.py https://YOUR-APP-URL.onrender.com
   ```

**Note:** On the free plan, the app sleeps after ~15 min of no traffic. The first request after that may take 30–60 seconds (see the notice on the app).

---

For more detail (troubleshooting, cold starts, updating the app), see **[DEPLOY.md](DEPLOY.md)**.
