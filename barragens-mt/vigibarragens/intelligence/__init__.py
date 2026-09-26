"""Camada de inteligência auditável do VIGIBARRAGENS-MT."""

from .integrated_state import build_intelligence_state, classify_trend

__all__ = ["build_intelligence_state", "classify_trend"]
