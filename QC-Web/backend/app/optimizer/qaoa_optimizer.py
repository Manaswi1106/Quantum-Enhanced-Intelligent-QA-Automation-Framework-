"""QAOA optimizer using Qiskit + Qiskit Aer for test-case selection.

QAOA decides WHAT to test. Playwright executes HOW to test.
This runs as a local Qiskit Aer simulation — not on quantum hardware.
"""
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def run_qaoa(
    qubo_matrix: list[list[float]],
    test_ids: list[int],
    budget: int = 10,
    p: int = 1,
    shots: int = 1024,
) -> dict:
    """Run QAOA optimization on the QUBO matrix using Qiskit Aer simulation.

    Args:
        qubo_matrix: n×n QUBO matrix (as nested lists)
        test_ids: list of test case IDs corresponding to matrix indices
        budget: max tests to select
        p: QAOA circuit depth (number of layers)
        shots: number of measurement shots

    Returns:
        dict with selected_tests, excluded_tests, objective_value, metadata
    """
    n = len(qubo_matrix)

    if n == 0:
        return {
            "selected_tests": [],
            "excluded_tests": [],
            "objective_value": 0.0,
            "metadata": {"error": "Empty QUBO matrix"},
        }

    Q = np.array(qubo_matrix)

    # For small problems (n <= 20), use full QAOA circuit
    # For larger problems, use a greedy-quantum-hybrid approach
    if n <= 20:
        result = _run_qaoa_circuit(Q, n, p, shots)
    else:
        # For large problems: partition into subproblems
        logger.info(f"Large problem (n={n}), using hybrid approach")
        result = _run_hybrid_qaoa(Q, n, p, shots, budget)

    bitstring = result["best_bitstring"]
    obj_value = result["objective_value"]

    selected = []
    excluded = []
    for i, bit in enumerate(bitstring):
        if bit == 1:
            selected.append(test_ids[i])
        else:
            excluded.append(test_ids[i])

    # If sampling yielded zero selected tests, pick the highest value test(s) by diagonal QUBO score
    if len(selected) == 0 and len(test_ids) > 0 and budget > 0:
        scored = [(tid, Q[i, i]) for i, tid in enumerate(test_ids)]
        scored.sort(key=lambda x: x[1])  # most negative first
        k = min(budget, max(1, min(len(test_ids), 3)))
        selected = [s[0] for s in scored[:k]]
        excluded = [tid for tid in test_ids if tid not in selected]
        sel_indices = [test_ids.index(tid) for tid in selected]
        obj_value = _evaluate_objective(Q, sel_indices)

    # Enforce budget: if more than budget selected, keep the best
    if len(selected) > budget:
        # Score each selected test by its diagonal QUBO value (more negative = more valuable)
        scored = [(tid, Q[test_ids.index(tid), test_ids.index(tid)]) for tid in selected]
        scored.sort(key=lambda x: x[1])  # most negative first (most valuable)
        selected = [s[0] for s in scored[:budget]]
        excluded = [tid for tid in test_ids if tid not in selected]

        # Recalculate objective
        sel_indices = [test_ids.index(tid) for tid in selected]
        obj_value = _evaluate_objective(Q, sel_indices)

    return {
        "selected_tests": selected,
        "excluded_tests": excluded,
        "objective_value": float(obj_value),
        "metadata": {
            "simulator": "qiskit_aer",
            "method": "qaoa_simulation",
            "p": p,
            "shots": shots,
            "num_variables": n,
            "num_selected": len(selected),
            "num_excluded": len(excluded),
            "best_bitstring": "".join(str(b) for b in bitstring),
            "all_counts": result.get("counts", {}),
        },
    }


