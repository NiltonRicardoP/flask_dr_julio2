"""Integração com o gateway Stripe."""
from __future__ import annotations

from typing import Any, Dict, List

import stripe
from flask import current_app

from .gateway import PaymentGateway


class StripeGateway(PaymentGateway):
    """Implementação de ``PaymentGateway`` usando Stripe."""

    def __init__(self) -> None:
        api_key = current_app.config.get("STRIPE_SECRET_KEY")
        stripe.api_key = api_key

    def create_checkout_session(
        self,
        *,
        amount: float,
        currency: str,
        success_url: str,
        cancel_url: str,
        payment_method_types: List[str],
        metadata: Dict[str, Any] | None = None,
    ) -> stripe.checkout.Session:
        price_data = {
            "currency": currency,
            "product_data": {"name": metadata.get("course_title") if metadata else "Curso"},
            "unit_amount": int(amount * 100),
        }
        return stripe.checkout.Session.create(
            payment_method_types=payment_method_types,
            line_items=[{"price_data": price_data, "quantity": 1}],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )

    def construct_event(self, payload: bytes, signature: str) -> Any:
        secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
        return stripe.Webhook.construct_event(payload, signature, secret)

    def retrieve_session(self, session_id: str) -> stripe.checkout.Session:
        return stripe.checkout.Session.retrieve(session_id)
