# QuantumPortfolio — Advanced Portfolio Optimizer

A **professional** web application for portfolio optimization using advanced quantum-inspired algorithms. Features **real-time market data**, multiple industry sectors, and comprehensive analytics. No API keys or cloud credits required.

## Features

- **Real-time market data** – Live prices and analytics via [yfinance](https://pypi.org/project/yfinance/) (no API key); auto-refresh every 5 minutes
- **Industry sectors** – Tech, Finance, Healthcare, Energy, Consumer, Defensive, Growth, and more
- **Advanced optimization** – Quantum-inspired VQE algorithms on Qiskit's Aer simulator
- **User-friendly interface** – Clear explanations for all experience levels, professional design
- **Risk–return visualization** – Interactive scatter plots, efficient frontier, portfolio comparison
- **Historical analysis** – 3-month backtesting with S&P 500 benchmark
- **Risk tolerance control** – Adjustable slider for personalized portfolio recommendations
- **Export capabilities** – Download results as screenshots for reporting
- **Dark/light themes** – Professional appearance with user preference persistence
- **Real-time updates** – Live market data with staleness indicators
- **Demo mode** – Pre-computed data for instant demonstration without network calls

## Tech Stack (100% Free)

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3.9+, Flask |
| Algorithms  | Qiskit, qiskit-finance, qiskit-optimization, qiskit-algorithms, qiskit-aer |
| Market Data | yfinance (no API key required) |
| Frontend    | HTML, Tailwind CSS (CDN), Chart.js, Vanilla JavaScript |
| Deployment  | Gunicorn (Render free tier compatible) |

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Install and Run Locally

```bash
cd quantum-portfolio-app
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001** in your browser.

### Usage

1. **Select stocks:** Choose from industry sectors (Tech, Finance, Healthcare, etc.) or pick individual stocks. 4-6 stocks recommended for optimal performance.
2. **Set budget:** Specify how many different stocks to hold in your portfolio (e.g., 2-3 from 6 options).
3. **Adjust risk tolerance:** Use the slider to balance returns vs. safety (0 = max returns, 1 = min risk).
4. **Optimize:** Click "Optimize My Portfolio" to generate personalized recommendations.
5. **Analyze results:** View recommended portfolio, risk-return charts, historical performance, and detailed analytics.
6. **Export:** Download screenshots of your results for reporting or documentation.

## Available Stock Universe

**20 stocks across multiple sectors:**
- **Technology:** AAPL, GOOGL, MSFT, AMZN, TSLA, META, NVDA, NFLX
- **Finance:** JPM, BAC, WFC
- **Healthcare:** JNJ, PFE, UNH
- **Energy:** XOM, CVX
- **Consumer:** KO, PEP, WMT, DIS

**Predefined sector portfolios for quick selection:**
- Tech (8 stocks)
- Finance (6 stocks)
- Healthcare (6 stocks)
- Energy (6 stocks)
- Consumer (6 stocks)
- Defensive (6 stocks)
- Growth (7 stocks)

## API Endpoints

- `GET /` – Main application interface
- `GET /api/health` – Health check for deployment monitoring
- `GET /api/symbols` – List available symbols with optional market data
- `GET /api/market?symbols=AAPL,GOOGL` – Real-time market data (5-minute cache)
- `GET /api/predefined` – Available sector portfolios
- `POST /api/optimize` – Run portfolio optimization (quantum or classical)
- `GET /api/circuit?numQubits=4` – Generate quantum circuit diagram
- `GET /api/risk-return?symbols=AAPL,GOOGL` – Risk-return analysis with efficient frontier
- `POST /api/backtest` – Historical performance analysis (3 months)
- `GET /api/demo-data` – Pre-computed demo data for instant results

## Why Quantum Computing?

This application uses **real quantum algorithms** (not just buzzwords):

- Portfolio optimization is encoded as a **Quadratic Program** and converted to a qubit Hamiltonian
- **VQE (Variational Quantum Eigensolver)** runs parameterized quantum circuits on Qiskit's Aer simulator
- The algorithm explores multiple portfolio combinations simultaneously through quantum superposition
- Results are compared against classical optimization to demonstrate quantum advantage
- All computations are transparent with detailed probability distributions and convergence metrics

## Performance

- **Assets:** Up to 6 stocks for optimal runtime (~2-5 seconds with 100 VQE iterations)
- **Caching:** Market data cached for 5 minutes; covariance matrices cached per symbol set
- **Backtesting:** 3-month historical analysis with S&P 500 benchmark
- **Real-time:** Auto-refresh every 5 minutes with staleness indicators

## Deployment on Render

1. Push this repository to GitHub
2. On [Render](https://render.com), create a **Web Service**
3. Connect your GitHub repository
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `gunicorn --bind 0.0.0.0:$PORT app:app`
6. **Environment:** Python 3
7. **Plan:** Free tier (no credit card required)
8. (Optional) Set **Health Check Path:** `/api/health`

Your live URL will be `https://<your-service>.onrender.com`

**Note:** Free tier sleeps after 15 minutes of inactivity. First load may take 30-60 seconds (cold start notice displayed in app).

## Docker Deployment (Optional)

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
docker build -t quantumportfolio .
docker run -p 5000:5000 -e PORT=5000 quantumportfolio
```

## Educational Value

This tool is designed for:
- **Learning:** Understand portfolio optimization concepts with clear explanations
- **Demonstration:** Show quantum computing applications in finance
- **Experimentation:** Test different risk profiles and stock combinations
- **Education:** Visualize risk-return tradeoffs and efficient frontiers

**Disclaimer:** This tool is for educational and demonstration purposes only. Always conduct your own research and consult financial advisors before making investment decisions.

## License

This project uses open-source technologies:
- Qiskit (Apache 2.0)
- yfinance (Apache 2.0)
- Flask (BSD 3-Clause)
- Chart.js (MIT)

Free to use and modify for educational and non-commercial purposes.

## Author

**Saad Mohsin**
- GitHub: [@saadsmohsin-web](https://github.com/saadsmohsin-web)

## Acknowledgments

Built with:
- [Qiskit](https://qiskit.org/) - Open-source quantum computing framework
- [yfinance](https://github.com/ranaroussi/yfinance) - Market data without API keys
- [Flask](https://flask.palletsprojects.com/) - Python web framework
- [Chart.js](https://www.chartjs.org/) - Interactive visualizations
- [Tailwind CSS](https://tailwindcss.com/) - Modern UI design