def _run_qaoa_circuit(Q: np.ndarray, n: int, p: int, shots: int) -> dict:
    """Run actual QAOA circuit using Qiskit + Aer."""
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
        from scipy.optimize import minimize

        simulator = AerSimulator()

        def create_qaoa_circuit(gamma_list, beta_list):
            """Create QAOA circuit with given parameters."""
            qc = QuantumCircuit(n)

            # Initial state: uniform superposition
            for i in range(n):
                qc.h(i)

            # QAOA layers
            for layer in range(p):
                gamma = gamma_list[layer]
                beta = beta_list[layer]

                # Cost unitary: exp(-i * gamma * C)
                # For QUBO diagonal terms
                for i in range(n):
                    if abs(Q[i, i]) > 1e-10:
                        qc.rz(2 * gamma * Q[i, i], i)

                # For QUBO off-diagonal terms (ZZ interactions)
                for i in range(n):
                    for j in range(i + 1, n):
                        if abs(Q[i, j] + Q[j, i]) > 1e-10:
                            coeff = (Q[i, j] + Q[j, i]) / 2
                            qc.cx(i, j)
                            qc.rz(2 * gamma * coeff, j)
                            qc.cx(i, j)

                # Mixer unitary: exp(-i * beta * B)
                for i in range(n):
                    qc.rx(2 * beta, i)

            qc.measure_all()
            return qc

        def objective_function(params):
            """Evaluate QAOA with given parameters."""
            gamma_list = params[:p]
            beta_list = params[p:]

            qc = create_qaoa_circuit(gamma_list, beta_list)
            job = simulator.run(qc, shots=shots)
            counts = job.result().get_counts()

            # Calculate expectation value
            total_val = 0.0
            for bitstring, count in counts.items():
                bits = [int(b) for b in reversed(bitstring)]  # LSB first
                val = 0.0
                for i in range(n):
                    for j in range(n):
                        val += Q[i, j] * bits[i] * bits[j]
                total_val += val * count

            return total_val / shots

        # Optimize QAOA parameters
        np.random.seed(42)
        initial_params = np.random.uniform(0, np.pi, 2 * p)

        result = minimize(
            objective_function,
            initial_params,
            method="COBYLA",
            options={"maxiter": 100, "rhobeg": 0.5},
        )

        # Get the best bitstring from final circuit
        optimal_gamma = result.x[:p]
        optimal_beta = result.x[p:]
        final_qc = create_qaoa_circuit(optimal_gamma, optimal_beta)
        final_job = simulator.run(final_qc, shots=shots)
        final_counts = final_job.result().get_counts()

        # Find best bitstring (lowest objective value)
        best_bitstring = None
        best_value = float("inf")
        for bitstring_str, count in final_counts.items():
            bits = [int(b) for b in reversed(bitstring_str)]
            val = sum(Q[i, j] * bits[i] * bits[j] for i in range(n) for j in range(n))
            if val < best_value:
                best_value = val
                best_bitstring = bits

        # Get top 5 bitstrings for metadata
        top_counts = dict(sorted(final_counts.items(), key=lambda x: -x[1])[:5])

        return {
            "best_bitstring": best_bitstring or [0] * n,
            "objective_value": best_value,
            "counts": top_counts,
        }

    except Exception as e:
        logger.error(f"QAOA circuit execution failed: {e}")
        # Fallback to classical greedy
        return _classical_fallback(Q, n)


def _run_hybrid_qaoa(Q: np.ndarray, n: int, p: int, shots: int, budget: int) -> dict:
    """Hybrid approach for large problems: score + QAOA on top candidates."""
    # Score all tests by diagonal value
    scores = [(-Q[i, i], i) for i in range(n)]
    scores.sort(reverse=True)

    # Take top min(20, n) candidates for QAOA
    top_k = min(20, n)
    top_indices = [s[1] for s in scores[:top_k]]

    # Build sub-QUBO
    sub_Q = np.zeros((top_k, top_k))
    for i_new, i_old in enumerate(top_indices):
        for j_new, j_old in enumerate(top_indices):
            sub_Q[i_new, j_new] = Q[i_old, j_old]

    # Run QAOA on sub-problem
    sub_result = _run_qaoa_circuit(sub_Q, top_k, p, shots)

    # Map back to original indices
    full_bitstring = [0] * n
    for i_new, bit in enumerate(sub_result["best_bitstring"]):
        full_bitstring[top_indices[i_new]] = bit

    return {
        "best_bitstring": full_bitstring,
        "objective_value": sub_result["objective_value"],
        "counts": sub_result.get("counts", {}),
    }


def _classical_fallback(Q: np.ndarray, n: int) -> dict:
    """Classical greedy fallback if QAOA fails."""
    logger.warning("Using classical greedy fallback")
    # Select tests with most negative diagonal values (highest value)
    scores = [(-Q[i, i], i) for i in range(n)]
    scores.sort(reverse=True)

    bitstring = [0] * n
    for score, idx in scores:
        if score > 0:
            bitstring[idx] = 1

    obj_val = sum(Q[i, j] * bitstring[i] * bitstring[j] for i in range(n) for j in range(n))

    return {
        "best_bitstring": bitstring,
        "objective_value": obj_val,
        "counts": {"classical_fallback": 1},
    }


def _evaluate_objective(Q: np.ndarray, selected_indices: list[int]) -> float:
    """Evaluate QUBO objective for given selected indices."""
    n = Q.shape[0]
    bits = [0] * n
    for i in selected_indices:
        bits[i] = 1
    return sum(Q[i, j] * bits[i] * bits[j] for i in range(n) for j in range(n))
