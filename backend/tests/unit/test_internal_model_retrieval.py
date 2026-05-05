"""Unit tests for Critical internal model retrieval scaffolding."""

from __future__ import annotations

from app.services.internal_model_retrieval import resolve_internal_model_retrieval_policy


def test_internal_model_retrieval_policy_stays_disabled_without_dataset_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": False})()

    decision = resolve_internal_model_retrieval_policy(namespace=namespace)

    assert decision.allowed is False
    assert decision.reason == "policy_disabled"
    assert decision.attempted is False


def test_internal_model_retrieval_policy_allows_dataset_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": True})()

    decision = resolve_internal_model_retrieval_policy(namespace=namespace)

    assert decision.allowed is True
    assert decision.reason == "policy_enabled"
    assert decision.attempted is False
