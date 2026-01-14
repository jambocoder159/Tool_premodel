"""
3D Surface Visualization for Binary Options.

Generates 3D plots showing how option prices and Greeks vary
with spot price and time to expiry.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from ..models import BinaryOptionPricer, GreeksAnalyzer
from ..config import OUTPUT_DIR


class SurfacePlotter:
    """
    Generate 3D surface plots for binary options analysis.

    Plots available:
    - Price surface: Option price vs (Spot, Time)
    - Delta surface: Delta vs (Spot, Time)
    - Gamma surface: Gamma vs (Spot, Time)
    - Combined dashboard: All surfaces in one figure
    """

    def __init__(
        self,
        strike: float = 95000,
        volatility: float = 0.60,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize plotter.

        Args:
            strike: Strike price for analysis
            volatility: Annualized volatility
            output_dir: Directory for saving plots
        """
        self.strike = strike
        self.volatility = volatility
        self.output_dir = output_dir or OUTPUT_DIR
        self.pricer = BinaryOptionPricer(default_volatility=volatility)
        self.analyzer = GreeksAnalyzer(self.pricer)

        # Default ranges
        self.spot_range = (strike * 0.995, strike * 1.005)  # ±0.5%
        self.time_range = (1, 900)  # 1 second to 15 minutes

    def set_ranges(
        self,
        spot_pct: float = 0.5,
        time_max_seconds: int = 900
    ) -> None:
        """
        Set plot ranges.

        Args:
            spot_pct: Percentage range around strike (e.g., 0.5 = ±0.5%)
            time_max_seconds: Maximum time to expiry in seconds
        """
        self.spot_range = (
            self.strike * (1 - spot_pct / 100),
            self.strike * (1 + spot_pct / 100)
        )
        self.time_range = (1, time_max_seconds)

    def _generate_meshgrid(
        self,
        spot_steps: int = 50,
        time_steps: int = 50
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate meshgrid for 3D plots."""
        spots = np.linspace(self.spot_range[0], self.spot_range[1], spot_steps)
        times = np.linspace(self.time_range[0], self.time_range[1], time_steps)
        return np.meshgrid(spots, times)

    def plot_price_surface(
        self,
        spot_steps: int = 50,
        time_steps: int = 50,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Plot 3D price surface.

        Shows how Up option price varies with spot price and time.

        Args:
            spot_steps: Grid resolution for spot axis
            time_steps: Grid resolution for time axis
            save: Save plot to file
            show: Display plot interactively

        Returns:
            Path to saved file if save=True
        """
        S, T = self._generate_meshgrid(spot_steps, time_steps)
        prices = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                prices[i, j] = self.pricer.binary_call_price(
                    S[i, j], self.strike, T[i, j], self.volatility
                )

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Plot surface
        surf = ax.plot_surface(
            S, T, prices,
            cmap=cm.RdYlGn,
            linewidth=0,
            antialiased=True,
            alpha=0.8
        )

        # Add strike line
        strike_line_spots = np.array([self.strike] * time_steps)
        strike_line_times = np.linspace(self.time_range[0], self.time_range[1], time_steps)
        strike_line_prices = np.array([
            self.pricer.binary_call_price(self.strike, self.strike, t, self.volatility)
            for t in strike_line_times
        ])
        ax.plot(strike_line_spots, strike_line_times, strike_line_prices,
                'k--', linewidth=2, label='ATM')

        ax.set_xlabel('BTC Spot Price ($)', fontsize=10)
        ax.set_ylabel('Time to Expiry (seconds)', fontsize=10)
        ax.set_zlabel('Up Option Price', fontsize=10)
        ax.set_title(
            f'Binary Option Price Surface\n'
            f'Strike: ${self.strike:,.0f}, Volatility: {self.volatility:.0%}',
            fontsize=12
        )

        fig.colorbar(surf, shrink=0.5, aspect=10, label='Price')

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'price_surface_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None

    def plot_delta_surface(
        self,
        spot_steps: int = 50,
        time_steps: int = 50,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Plot 3D Delta surface.

        Shows how Delta varies with spot price and time.
        Delta peaks near strike and near expiry.
        """
        S, T = self._generate_meshgrid(spot_steps, time_steps)
        deltas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                greeks = self.pricer.calculate_greeks(
                    S[i, j], self.strike, T[i, j], self.volatility
                )
                deltas[i, j] = greeks['delta']

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(
            S, T, deltas,
            cmap=cm.viridis,
            linewidth=0,
            antialiased=True,
            alpha=0.8
        )

        ax.set_xlabel('BTC Spot Price ($)', fontsize=10)
        ax.set_ylabel('Time to Expiry (seconds)', fontsize=10)
        ax.set_zlabel('Delta', fontsize=10)
        ax.set_title(
            f'Delta Surface\n'
            f'Strike: ${self.strike:,.0f}, Volatility: {self.volatility:.0%}',
            fontsize=12
        )

        fig.colorbar(surf, shrink=0.5, aspect=10, label='Delta')

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'delta_surface_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None

    def plot_gamma_surface(
        self,
        spot_steps: int = 50,
        time_steps: int = 50,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Plot 3D Gamma surface.

        Shows gamma risk concentration near strike and expiry.
        This is the "gamma risk zone" from the research.
        """
        S, T = self._generate_meshgrid(spot_steps, time_steps)
        gammas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                greeks = self.pricer.calculate_greeks(
                    S[i, j], self.strike, T[i, j], self.volatility
                )
                # Use absolute value for visualization
                gammas[i, j] = abs(greeks['gamma'])

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(
            S, T, gammas,
            cmap=cm.hot,
            linewidth=0,
            antialiased=True,
            alpha=0.8
        )

        ax.set_xlabel('BTC Spot Price ($)', fontsize=10)
        ax.set_ylabel('Time to Expiry (seconds)', fontsize=10)
        ax.set_zlabel('|Gamma|', fontsize=10)
        ax.set_title(
            f'Gamma Risk Surface\n'
            f'Strike: ${self.strike:,.0f} - Peak = DANGER ZONE',
            fontsize=12
        )

        fig.colorbar(surf, shrink=0.5, aspect=10, label='|Gamma|')

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'gamma_surface_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None

    def plot_theta_surface(
        self,
        spot_steps: int = 50,
        time_steps: int = 50,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Plot 3D Theta surface.

        Shows time decay rate across spot and time.
        """
        S, T = self._generate_meshgrid(spot_steps, time_steps)
        thetas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                greeks = self.pricer.calculate_greeks(
                    S[i, j], self.strike, T[i, j], self.volatility
                )
                # Convert to per-minute for readability
                thetas[i, j] = greeks['theta'] * 60

        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(
            S, T, thetas,
            cmap=cm.coolwarm,
            linewidth=0,
            antialiased=True,
            alpha=0.8
        )

        ax.set_xlabel('BTC Spot Price ($)', fontsize=10)
        ax.set_ylabel('Time to Expiry (seconds)', fontsize=10)
        ax.set_zlabel('Theta (per minute)', fontsize=10)
        ax.set_title(
            f'Theta Decay Surface\n'
            f'Strike: ${self.strike:,.0f}',
            fontsize=12
        )

        fig.colorbar(surf, shrink=0.5, aspect=10, label='Theta/min')

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'theta_surface_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None

    def plot_dashboard(
        self,
        spot_steps: int = 40,
        time_steps: int = 40,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Generate complete dashboard with all surfaces.

        Creates a 2x2 grid with Price, Delta, Gamma, and Theta.
        """
        S, T = self._generate_meshgrid(spot_steps, time_steps)

        # Calculate all values
        prices = np.zeros_like(S)
        deltas = np.zeros_like(S)
        gammas = np.zeros_like(S)
        thetas = np.zeros_like(S)

        for i in range(time_steps):
            for j in range(spot_steps):
                prices[i, j] = self.pricer.binary_call_price(
                    S[i, j], self.strike, T[i, j], self.volatility
                )
                greeks = self.pricer.calculate_greeks(
                    S[i, j], self.strike, T[i, j], self.volatility
                )
                deltas[i, j] = greeks['delta']
                gammas[i, j] = abs(greeks['gamma'])
                thetas[i, j] = greeks['theta'] * 60

        fig = plt.figure(figsize=(16, 12))

        # Price surface
        ax1 = fig.add_subplot(221, projection='3d')
        ax1.plot_surface(S, T, prices, cmap=cm.RdYlGn, alpha=0.8)
        ax1.set_xlabel('Spot ($)')
        ax1.set_ylabel('Time (s)')
        ax1.set_zlabel('Price')
        ax1.set_title('Up Option Price')

        # Delta surface
        ax2 = fig.add_subplot(222, projection='3d')
        ax2.plot_surface(S, T, deltas, cmap=cm.viridis, alpha=0.8)
        ax2.set_xlabel('Spot ($)')
        ax2.set_ylabel('Time (s)')
        ax2.set_zlabel('Delta')
        ax2.set_title('Delta')

        # Gamma surface
        ax3 = fig.add_subplot(223, projection='3d')
        ax3.plot_surface(S, T, gammas, cmap=cm.hot, alpha=0.8)
        ax3.set_xlabel('Spot ($)')
        ax3.set_ylabel('Time (s)')
        ax3.set_zlabel('|Gamma|')
        ax3.set_title('Gamma Risk (Peak = Danger)')

        # Theta surface
        ax4 = fig.add_subplot(224, projection='3d')
        ax4.plot_surface(S, T, thetas, cmap=cm.coolwarm, alpha=0.8)
        ax4.set_xlabel('Spot ($)')
        ax4.set_ylabel('Time (s)')
        ax4.set_zlabel('Theta/min')
        ax4.set_title('Theta Decay')

        fig.suptitle(
            f'Binary Option Greeks Dashboard\n'
            f'Strike: ${self.strike:,.0f}, Volatility: {self.volatility:.0%}',
            fontsize=14
        )

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'dashboard_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None

    def plot_zone_heatmap(
        self,
        spot_steps: int = 100,
        time_steps: int = 100,
        save: bool = True,
        show: bool = False
    ) -> Optional[str]:
        """
        Generate 2D heatmap showing market zones.

        Colors:
        - Green: Linear decay zone (safe)
        - Yellow: Lock-in zone (low risk)
        - Red: Gamma risk zone (danger)
        """
        spots = np.linspace(self.spot_range[0], self.spot_range[1], spot_steps)
        times = np.linspace(self.time_range[0], self.time_range[1], time_steps)

        zones = np.zeros((time_steps, spot_steps))

        for i, t in enumerate(times):
            for j, s in enumerate(spots):
                zone, _ = self.pricer.classify_zone(t, s, self.strike)
                if zone == "linear_decay":
                    zones[i, j] = 0
                elif zone == "lock_in":
                    zones[i, j] = 1
                elif zone == "gamma_risk":
                    zones[i, j] = 2
                else:  # transition
                    zones[i, j] = 1.5

        fig, ax = plt.subplots(figsize=(12, 8))

        # Custom colormap
        from matplotlib.colors import ListedColormap
        colors = ['#2ecc71', '#f1c40f', '#e74c3c', '#e67e22']  # green, yellow, red, orange
        cmap = ListedColormap(colors)

        im = ax.imshow(
            zones,
            extent=[
                self.spot_range[0], self.spot_range[1],
                self.time_range[0], self.time_range[1]
            ],
            origin='lower',
            aspect='auto',
            cmap=cmap,
            vmin=0,
            vmax=2
        )

        # Add strike line
        ax.axvline(x=self.strike, color='white', linestyle='--', linewidth=2, label='Strike')

        ax.set_xlabel('BTC Spot Price ($)', fontsize=12)
        ax.set_ylabel('Time to Expiry (seconds)', fontsize=12)
        ax.set_title(
            f'Market Zone Classification\n'
            f'Strike: ${self.strike:,.0f}',
            fontsize=14
        )

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#2ecc71', label='Linear Decay (Safe)'),
            Patch(facecolor='#f1c40f', label='Lock-in (Low Risk)'),
            Patch(facecolor='#e74c3c', label='Gamma Risk (DANGER)'),
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()

        filepath = None
        if save:
            filepath = self.output_dir / f'zone_heatmap_{datetime.now():%Y%m%d_%H%M%S}.png'
            plt.savefig(filepath, dpi=150, bbox_inches='tight')

        if show:
            plt.show()
        else:
            plt.close()

        return str(filepath) if filepath else None


def generate_all_plots(
    strike: float = 95000,
    volatility: float = 0.60,
    spot_pct: float = 0.5,
    show: bool = False
) -> dict:
    """
    Generate all visualization plots.

    Args:
        strike: Strike price
        volatility: Annualized volatility
        spot_pct: Spot range as percentage around strike
        show: Display plots interactively

    Returns:
        Dict with paths to generated files
    """
    plotter = SurfacePlotter(strike=strike, volatility=volatility)
    plotter.set_ranges(spot_pct=spot_pct)

    results = {}

    print("Generating Price Surface...")
    results['price'] = plotter.plot_price_surface(save=True, show=show)

    print("Generating Delta Surface...")
    results['delta'] = plotter.plot_delta_surface(save=True, show=show)

    print("Generating Gamma Surface...")
    results['gamma'] = plotter.plot_gamma_surface(save=True, show=show)

    print("Generating Theta Surface...")
    results['theta'] = plotter.plot_theta_surface(save=True, show=show)

    print("Generating Dashboard...")
    results['dashboard'] = plotter.plot_dashboard(save=True, show=show)

    print("Generating Zone Heatmap...")
    results['zones'] = plotter.plot_zone_heatmap(save=True, show=show)

    return results
