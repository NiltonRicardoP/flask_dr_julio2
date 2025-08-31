"""Abstrações para gateways de pagamento."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class PaymentGateway(ABC):
    """Interface para provedores de pagamento."""

    @abstractmethod
    def create_checkout_session(
        self,
        *,
        amount: float,
        currency: str,
        success_url: str,
        cancel_url: str,
        payment_method_types: List[str],
        metadata: Dict[str, Any] | None = None,
    ) -> Any:
        """Cria uma sessão de checkout e retorna o objeto do provedor."""

    @abstractmethod
    def construct_event(self, payload: bytes, signature: str) -> Any:
        """Valida e retorna o evento recebido via webhook."""
