"""
Binary Options Pricing Model for Polymarket 15-minute markets.

Uses adapted Black-Scholes model for digital/binary options pricing.
"""
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from scipy.stats import norm


# Constants
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60  # 31,557,600


@dataclass
class PricingResult:
    """Result of binary option pricing calculation."""
    timestamp: datetime
    spot_price: float
    strike_price: float
    time_to_expiry_seconds: float
    volatility: float

    # Theoretical prices (0 to 1)
    up_price: float
    down_price: float

    # Greeks
    delta: float
    gamma: float
    theta: float  # Per second
    vega: float

    # Market zone classification
    zone: str
    zone_description: str


class BinaryOptionPricer:
    """
    Binary options pricing using Black-Scholes framework.

    For Polymarket 15-minute BTC Up/Down markets:
    - "Up" = Binary Call (pays if S >= K at expiry)
    - "Down" = Binary Put (pays if S < K at expiry)

    Formulas:
        d1 = (ln(S/K) + (r + 0.5*sigma^2)*T) / (sigma*sqrt(T))
        d2 = d1 - sigma*sqrt(T)

        Binary Call Price = e^(-rT) * N(d2)
        Binary Put Price = e^(-rT) * N(-d2)

    For short-term (15 min), we use r=0 so:
        Binary Call = N(d2)
        Binary Put = N(-d2) = 1 - N(d2)
    """

    def __init__(self, default_volatility: float = 0.60):
        """
        Initialize pricer.

        Args:
            default_volatility: Annualized volatility (default 60% for crypto)
        """
        self.default_volatility = default_volatility

    def _calculate_d1_d2(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        r: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculate d1 and d2 for Black-Scholes.

        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry in years
            sigma: Annualized volatility
            r: Risk-free rate (default 0)

        Returns:
            Tuple of (d1, d2)
        """
        if T <= 0:
            # At or past expiry
            if S >= K:
                return (float('inf'), float('inf'))
            else:
                return (float('-inf'), float('-inf'))

        if sigma <= 0:
            sigma = 0.0001  # Avoid division by zero

        sqrt_T = math.sqrt(T)

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        return d1, d2

    def binary_call_price(
        self,
        S: float,
        K: float,
        T_seconds: float,
        sigma: Optional[float] = None,
        r: float = 0.0
    ) -> float:
        """
        Calculate binary call (Up) option price.

        Args:
            S: Current spot price (BTC)
            K: Strike price
            T_seconds: Time to expiry in seconds
            sigma: Annualized volatility (uses default if None)
            r: Risk-free rate

        Returns:
            Price between 0 and 1
        """
        if sigma is None:
            sigma = self.default_volatility

        T = T_seconds / SECONDS_PER_YEAR

        if T <= 0:
            # At expiry: pay 1 if S >= K, else 0
            return 1.0 if S >= K else 0.0

        _, d2 = self._calculate_d1_d2(S, K, T, sigma, r)

        # Binary call = N(d2) for r=0
        price = norm.cdf(d2)

        return max(0.0, min(1.0, price))

    def binary_put_price(
        self,
        S: float,
        K: float,
        T_seconds: float,
        sigma: Optional[float] = None,
        r: float = 0.0
    ) -> float:
        """
        Calculate binary put (Down) option price.

        Args:
            S: Current spot price (BTC)
            K: Strike price
            T_seconds: Time to expiry in seconds
            sigma: Annualized volatility (uses default if None)
            r: Risk-free rate

        Returns:
            Price between 0 and 1
        """
        # Binary put = 1 - Binary call
        return 1.0 - self.binary_call_price(S, K, T_seconds, sigma, r)

    def calculate_greeks(
        self,
        S: float,
        K: float,
        T_seconds: float,
        sigma: Optional[float] = None,
        r: float = 0.0
    ) -> dict:
        """
        Calculate Greeks for binary call option.

        Args:
            S: Spot price
            K: Strike price
            T_seconds: Time to expiry in seconds
            sigma: Annualized volatility
            r: Risk-free rate

        Returns:
            Dict with delta, gamma, theta, vega
        """
        if sigma is None:
            sigma = self.default_volatility

        T = T_seconds / SECONDS_PER_YEAR

        if T <= 0:
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0
            }

        d1, d2 = self._calculate_d1_d2(S, K, T, sigma, r)
        sqrt_T = math.sqrt(T)

        # n(d2) = standard normal PDF at d2
        n_d2 = norm.pdf(d2)

        # Delta: dPrice/dS
        # For binary call: delta = n(d2) / (S * sigma * sqrt(T))
        delta = n_d2 / (S * sigma * sqrt_T)

        # Gamma: dDelta/dS
        # For binary call: gamma = -n(d2) * d1 / (S^2 * sigma^2 * T)
        gamma = -n_d2 * d1 / (S ** 2 * sigma ** 2 * T)

        # Theta: dPrice/dT (per year, then convert to per second)
        # For binary call: theta_annual = n(d2) * (d1/(2*T) + r) / (sigma * sqrt(T))
        # For r=0: theta_annual = n(d2) * d1 / (2 * T * sigma * sqrt(T))
        theta_annual = n_d2 * d1 / (2 * T * sigma * sqrt_T)
        theta_per_second = -theta_annual / SECONDS_PER_YEAR  # Negative because price decays

        # Vega: dPrice/dSigma
        # For binary call: vega = -n(d2) * d1 * sqrt(T) / sigma
        vega = -n_d2 * d1 * sqrt_T / sigma

        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta_per_second,
            'vega': vega
        }

    def classify_zone(
        self,
        T_seconds: float,
        S: float,
        K: float
    ) -> Tuple[str, str]:
        """
        Classify current market state into zones.

        Zones based on project research:
        1. linear_decay: >3 min remaining, normal theta decay
        2. lock_in: Near expiry but far from strike, minimal movement
        3. gamma_risk: Near expiry AND near strike, extreme sensitivity

        Args:
            T_seconds: Time to expiry in seconds
            S: Spot price
            K: Strike price

        Returns:
            Tuple of (zone_name, description)
        """
        # Distance to strike as percentage
        distance_pct = abs(S - K) / K * 100

        if T_seconds > 180:  # > 3 minutes
            return (
                "linear_decay",
                f"Normal theta decay zone. {T_seconds:.0f}s remaining, {distance_pct:.2f}% from strike."
            )
        elif T_seconds > 60 and distance_pct > 0.5:  # 1-3 min, far from strike
            return (
                "lock_in",
                f"Lock-in zone. Price far from strike ({distance_pct:.2f}%), minimal movement expected."
            )
        elif T_seconds <= 60 and distance_pct <= 0.5:  # <1 min, near strike
            return (
                "gamma_risk",
                f"GAMMA RISK! {T_seconds:.0f}s remaining, only {distance_pct:.2f}% from strike. Extreme sensitivity."
            )
        else:
            return (
                "transition",
                f"Transition zone. {T_seconds:.0f}s remaining, {distance_pct:.2f}% from strike."
            )

    def price(
        self,
        spot: float,
        strike: float,
        ttl_seconds: float,
        sigma: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> PricingResult:
        """
        Full pricing calculation with Greeks and zone classification.

        Args:
            spot: Current BTC spot price
            strike: Strike price
            ttl_seconds: Time to expiry in seconds
            sigma: Annualized volatility (uses default if None)
            timestamp: Timestamp for result (uses now if None)

        Returns:
            PricingResult with all calculations
        """
        if sigma is None:
            sigma = self.default_volatility

        if timestamp is None:
            timestamp = datetime.now()

        # Calculate prices
        up_price = self.binary_call_price(spot, strike, ttl_seconds, sigma)
        down_price = self.binary_put_price(spot, strike, ttl_seconds, sigma)

        # Calculate Greeks
        greeks = self.calculate_greeks(spot, strike, ttl_seconds, sigma)

        # Classify zone
        zone, zone_desc = self.classify_zone(ttl_seconds, spot, strike)

        return PricingResult(
            timestamp=timestamp,
            spot_price=spot,
            strike_price=strike,
            time_to_expiry_seconds=ttl_seconds,
            volatility=sigma,
            up_price=up_price,
            down_price=down_price,
            delta=greeks['delta'],
            gamma=greeks['gamma'],
            theta=greeks['theta'],
            vega=greeks['vega'],
            zone=zone,
            zone_description=zone_desc
        )

    def implied_volatility(
        self,
        market_price: float,
        S: float,
        K: float,
        T_seconds: float,
        is_call: bool = True,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Optional[float]:
        """
        Calculate implied volatility from market price using Newton-Raphson.

        Args:
            market_price: Observed market price (0 to 1)
            S: Spot price
            K: Strike price
            T_seconds: Time to expiry in seconds
            is_call: True for Up/Call, False for Down/Put
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence tolerance

        Returns:
            Implied volatility (annualized) or None if not converged
        """
        if T_seconds <= 0:
            return None

        # Initial guess
        sigma = 0.5  # 50% volatility starting point

        for _ in range(max_iterations):
            # Calculate price with current sigma
            if is_call:
                price = self.binary_call_price(S, K, T_seconds, sigma)
            else:
                price = self.binary_put_price(S, K, T_seconds, sigma)

            # Calculate vega
            greeks = self.calculate_greeks(S, K, T_seconds, sigma)
            vega = greeks['vega']

            # Price difference
            diff = price - market_price

            if abs(diff) < tolerance:
                return sigma

            if abs(vega) < 1e-10:
                # Vega too small, try different approach
                break

            # Newton-Raphson update
            sigma = sigma - diff / vega

            # Keep sigma in reasonable bounds
            sigma = max(0.01, min(5.0, sigma))

        return None  # Did not converge
