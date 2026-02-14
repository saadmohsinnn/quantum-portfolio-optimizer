"""
Pure NumPy portfolio optimizer - no Qiskit required.
Guarantees optimization works on memory-constrained hosts (Render free tier, etc.).
Uses brute-force enumeration for small n (≤12 assets); exact and deterministic.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

import numpy as np

from quantum_optimizer import OptimizationResult


def run_classical_numpy(
    mu: np.ndarray,
    sigma: np.ndarray,
    risk_factor: float,
    budget: int,
) -> OptimizationResult:
    """
    Exact classical portfolio optimization using brute-force enumeration.
    Matches Qiskit's PortfolioOptimization formulation:
      minimize: risk_factor * (x^T sigma x) - (1 - risk_factor) * (mu^T x)
      subject to: sum(x) = budget, x in {0,1}^n
    Uses only NumPy - no Qiskit, no heavy dependencies. Always succeeds.
    """
    t0 = time.perf_counter()
    n = len(mu)
    best_obj = np.inf
    best_x = np.zeros(n)

    for indices in itertools.combinations(range(n), budget):
        x = np.zeros(n)
        for i in indices:
            x[i] = 1.0
        # Objective: q * x^T sigma x - (1-q) * mu^T x
        var = float(np.dot(x, np.dot(sigma, x)))
        ret = float(np.dot(mu, x))
        obj = risk_factor * var - (1.0 - risk_factor) * ret
        if obj < best_obj:
            best_obj = obj
            best_x = x.copy()

    elapsed_ms = (time.perf_counter() - t0) * 1000
    selected = [i for i in range(n) if best_x[i] >= 0.5]
    k = len(selected)
    weights = {i: 1.0 / k if i in selected else 0.0 for i in range(n)}

    ret_val = float(np.mean([mu[i] for i in selected])) if k else 0.0
    w_vec = np.array([1.0 / k if i in selected else 0.0 for i in range(n)])
    risk_val = float(np.sqrt(np.dot(w_vec, np.dot(sigma, w_vec))))

    bitstring = "".join(str(int(best_x[i])) for i in range(n))
    return OptimizationResult(
        selected_indices=selected,
        weights=weights,
        objective_value=best_obj,
        expected_return=ret_val,
        risk=risk_val,
        computation_time_ms=elapsed_ms,
        method_used="Classical (exact)",
        probability_distribution={bitstring: 1.0},
        convergence_history=[],
    )
