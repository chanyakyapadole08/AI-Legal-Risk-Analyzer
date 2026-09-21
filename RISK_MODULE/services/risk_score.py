def verdict(score: int) -> str:
    """
    Convert numeric score into professional risk label.

    Thresholds:
    0-39   LOW RISK
    40-69  MEDIUM RISK
    70-84  HIGH RISK
    85-100 CRITICAL RISK
    """

    try:
        score = int(score)
    except Exception:
        score = 0

    score = max(
        0,
        min(
            score,
            100
        )
    )

    if score >= 85:
        return "CRITICAL RISK"

    if score >= 70:
        return "HIGH RISK"

    if score >= 40:
        return "MEDIUM RISK"

    return "LOW RISK"