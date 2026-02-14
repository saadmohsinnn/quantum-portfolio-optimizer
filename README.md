# Quantumport– Web App

A **free** web application that lets you select stocks, fetch **live market data**, and run a **real quantum optimization** (VQE on Qiskit’s Aer simulator) to suggest an optimal portfolio. No API keys or cloud credits required.

## Features

- **Live market data** – Current prices and returns via [yfinance](https://pypi.org/project/yfinance/) (no API key); auto-refresh every 5 minutes
- **Predefined stock lists** – Finnish stocks, Tech Giants, EU Banks (one-click selection)
- **Quantum optimization** – Real Qiskit circuits: portfolio problem → Quadratic Program → VQE on Aer simulator
- **Explainability** – Tooltips on qubit, superposition, entanglement, VQE; “How it works” sidebar in plain language
- **Risk–return visualization** – Scatter plot of stocks, efficient frontier, quantum vs classical portfolio highlighted
- **Quantum circuit viewer** – Toggle to show the actual VQE ansatz circuit diagram
- **Historical backtest** – 3‑month cumulative returns: quantum portfolio vs classical vs equal-weight vs S&P 500
- **Risk tolerance slider** – Adjust risk (0 = max return, 1 = min risk); re-runs optimization with backend caching
- **Shareable results** – “Generate LinkedIn post” and download screenshot (html2canvas) for sharing
- **Dark/light mode** – Toggle with persistence
- **Progress & timing** – Progress bar during VQE; “Quantum simulation completed in X.XX seconds”
- **Error handling** – Friendly messages; fallback to classical if VQE fails; stale data indicator
- **Educational video** – Optional “What is Quantum Computing?” YouTube embed in a modal

## Tech stack (100% free)

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3.9+, Flask |
| Quantum     | Qiskit, qiskit-finance, qiskit-optimization, qiskit-algorithms, qiskit-aer |
| Data        | yfinance (no API key) |
| Frontend    | HTML, Tailwind CSS (CDN), Chart.js, vanilla JS, html2canvas (CDN) |
| Deployment  | gunicorn (e.g. Render free tier) |

## Quick start

### Prerequisites

- Python 3.9+
- pip

### Install and run locally

```bash
cd quantum-portfolio-app
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001** (or the port shown in the terminal; 5000 may be used by macOS AirPlay) in your browser.

### Usage

1. Use **Quick select** (Finnish, Tech Giants, EU Banks, All) or pick stocks manually (4–6 for fast optimization).
2. Set **Budget** (how many assets to hold) and **Risk tolerance** (0 = max return, 1 = min risk).
3. Check **Use quantum (VQE)** and click **Run optimization**.
4. View recommended portfolio, risk–return chart, probability distribution, convergence, and **Show quantum circuit**.
5. Click **Show historical performance** for the 3‑month backtest; use **Generate LinkedIn post** or **Download screenshot** to share.

## Demo script for LinkedIn

Use this to present the app in a post or video:

1. **Hook** – “I built a portfolio optimizer that uses real quantum circuits (VQE) to pick stocks.”
2. **Show** – Open the app; pick a list (e.g. Tech Giants); run optimization; point out “Quantum simulation completed in X seconds” and the recommended portfolio.
3. **Explain** – “Each stock is a qubit; the circuit explores combinations in superposition; measurement gives the best portfolio. Here’s the actual circuit we use.” (Toggle “Show quantum circuit”.)
4. **Proof** – “Show historical performance” to compare quantum vs classical vs S&P 500 over 3 months.
5. **CTA** – “Try it yourself – no API keys, runs in the browser. Link in comments. #QuantumComputing #FinTech #PortfolioOptimization”

**Suggested hashtags:** `#QuantumComputing` `#FinTech` `#PortfolioOptimization` `#Qiskit` `#QuantumFinance`

## API (for frontend / scripting)

- `GET /` – Serves the single-page UI.
- `GET /api/symbols` – List of predefined symbols. `?withData=true` returns current market data.
- `GET /api/market?symbols=AAPL,GOOGL` – Market data for given symbols (cached; 5‑min TTL).
- `GET /api/predefined` – Predefined lists: `{ "lists": { "finnish": [...], "tech_giants": [...], ... } }`.
- `POST /api/optimize` – Body: `{ "symbols": [...], "budget": 2, "riskFactor": 0.5, "useQuantum": true }`. Returns classical and (if requested) quantum results.
- `GET /api/circuit?numQubits=4` – Returns `{ "imageBase64": "..." }` for the VQE ansatz circuit (PNG).
- `GET /api/risk-return?symbols=AAPL,GOOGL` – Returns `{ "assets": [{ symbol, name, return, risk }], "efficientFrontier": [...] }`.
- `POST /api/backtest` – Body: `{ "symbols": [...], "quantumIndices": [0,1], "classicalIndices": [0,2], "days": 90 }`. Returns `{ "dates", "quantum", "classical", "equalWeight", "benchmark" }` (cumulative return curves).

## Why this is “real” quantum

- The portfolio problem is encoded as a **Quadratic Program** and then as a qubit Hamiltonian (Qiskit Finance + Optimization).
- **VQE** runs actual parameterized circuits (e.g. `n_local` with RY + CZ) on the **Aer simulator**.
- Measurement gives a **probability distribution** over bitstrings (portfolios); we show the top outcomes and compare with the **exact classical** solution.
- No classical-only heuristic is labeled as “quantum”; the backend uses Qiskit’s VQE and classical reference solver.

## Performance and limits

- **Assets** – Up to 6 for reasonable VQE runtime (~2–5 s with ~100 iterations).
- **Caching** – Market data TTL 5 minutes; covariance cached per symbol set for fast risk-slider re-runs.
- **Backtest** – 3 months (90 days) of history; S&P 500 as benchmark.

## Deployment (e.g. Render)

1. Push the project to GitHub.
2. On [Render](https://render.com), create a new **Web Service**, connect the repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `gunicorn --bind 0.0.0.0:$PORT app:app`
5. **PORT** is set automatically by Render.

No database or Redis required; in-memory caching is enough for the free tier.

For **step-by-step deployment on Render** (free tier, no credit card), see **[DEPLOY.md](DEPLOY.md)**. Summary:

1. Push the repo to GitHub.
2. On [Render](https://render.com): **New +** → **Web Service** → connect the repo.
3. Set **Build Command:** `pip install -r requirements.txt`, **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`, **Plan:** Free.
4. (Optional) Set **Health Check Path** to `/api/health`.
5. Deploy; your live URL will be `https://<your-service>.onrender.com`.

After deploy, run `python verification.py https://<your-service>.onrender.com` to verify. Free tier may sleep after ~15 min; first load after that can take 30–60 s (see cold-start notice on the app).

## Optional: run with Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t quantum-portfolio-app .
docker run -p 5000:5000 -e PORT=5000 quantum-portfolio-app
```

## Predefined symbols and lists

- **Default symbols** (in `data_fetcher.py`): Nokia (NOK), Nordea (NDA-FI.HE), Fortum (FORTUM.HE), UPM (UPM.HE), Kone (KONE.HE), Apple (AAPL), Google (GOOGL), Microsoft (MSFT), Amazon (AMZN), Tesla (TSLA).
- **Predefined lists**: Finnish (NOK, Nordea, Fortum, UPM, Kone, Kesko), Tech Giants (AAPL, GOOGL, MSFT, AMZN, META, NVDA), EU Banks (Nordea, Deutsche Bank, BNP, Santander, ING, Société Générale), All (default symbols).

## License

Use and modify freely. Qiskit is Apache 2.0; yfinance and Flask have their own permissive licenses.
