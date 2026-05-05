"""Unit tests for agent model defaults."""

from __future__ import annotations

from types import SimpleNamespace

from app.models.agent import _default_allowed_modes


def test_default_allowed_modes_include_thinking_when_enterprise_enabled(monkeypatch) -> None:
    """Agent defaults should include Thinking while Enterprise is enabled."""

    monkeypatch.setattr(
        "app.models.agent.get_settings",
        lambda: SimpleNamespace(enterprise_enabled=True),
    )

    assert _default_allowed_modes() == ["auto", "instant", "thinking"]


def test_default_allowed_modes_exclude_thinking_when_enterprise_disabled(monkeypatch) -> None:
    """Agent defaults should stay Standard-only when Enterprise is disabled."""

    monkeypatch.setattr(
        "app.models.agent.get_settings",
        lambda: SimpleNamespace(enterprise_enabled=False),
    )

    assert _default_allowed_modes() == ["auto", "instant"]
