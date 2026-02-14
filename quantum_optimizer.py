"""
Real quantum portfolio optimization using Qiskit (VQE + classical exact).
Encodes the portfolio problem into qubits and runs actual quantum circuits on the Aer simulator.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports so the app starts even if Qiskit is slow to load
_qiskit_imported = False
_PortfolioOptimization = None
_MinimumEigenOptimizer = None
_NumPyMinimumEigensolver = None
_SamplingVQE = None
_COBYLA = None
_algorithm_globals = None
_n_local = None
_QuasiDistribution = None
_SamplerV2 = None


def _ensure_qiskit():
    global _qiskit_imported, _PortfolioOptimization, _MinimumEigenOptimizer
    global _NumPyMinimumEigensolver, _SamplingVQE, _COBYLA, _algorithm_globals
    global _n_local, _QuasiDistribution, _SamplerV2
    if _qiskit_imported:
        return
    from qiskit.circuit.library import n_local
    from qiskit.result import QuasiDistribution
    from qiskit_finance.applications.optimization import PortfolioOptimization
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    try:
        from qiskit_algorithms import NumPyMinimumEigensolver, SamplingVQE
        from qiskit_algorithms.optimizers import COBYLA
        from qiskit_algorithms.utils import algorithm_globals
        from qiskit_aer.primitives import SamplerV2
    except ImportError:
        from qiskit_optimization.minimum_eigensolvers import (
            NumPyMinimumEigensolver,
            SamplingVQE,
        )
        from qiskit_optimization.optimizers import COBYLA
        from qiskit_optimization.utils import algorithm_globals
        from qiskit_aer.primitives import SamplerV2
    _n_local = n_local
    _QuasiDistribution = QuasiDistribution
    _PortfolioOptimization = PortfolioOptimization
    _MinimumEigenOptimizer = MinimumEigenOptimizer
    _NumPyMinimumEigensolver = NumPyMinimumEigensolver
    _SamplingVQE = SamplingVQE
    _COBYLA = COBYLA
    _algorithm_globals = algorithm_globals
    _SamplerV2 = SamplerV2
    _qiskit_imported = True


@dataclass
class OptimizationResult:
    """Result of portfolio optimization (classical and/or quantum)."""
    selected_indices: list[int]           # indices of selected assets
    weights: dict[int, float]             # index -> weight
    objective_value: float
    expected_return: float
    risk: float
    computation_time_ms: float
    method_used: str
    probability_distribution: dict[str, float] = field(default_factory=dict)  # e.g. "1,0,1,0" -> prob
    convergence_history: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "selectedIndices": self.selected_indices,
            "weights": {str(k): v for k, v in self.weights.items()},
            "objectiveValue": self.objective_value,
            "expectedReturn": self.expected_return,
            "risk": self.risk,
            "computationTimeMs": self.computation_time_ms,
            "methodUsed": self.method_used,
            "probabilityDistribution": self.probability_distribution,
            "convergenceHistory": self.convergence_history,
        }


def run_classical(mu: np.ndarray, sigma: np.ndarray, risk_factor: float, budget: int) -> OptimizationResult:
    """Exact classical solution (NumPy minimum eigensolver)."""
    _ensure_qiskit()
    t0 = time.perf_counter()
    portfolio = _PortfolioOptimization(
        expected_returns=mu,
        covariances=sigma,
        risk_factor=risk_factor,
        budget=budget,
    )
    qp = portfolio.to_quadratic_program()
    exact_mes = _NumPyMinimumEigensolver()
    exact_opt = _MinimumEigenOptimizer(exact_mes)
    result = exact_opt.solve(qp)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    x = result.x
    selected = [i for i in range(len(x)) if x[i] >= 0.5]
    k = len(selected)
    weights = {i: 1.0 / k if i in selected else 0.0 for i in range(len(x))}
    ret = _portfolio_return(x, mu, k)
    risk = _portfolio_risk(x, sigma, k)
    return OptimizationResult(
        selected_indices=selected,
        weights=weights,
        objective_value=float(result.fval),
        expected_return=ret,
        risk=risk,
        computation_time_ms=elapsed_ms,
        method_used="Classical (exact)",
        probability_distribution={"".join(map(str, x.astype(int))): 1.0},
        convergence_history=[],
    )


def run_vqe(
    mu: np.ndarray,
    sigma: np.ndarray,
    risk_factor: float,
    budget: int,
    maxiter: int = 100,
    reps: int = 2,
) -> OptimizationResult:
    """
    Quantum solution using SamplingVQE (real quantum circuits on Aer simulator).
    Keeps iterations low for fast web response (~2–5 seconds).
    """
    _ensure_qiskit()
    t0 = time.perf_counter()
    n = len(mu)
    portfolio = _PortfolioOptimization(
        expected_returns=mu,
        covariances=sigma,
        risk_factor=risk_factor,
        budget=budget,
    )
    qp = portfolio.to_quadratic_program()
    _algorithm_globals.random_seed = 42
    convergence: list[float] = []

    def callback(_n: int, _params: np.ndarray, mean: float, _meta: Any = None) -> None:
        convergence.append(float(mean))

    cobyla = _COBYLA()
    cobyla.set_options(maxiter=maxiter)
    ansatz = _n_local(n, "ry", "cz", entanglement="full", reps=reps)
    sampler = _SamplerV2(seed=42)
    svqe = _SamplingVQE(
        sampler=sampler,
        ansatz=ansatz,
        optimizer=cobyla,
        callback=callback,
    )
    opt = _MinimumEigenOptimizer(svqe)
    result = opt.solve(qp)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    x = result.x
    selected = [i for i in range(len(x)) if x[i] >= 0.5]
    k = max(len(selected), 1)
    weights = {i: 1.0 / k if i in selected else 0.0 for i in range(len(x))}
    ret = _portfolio_return(x, mu, k)
    risk = _portfolio_risk(x, sigma, k)
    prob_dist = _extract_probabilities(result)
    return OptimizationResult(
        selected_indices=selected,
        weights=weights,
        objective_value=float(result.fval),
        expected_return=ret,
        risk=risk,
        computation_time_ms=elapsed_ms,
        method_used="Quantum (VQE)",
        probability_distribution=prob_dist,
        convergence_history=convergence,
    )


def _portfolio_return(x: np.ndarray, mu: np.ndarray, k: int) -> float:
    if k == 0:
        return 0.0
    w = 1.0 / k
    return float(np.sum(mu * (x >= 0.5)) * w)


def _portfolio_risk(x: np.ndarray, sigma: np.ndarray, k: int) -> float:
    if k == 0:
        return 0.0
    w = 1.0 / k
    sel = x >= 0.5
    return float(np.sqrt(np.dot(w * sel, np.dot(sigma, w * sel))))


def _extract_probabilities(result: Any) -> dict[str, float]:
    """Extract binary outcome probabilities from VQE result."""
    out: dict[str, float] = {}
    try:
        eigenstate = result.min_eigen_solver_result.eigenstate
        if eigenstate is None:
            return out
        if isinstance(eigenstate, _QuasiDistribution):
            probs = eigenstate.binary_probabilities()
        elif isinstance(eigenstate, dict):
            probs = eigenstate
        else:
            probs = {k: abs(v) ** 2 for k, v in eigenstate.to_dict().items()}
        for key, p in probs.items():
            if isinstance(key, str):
                out[key] = float(p)
            else:
                out["".join(str(int(i)) for i in key)] = float(p)
    except Exception as e:
        logger.warning("Could not extract probabilities: %s", e)
    return out


def optimize(
    mu: np.ndarray,
    sigma: np.ndarray,
    risk_factor: float,
    budget: int,
    use_quantum: bool = True,
    vqe_maxiter: int = 100,
) -> tuple[OptimizationResult, Optional[OptimizationResult]]:
    """
    Run classical (always) and optionally quantum optimization.
    Returns (classical_result, quantum_result or None).
    """
    classical = run_classical(mu, sigma, risk_factor, budget)
    quantum = None
    if use_quantum:
        try:
            quantum = run_vqe(mu, sigma, risk_factor, budget, maxiter=vqe_maxiter, reps=2)
        except Exception as e:
            logger.exception("VQE failed: %s", e)
    return classical, quantum
