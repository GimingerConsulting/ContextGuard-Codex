from pathlib import Path

from contextguard.context_capsule import build_capsule
from contextguard.utils import estimate_tokens


def test_task_capsule_limit(tmp_path: Path):
    for index in range(50):
        (tmp_path / f"payment_{index}.py").write_text("x=1\n")
    capsule = build_capsule(tmp_path, "payment bug", token_limit=80)
    assert estimate_tokens(capsule) <= 80
    assert "ContextGuard capsule" in capsule


def test_high_confidence_capsule_is_short(tmp_path: Path):
    (tmp_path / "billing_service.py").write_text("class BillingService:\n    pass\n")
    capsule = build_capsule(tmp_path, "fix BillingService")
    assert len(capsule.encode()) < 260


def test_high_confidence_capsule_stays_compact_with_many_matches(tmp_path: Path):
    for index in range(25):
        (tmp_path / f"subscription_billing_{index}.py").write_text(
            f"class SubscriptionBilling{index}:\n    pass\n"
        )
    capsule = build_capsule(tmp_path, "fix subscription billing")
    assert len(capsule.encode()) < 300
