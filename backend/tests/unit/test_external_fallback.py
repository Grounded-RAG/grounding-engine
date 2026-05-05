"""Unit tests for Critical external fallback policy scaffolding."""

from __future__ import annotations

from app.services.external_fallback import resolve_external_fallback_policy


def test_external_fallback_policy_stays_disabled_without_dataset_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_web_fallback": False})()

    decision = resolve_external_fallback_policy(namespace=namespace)

    assert decision.allowed is False
    assert decision.reason == "policy_disabled"
    assert decision.attempted is False


def test_external_fallback_policy_allows_allowlisted_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_web_fallback": True})()

    decision = resolve_external_fallback_policy(namespace=namespace)

    assert decision.allowed is True
    assert decision.reason == "allowlisted_policy_enabled"
    assert decision.attempted is False
