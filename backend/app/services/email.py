"""Email delivery helpers backed by Resend."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.core.telemetry import get_logger

logger = get_logger("app.email")


class EmailServiceError(RuntimeError):
    """Raised when outbound email delivery fails."""

    def __init__(self, detail: str, *, status_code: int = 500) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


async def send_invitation_email(
    *,
    to_email: str,
    workspace_name: str,
    invited_by: str,
    invitation_token: str,
) -> None:
    """Send one workspace invitation email via Resend."""

    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning(
            "resend_api_key_not_configured_skipping_invitation_email",
            to_email=to_email,
        )
        return

    accept_url = f"{settings.frontend_url}/invitations/{invitation_token}/accept"
    payload = {
        "from": "Grounded AI <no-reply@grounded.ai>",
        "to": [to_email],
        "subject": f"You've been invited to {workspace_name}",
        "html": (
            f"<p>Hi,</p>"
            f"<p><strong>{invited_by}</strong> has invited you to join the workspace "
            f"<strong>{workspace_name}</strong> on Grounded AI.</p>"
            f"<p><a href=\"{accept_url}\">Accept your invitation</a></p>"
            "<p>This link expires in 7 days.</p>"
        ),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=10.0,
        )

    if response.status_code not in (200, 201):
        raise EmailServiceError(
            f"Resend returned {response.status_code}: {response.text}",
            status_code=502,
        )


async def send_password_reset_email(*, to_email: str, reset_token: str) -> None:
    """Send one password reset email via Resend."""

    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning(
            "resend_api_key_not_configured_skipping_password_reset_email",
            to_email=to_email,
        )
        return

    reset_url = f"{settings.frontend_url}/auth/reset-password?token={reset_token}"
    payload = {
        "from": "Grounded AI <no-reply@grounded.ai>",
        "to": [to_email],
        "subject": "Reset your Grounded AI password",
        "html": (
            "<p>Hi,</p>"
            "<p>We received a request to reset your password.</p>"
            f"<p><a href=\"{reset_url}\">Reset your password</a></p>"
            "<p>This link expires in 1 hour. If you did not request a reset, ignore this email.</p>"
        ),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=10.0,
        )

    if response.status_code not in (200, 201):
        raise EmailServiceError(
            f"Resend returned {response.status_code}: {response.text}",
            status_code=502,
        )
