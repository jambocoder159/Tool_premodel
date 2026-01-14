"""
Visualization module for Binary Options analysis.

Provides 3D surface plots and heatmaps for:
- Option price surfaces
- Greeks surfaces (Delta, Gamma, Theta)
- Market zone classification
"""
from .surfaces import (
    SurfacePlotter,
    generate_all_plots,
)

__all__ = [
    "SurfacePlotter",
    "generate_all_plots",
]
