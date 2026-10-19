"""Budget range keys (contract) → rupee bounds. `None` max = open-ended."""
BUDGETS: dict[str, tuple[int, int | None]] = {
    "5k_10k": (5000, 10000),
    "10k_15k": (10000, 15000),
    "15k_25k": (15000, 25000),
    "25k_50k": (25000, 50000),
    "50k_plus": (50000, None),
}


def budget_key_for(min_rupees: int) -> str:
    """Closest range for a known lower bound (used when importing data that only has min/max)."""
    for key, (lo, _) in BUDGETS.items():
        if lo == min_rupees:
            return key
    return min(BUDGETS, key=lambda k: abs(BUDGETS[k][0] - min_rupees))
