"""
Quantum Portfolio Optimizer - Flask web application.
Serves live market data and runs real Qiskit VQE + classical optimization.
"""

from __future__ import annotations

import io
import base64
import logging

import numpy as np
from flask import Flask, render_template, request, jsonify

from data_fetcher import (
    DataFetcher,
    DEFAULT_SYMBOLS,
    PREDEFINED_LISTS,
    AssetData,
)
from quantum_optimizer import optimize, OptimizationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_SORT_KEYS"] = False

# Cache for market data (5 min TTL handled inside DataFetcher)
data_fetcher = DataFetcher(cache_ttl_seconds=300)

# Max assets for optimization (keep quantum circuit small and fast)
MAX_ASSETS = 6
MIN_ASSETS = 2
DEFAULT_BUDGET = 2
VQE_MAX_ITER = 100


def asset_to_dict(a: AssetData) -> dict:
    return a.to_dict()


@app.route("/")
def index():
    """Serve the single-page app."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check for Render and load balancers. Returns 200 when the app is up."""
    return jsonify({"status": "ok", "service": "quantum-portfolio-optimizer"}), 200


@app.route("/api/symbols", methods=["GET"])
def api_symbols():
    """Return the list of predefined stock symbols with optional live data."""
    symbols = DEFAULT_SYMBOLS
    with_data = request.args.get("withData", "false").lower() == "true"
    if not with_data:
        return jsonify({"symbols": [{"symbol": s, "name": s} for s in symbols]})
    assets = data_fetcher.get_assets(symbols)
    return jsonify({
        "symbols": [asset_to_dict(a) for a in assets],
    })


@app.route("/api/market", methods=["GET"])
def api_market():
    """Fetch market data for given symbols (query param symbols=AAA,BBB,CCC)."""
    raw = request.args.get("symbols", "")
    symbols = [s.strip() for s in raw.split(",") if s.strip()] if raw else DEFAULT_SYMBOLS
    symbols = symbols[:MAX_ASSETS + 4]  # allow a few extra for display
    assets = data_fetcher.get_assets(symbols)
    return jsonify({"assets": [asset_to_dict(a) for a in assets]})


@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    """
    Run portfolio optimization.
    Body: { "symbols": ["AAPL","GOOGL",...], "budget": 2, "riskFactor": 0.5, "useQuantum": true }
    """
    try:
        body = request.get_json() or {}
        symbols = body.get("symbols") or []
        budget = int(body.get("budget", DEFAULT_BUDGET))
        risk_factor = float(body.get("riskFactor", 0.5))
        use_quantum = body.get("useQuantum", True)

        if len(symbols) < MIN_ASSETS:
            return jsonify({"error": f"Select at least {MIN_ASSETS} assets"}), 400
        if len(symbols) > MAX_ASSETS:
            return jsonify({"error": f"Select at most {MAX_ASSETS} assets for fast optimization"}), 400
        if budget < 1 or budget >= len(symbols):
            return jsonify({"error": "Budget must be between 1 and (number of assets - 1)"}), 400

        risk_factor = max(0.01, min(1.0, risk_factor))
        symbols = list(symbols)[:MAX_ASSETS]

        # Get expected returns and covariance from historical data
        mu, sigma = data_fetcher.get_expected_returns_and_covariance(symbols, use_cache=True)
        assets = data_fetcher.get_assets(symbols)

        classical, quantum = optimize(
            mu, sigma, risk_factor, budget, use_quantum=use_quantum, vqe_maxiter=VQE_MAX_ITER
        )

        # Build response with asset names for display
        symbol_list = [a.symbol for a in assets]
        name_by_idx = {i: assets[i].name for i in range(len(assets))}

        def result_payload(r: OptimizationResult) -> dict:
            d = r.to_dict()
            d["selectedSymbols"] = [symbol_list[i] for i in r.selected_indices]
            d["selectedNames"] = [name_by_idx.get(i, symbol_list[i]) for i in r.selected_indices]
            return d

        # Objective gap: how close quantum solution is to classical optimum (real metric)
        objective_gap = None
        if quantum and classical and classical.objective_value != 0:
            objective_gap = (quantum.objective_value - classical.objective_value) / abs(
                classical.objective_value
            )

        response = {
            "classical": result_payload(classical),
            "quantum": result_payload(quantum) if quantum else None,
            "symbols": symbol_list,
            "assetNames": name_by_idx,
            "objectiveGap": objective_gap,
        }
        return jsonify(response)
    except Exception as e:
        logger.exception("Optimize failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/circuit", methods=["GET"])
