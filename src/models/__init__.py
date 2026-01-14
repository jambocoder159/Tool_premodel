"""
Binary Options Pricing Models for Polymarket.

This module provides:
- Binary option pricing using Black-Scholes framework
- Greeks calculations (Delta, Gamma, Theta, Vega)
- Risk zone classification
- 3D surface generation for visualization
"""
from .pricing import (
    BinaryOptionPricer,
    PricingResult,
    SECONDS_PER_YEAR,
)
from .greeks import (
    GreeksAnalyzer,
    GreeksSnapshot,
    analyze_historical_greeks,
)

__all__ = [
    # Pricing
    "BinaryOptionPricer",
    "PricingResult",
    "SECONDS_PER_YEAR",
    # Greeks
    "GreeksAnalyzer",
    "GreeksSnapshot",
    "analyze_historical_greeks",
]
