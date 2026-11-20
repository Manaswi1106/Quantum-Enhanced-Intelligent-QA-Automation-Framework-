"""QUBO formulation for test-case selection optimization."""
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "change_impact": 0.30,
    "failure_rate": 0.20,
    "coverage": 0.20,
    "risk": 0.20,
    "efficiency": 0.10,
}


def build_qubo(
    test_cases: list[dict],
    weights: Optional[dict] = None,
    budget: int = 10,
    penalty_strength: float = 2.0,
) -> dict:
    """Build a QUBO matrix for test-case selection optimization.

    Each test case i has binary variable x_i:
      x_i = 1  →  test selected
      x_i = 0  →  test not selected

    Objective: maximize total test value while respecting budget constraint.

    Value of test i = weighted sum of:
      - change_impact
      - failure_rate (historical)
      - coverage
      - risk
      - 1/execution_cost (efficiency)

    Budget constraint: sum(x_i) <= budget  (enforced via penalty)

    Args:
        test_cases: list of dicts with keys: id, change_impact, failure_rate,
                    coverage, risk, execution_cost, redundancy_group
        weights: optional override for factor weights
        budget: max number of tests to select
        penalty_strength: multiplier for constraint penalties

    Returns:
        dict with: qubo_matrix, test_values, num_variables, metadata
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    n = len(test_cases)

    if n == 0:
        return {
            "qubo_matrix": [],
            "test_values": [],
            "num_variables": 0,
            "budget": budget,
            "weights": w,
            "metadata": {"error": "No test cases provided"},
        }

    # Calculate value for each test case
    values = []
    for tc in test_cases:
        cost = max(tc.get("execution_cost", 1.0), 0.1)
        efficiency = 1.0 / cost

        v = (
            w["change_impact"] * tc.get("change_impact", 0.5)
            + w["failure_rate"] * tc.get("failure_rate", 0.0)
            + w["coverage"] * tc.get("coverage", 0.5)
            + w["risk"] * tc.get("risk", 0.5)
            + w["efficiency"] * min(efficiency, 1.0)
        )
        values.append(v)

    # Build QUBO matrix (n x n)
    # Diagonal: -value_i (we negate because QUBO minimizes)
    # Off-diagonal: penalty terms for budget and redundancy
    Q = np.zeros((n, n))

    # Linear terms (diagonal): maximize value → minimize -value
    for i in range(n):
        Q[i, i] = -values[i]

    # Budget constraint: (sum(x_i) - budget)^2 penalty
    # Expanding: sum_i sum_j x_i*x_j - 2*budget*sum_i x_i + budget^2
    # The constant budget^2 doesn't affect optimization
    # Diagonal contribution: penalty * (1 - 2*budget) per x_i
    # Off-diagonal: penalty * 2 * x_i * x_j (for i<j)
    P = penalty_strength * max(max(values) if values else 1.0, 0.1)

    for i in range(n):
        Q[i, i] += P * (1 - 2 * budget)
        for j in range(i + 1, n):
            Q[i, j] += P * 2
            Q[j, i] += P * 2  # symmetric

    # Redundancy penalty: if two tests are in same redundancy group,
    # add penalty for selecting both
    redundancy_penalty = 0.5 * P
    for i in range(n):
        group_i = test_cases[i].get("redundancy_group")
        if not group_i:
            continue
        for j in range(i + 1, n):
            group_j = test_cases[j].get("redundancy_group")
            if group_i == group_j:
                Q[i, j] += redundancy_penalty
                Q[j, i] += redundancy_penalty

    return {
        "qubo_matrix": Q.tolist(),
        "test_values": values,
        "num_variables": n,
        "budget": budget,
        "weights": w,
        "test_ids": [tc["id"] for tc in test_cases],
        "metadata": {
            "penalty_strength": penalty_strength,
            "max_value": float(max(values)) if values else 0,
            "min_value": float(min(values)) if values else 0,
            "avg_value": float(np.mean(values)) if values else 0,
        },
    }
