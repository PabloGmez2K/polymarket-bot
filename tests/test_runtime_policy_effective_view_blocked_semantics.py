from tools import runtime_policy_effective_view as view


def test_env_blocked_wins_over_auto_canary_without_blocking_collision():
    assert view.effective_policy("blocked", "auto_canary") == ("blocked", "BLOCKED_CITIES")
    assert view.classify_collision(
        env_mode="blocked",
        runtime_mode="auto_canary",
        cross_mode="canary",
        effective_mode="blocked",
        drift_flags=["env_runtime_collision", "cross_effective_divergence"],
    ) == "documented_drift"


def test_active_env_over_auto_canary_is_drift_not_blocker():
    assert view.effective_policy("active", "auto_canary") == ("active", "ACTIVE_TRADING_CITIES")
    assert view.classify_collision(
        env_mode="active",
        runtime_mode="auto_canary",
        cross_mode="canary",
        effective_mode="active",
        drift_flags=["env_runtime_collision", "cross_effective_divergence"],
    ) == "documented_drift"


def test_cross_claiming_tradable_against_shadow_still_blocks():
    assert view.classify_collision(
        env_mode="shadow",
        runtime_mode="runtime_unknown",
        cross_mode="canary",
        effective_mode="shadow",
        drift_flags=["cross_effective_divergence"],
    ) == "blocking_operational_collision"
