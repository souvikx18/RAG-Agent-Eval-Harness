from app.services.metrics.registry import MetricRegistry


def test_registry_snapshot_contains_versions_and_configurations():
    registry = MetricRegistry()

    snapshot = registry.get_configuration_snapshot()

    assert snapshot == {
        "correctness": {
            "version": 1,
            "configuration": {
                "case_sensitive": False,
            },
        },
        "latency": {
            "version": 1,
            "configuration": {
                "fast_threshold_ms": 500,
                "acceptable_threshold_ms": 1000,
                "high_threshold_ms": 2000,
            },
        },
    }


def test_registry_snapshot_reflects_configuration_changes():
    registry = MetricRegistry()

    registry.configure(
        "correctness",
        {
            "case_sensitive": True,
        },
    )

    registry.configure(
        "latency",
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        },
    )

    snapshot = registry.get_configuration_snapshot()

    assert snapshot["correctness"] == {
        "version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }

    assert snapshot["latency"] == {
        "version": 2,
        "configuration": {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        },
    }


def test_failed_configuration_does_not_change_snapshot():
    registry = MetricRegistry()

    original_snapshot = (
        registry.get_configuration_snapshot()
    )

    try:
        registry.configure(
            "latency",
            {
                "unknown_setting": 123,
            },
        )
    except ValueError:
        pass

    assert (
        registry.get_configuration_snapshot()
        == original_snapshot
    )


def test_snapshot_is_independent_from_metric_state():
    registry = MetricRegistry()

    snapshot = registry.get_configuration_snapshot()

    snapshot["latency"]["version"] = 999
    snapshot["latency"]["configuration"][
        "fast_threshold_ms"
    ] = 9999

    current_snapshot = (
        registry.get_configuration_snapshot()
    )

    assert current_snapshot["latency"]["version"] == 1
    assert (
        current_snapshot["latency"]["configuration"][
            "fast_threshold_ms"
        ]
        == 500
    )


def test_empty_registry_returns_empty_snapshot():
    registry = MetricRegistry(
        register_defaults=False
    )

    assert registry.get_configuration_snapshot() == {}