def api_circuit():
    """Generate a quantum circuit diagram (PNG) and return circuit stats (qubits, parameters, depth)."""
    try:
        n = int(request.args.get("numQubits", 4))
        n = max(2, min(6, n))
        from qiskit.circuit.library import n_local
        ansatz = n_local(n, "ry", "cz", entanglement="full", reps=2)
        num_parameters = ansatz.num_parameters
        depth = ansatz.depth()
        buf = io.BytesIO()
        fig = ansatz.draw(output="mpl")
        if fig is not None:
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
            import matplotlib.pyplot as plt
            plt.close(fig)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        return jsonify({
            "imageBase64": b64,
            "numQubits": n,
            "numParameters": num_parameters,
            "depth": depth,
        })
    except Exception as e:
        logger.exception("Circuit image failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/predefined", methods=["GET"])
def api_predefined():
    """Return predefined stock list names and their symbols."""
    lists = {}
    for name, symbols in PREDEFINED_LISTS.items():
        lists[name] = symbols
    return jsonify({"lists": lists})


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    """
    Historical backtest: cumulative returns for quantum, classical, equal-weight, benchmark.
    Body: { "symbols": [...], "quantumIndices": [0,1], "classicalIndices": [0,2], "days": 90 }
    """
    try:
        body = request.get_json() or {}
        symbols = body.get("symbols") or []
        quantum_indices = body.get("quantumIndices") or []
        classical_indices = body.get("classicalIndices") or []
        days = int(body.get("days", 90))
        days = max(30, min(365, days))
        if not symbols:
            return jsonify({"error": "symbols required"}), 400
        curves = data_fetcher.get_backtest_curves(
            symbols, quantum_indices, classical_indices, days=days
        )
        if curves is None:
            return jsonify({"error": "Could not compute backtest (check data)"}), 503
        return jsonify(curves)
    except Exception as e:
        logger.exception("Backtest failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/risk-return", methods=["GET"])
def api_risk_return():
    """
    Risk–return data for scatter plot and efficient frontier.
    Query: symbols=AAPL,GOOGL,... or from last optimization (we need symbols).
    Returns assets (expectedReturn, volatility), efficient frontier points,
    and optionally classical/quantum portfolio point (from last run we don't have; frontend can pass).
    """
    try:
        raw = request.args.get("symbols", "")
        symbols = [s.strip() for s in raw.split(",") if s.strip()] if raw else DEFAULT_SYMBOLS
        symbols = symbols[:MAX_ASSETS + 4]
        assets = data_fetcher.get_assets(symbols)
        if len(assets) < 2:
            return jsonify({"assets": [], "efficientFrontier": []})
        mu, sigma = data_fetcher.get_expected_returns_and_covariance(
            [a.symbol for a in assets], use_cache=True
        )
        n = len(assets)
        # Per-asset risk = sqrt(sigma_ii), return = mu_i
        volatilities = [float(np.sqrt(max(sigma[i, i], 0))) for i in range(n)]
        returns = [float(mu[i]) for i in range(n)]
        asset_points = [
            {"symbol": assets[i].symbol, "name": assets[i].name, "return": returns[i], "risk": volatilities[i]}
            for i in range(n)
        ]
        # Efficient frontier: for discrete budget-k problem, compute all C(n,k) portfolios for k=1..n-1
        # and return Pareto-optimal (risk, return) points. Keep it simple: grid of risk factors.
        import itertools
        frontier = []
        for k in range(1, n):
            for combo in itertools.combinations(range(n), k):
                w = 1.0 / k
                weights = np.zeros(n)
                for i in combo:
                    weights[i] = w
                ret = float(np.dot(weights, mu))
                risk = float(np.sqrt(np.dot(weights, np.dot(sigma, weights))))
                frontier.append({"return": ret, "risk": risk})
        # Sort by risk, then take Pareto front (max return for given risk)
        frontier.sort(key=lambda p: (p["risk"], -p["return"]))
        pareto = []
        best_ret = -1e9
        for p in frontier:
            if p["return"] > best_ret:
                best_ret = p["return"]
                pareto.append(p)
        return jsonify({"assets": asset_points, "efficientFrontier": pareto})
    except Exception as e:
        logger.exception("Risk-return failed: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    # Use PORT from environment (e.g. Render) or 5001 to avoid macOS AirPlay using 5000
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
