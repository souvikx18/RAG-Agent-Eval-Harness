def calculate_correctness_score(
    expected_behavior: str | None,
    actual_output: str | None,
) -> tuple[float, str]:
    if not actual_output:
        return 0.0, "No actual output was produced."

    if not expected_behavior:
        return 1.0, "No expected behavior was provided."

    expected = expected_behavior.lower().strip()
    actual = actual_output.lower().strip()

    if expected in actual:
        return 1.0, "Expected behavior was found in the actual output."

    return 0.0, "Expected behavior was not found in the actual output."


def calculate_latency_score(
    latency_ms: int | None,
) -> tuple[float, str]:
    if latency_ms is None:
        return 0.0, "Latency was not recorded."

    if latency_ms <= 500:
        return 1.0, "Latency is within the target range."

    if latency_ms <= 1000:
        return 0.75, "Latency is acceptable but above the target range."

    if latency_ms <= 2000:
        return 0.5, "Latency is relatively high."

    return 0.0, "Latency exceeds the target range."