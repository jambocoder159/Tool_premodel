"""
Greeks Analysis for Binary Options.

Provides detailed sensitivity analysis and visualization helpers
for Polymarket 15-minute BTC binary options.
"""
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
from scipy.stats import norm

from .pricing import SECONDS_PER_YEAR, BinaryOptionPricer


@dataclass
class GreeksSnapshot:
    """Complete Greeks snapshot at a point in time."""
    spot: float
    strike: float
    ttl_seconds: float
    volatility: float

    # Prices
    up_price: float
    down_price: float

    # First-order Greeks
    delta_up: float      # dUp/dS
    delta_down: float    # dDown/dS (= -delta_up)

    # Second-order Greeks
    gamma_up: float      # d²Up/dS²
    gamma_down: float    # d²Down/dS² (= -gamma_up)

    # Time decay
    theta_up: float      # dUp/dt (per second)
    theta_down: float    # dDown/dt (per second)

    # Volatility sensitivity
    vega_up: float       # dUp/dσ
    vega_down: float     # dDown/dσ (= -vega_up)

    # Higher-order Greeks (optional)
    vanna: Optional[float] = None   # d²Price/dS dσ
    charm: Optional[float] = None   # d²Price/dS dt


class GreeksAnalyzer:
    """
    Advanced Greeks analysis for binary options.

    Provides:
    - Complete Greeks calculation for both Up and Down
    - Greeks surface generation for 3D visualization
    - Risk zone analysis
    - Delta hedging calculations
    """

    def __init__(self, pricer: Optional[BinaryOptionPricer] = None):
        """
        Initialize analyzer.

        Args:
            pricer: BinaryOptionPricer instance (creates default if None)
        """
        self.pricer = pricer or BinaryOptionPricer()

    def full_greeks(
        self,
        spot: float,
        strike: float,
        ttl_seconds: float,
        sigma: Optional[float] = None
    ) -> GreeksSnapshot:
        """
        Calculate complete Greeks for both Up and Down options.

        Args:
            spot: Current BTC price
            strike: Strike price
            ttl_seconds: Time to expiry in seconds
            sigma: Volatility (uses pricer default if None)

        Returns:
            GreeksSnapshot with all calculations
        """
        if sigma is None:
            sigma = self.pricer.default_volatility

        # Get prices
        up_price = self.pricer.binary_call_price(spot, strike, ttl_seconds, sigma)
        down_price = self.pricer.binary_put_price(spot, strike, ttl_seconds, sigma)

        # Get Greeks for Up (call)
        greeks_up = self.pricer.calculate_greeks(spot, strike, ttl_seconds, sigma)

        # Down Greeks are negative of Up Greeks (for delta, gamma, vega)
        # Theta for down is also related but needs separate calculation
        return GreeksSnapshot(
            spot=spot,
            strike=strike,
            ttl_seconds=ttl_seconds,
            volatility=sigma,
            up_price=up_price,
            down_price=down_price,
            delta_up=greeks_up['delta'],
            delta_down=-greeks_up['delta'],
            gamma_up=greeks_up['gamma'],
            gamma_down=-greeks_up['gamma'],
            theta_up=greeks_up['theta'],
            theta_down=-greeks_up['theta'],
            vega_up=greeks_up['vega'],
            vega_down=-greeks_up['vega']
        )

    def delta_surface(
        self,
        strike: float,
        spot_range: Tuple[float, float],
        time_range: Tuple[float, float],
        spot_steps: int = 50,
        time_steps: int = 50,
        sigma: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate Delta surface for 3D visualization.

        Args:
            strike: Strike price
            spot_range: (min_spot, max_spot) tuple
            time_range: (min_seconds, max_seconds) tuple
            spot_steps: Number of spot price steps
            time_steps: Number of time steps
            sigma: Volatility

        Returns:
            Tuple of (spots, times, deltas) numpy arrays for plotting
        """
        if sigma is None:
            sigma = self.pricer.default_volatility

        spots = np.linspace(spot_range[0], spot_range[1], spot_steps)
        times = np.linspace(time_range[0], time_range[1], time_steps)

        # Create meshgrid
        S, T = np.meshgrid(spots, times)
        deltas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                greeks = self.pricer.calculate_greeks(
                    S[i, j], strike, T[i, j], sigma
                )
                deltas[i, j] = greeks['delta']

        return spots, times, deltas

    def gamma_surface(
        self,
        strike: float,
        spot_range: Tuple[float, float],
        time_range: Tuple[float, float],
        spot_steps: int = 50,
        time_steps: int = 50,
        sigma: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate Gamma surface for 3D visualization.

        Gamma is highest near strike and near expiry - the "gamma risk" zone.

        Returns:
            Tuple of (spots, times, gammas) numpy arrays
        """
        if sigma is None:
            sigma = self.pricer.default_volatility

        spots = np.linspace(spot_range[0], spot_range[1], spot_steps)
        times = np.linspace(time_range[0], time_range[1], time_steps)

        S, T = np.meshgrid(spots, times)
        gammas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                greeks = self.pricer.calculate_greeks(
                    S[i, j], strike, T[i, j], sigma
                )
                gammas[i, j] = greeks['gamma']

        return spots, times, gammas

    def price_surface(
        self,
        strike: float,
        spot_range: Tuple[float, float],
        time_range: Tuple[float, float],
        spot_steps: int = 50,
        time_steps: int = 50,
        sigma: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate price surface for 3D visualization.

        Shows how Up option price varies with spot and time.

        Returns:
            Tuple of (spots, times, prices) numpy arrays
        """
        if sigma is None:
            sigma = self.pricer.default_volatility

        spots = np.linspace(spot_range[0], spot_range[1], spot_steps)
        times = np.linspace(time_range[0], time_range[1], time_steps)

        S, T = np.meshgrid(spots, times)
        prices = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                prices[i, j] = self.pricer.binary_call_price(
                    S[i, j], strike, T[i, j], sigma
                )

        return spots, times, prices

    def risk_profile(
        self,
        spot: float,
        strike: float,
        ttl_seconds: float,
        sigma: Optional[float] = None
    ) -> dict:
        """
        Generate risk profile summary.

        Args:
            spot: Current spot price
            strike: Strike price
            ttl_seconds: Time to expiry
            sigma: Volatility

        Returns:
            Dict with risk metrics and recommendations
        """
        greeks = self.full_greeks(spot, strike, ttl_seconds, sigma)
        zone, zone_desc = self.pricer.classify_zone(ttl_seconds, spot, strike)

        # Calculate risk metrics
        distance_pct = (spot - strike) / strike * 100
        moneyness = "ITM" if spot >= strike else "OTM"

        # Dollar delta (price change per $1 move in BTC)
        dollar_delta = greeks.delta_up

        # Expected theta decay in next minute
        theta_1min = greeks.theta_up * 60

        # Gamma risk score (0-100)
        # Higher when near strike AND near expiry
        time_factor = max(0, 1 - ttl_seconds / 900)  # 0 at 15min, 1 at 0
        strike_factor = max(0, 1 - abs(distance_pct) / 1)  # 0 at 1%, 1 at 0%
        gamma_risk_score = time_factor * strike_factor * 100

        return {
            'zone': zone,
            'zone_description': zone_desc,
            'moneyness': moneyness,
            'distance_to_strike_pct': distance_pct,
            'up_price': greeks.up_price,
            'down_price': greeks.down_price,
            'delta': greeks.delta_up,
            'dollar_delta': dollar_delta,
            'gamma': greeks.gamma_up,
            'theta_per_second': greeks.theta_up,
            'theta_per_minute': theta_1min,
            'vega': greeks.vega_up,
            'gamma_risk_score': gamma_risk_score,
            'recommendation': self._get_recommendation(
                zone, distance_pct, ttl_seconds, gamma_risk_score
            )
        }

    def _get_recommendation(
        self,
        zone: str,
        distance_pct: float,
        ttl_seconds: float,
        gamma_risk_score: float
    ) -> str:
        """Generate trading recommendation based on risk profile."""
        if gamma_risk_score > 70:
            return "HIGH RISK: Extreme gamma exposure. Avoid new positions."
        elif zone == "lock_in":
            direction = "Up" if distance_pct > 0 else "Down"
            return f"LOCK-IN: {direction} likely to win. Low risk of reversal."
        elif zone == "linear_decay":
            return "NORMAL: Standard theta decay. Greeks behave predictably."
        else:
            return "TRANSITION: Monitor closely for zone changes."

    def delta_hedge_ratio(
        self,
        position_size: float,
        spot: float,
        strike: float,
        ttl_seconds: float,
        sigma: Optional[float] = None
    ) -> dict:
        """
        Calculate delta hedging requirements.

        Args:
            position_size: Number of Up contracts held (negative if short)
            spot: Current spot price
            strike: Strike price
            ttl_seconds: Time to expiry
            sigma: Volatility

        Returns:
            Dict with hedging calculations
        """
        greeks = self.full_greeks(spot, strike, ttl_seconds, sigma)

        # Position delta
        position_delta = position_size * greeks.delta_up

        # BTC needed to hedge (negative means short BTC)
        btc_to_hedge = -position_delta

        # Dollar value of hedge
        hedge_value = btc_to_hedge * spot

        return {
            'position_size': position_size,
            'unit_delta': greeks.delta_up,
            'position_delta': position_delta,
            'btc_to_hedge': btc_to_hedge,
            'hedge_value_usd': hedge_value,
            'gamma_exposure': position_size * greeks.gamma_up,
            'rebalance_needed_per_dollar': abs(position_size * greeks.gamma_up)
        }


def analyze_historical_greeks(
    data: List[dict],
    strike: float,
    sigma: float = 0.60
) -> List[dict]:
    """
    Analyze Greeks for historical data points.

    Args:
        data: List of dicts with 'btc_price' and 'time_to_expiry_seconds'
        strike: Strike price
        sigma: Volatility

    Returns:
        List of dicts with original data plus Greeks
    """
    analyzer = GreeksAnalyzer()
    results = []

    for point in data:
        spot = point.get('btc_price', 0)
        ttl = point.get('time_to_expiry_seconds', 0)

        if spot > 0 and ttl is not None:
            greeks = analyzer.full_greeks(spot, strike, ttl, sigma)
            results.append({
                **point,
                'up_price': greeks.up_price,
                'down_price': greeks.down_price,
                'delta': greeks.delta_up,
                'gamma': greeks.gamma_up,
                'theta': greeks.theta_up,
                'vega': greeks.vega_up
            })

    return results
