# Tool_premodel

## Polymarket 15-Minute Binary Option Pricing Model

Reverse engineering market maker behavior in Polymarket's ultra-short-term cryptocurrency prediction markets.

## Project Summary

This project analyzes 15-minute binary option markets on Polymarket (e.g., "Will Bitcoin be above $95,000 in 15 minutes?"). Through automated data pipelines and financial mathematics, we reverse-engineer market maker pricing logic.

## Core Research Questions

How do these three variables non-linearly determine Yes/No prices?

1. **Time to Expiry (Theta)**: Time decay effects on price
2. **Distance to Strike (Delta/Gamma)**: Price sensitivity to underlying movement
3. **Volatility (Vega)**: Pricing premium during market panic or calm

## Key Scenarios

- **Linear Decay Zone**: ~3 min remaining, small price dip -> minor correction (-3¢)
- **Lock-in Effect Zone**: ~1 min remaining, price far from strike -> minimal movement (-1¢)
- **Extreme Reversal Zone (Gamma Risk)**: Near expiry, price crosses strike -> collapse (-60¢)

## Technical Roadmap

### Data Engineering (Python)
- Exchange API integration (Binance/Bybit) for high-frequency spot prices
- Polymarket API for order book and trade data
- Time-series alignment at second-level precision

### Mathematical Modeling
- Binary options pricing model
- Implied volatility calculation
- Greeks sensitivity analysis (Delta, Gamma, Theta, Vega)

### Visualization
- 3D pricing surface: Time × Price × Contract Value

## Expected Deliverables

1. Automated Python data cleaning pipeline
2. Pricing model: Input (current price, time remaining) -> Output (theoretical Yes price)
3. Analysis report on market maker efficiency and arbitrage opportunities

## Quick Start

```bash
# Read CLAUDE.md first for development rules
# All source code goes in src/
python src/main.py
```

## Project Structure

```
Tool_premodel/
├── CLAUDE.md          # Development rules for Claude Code
├── README.md          # This file
├── .gitignore         # Git ignore patterns
├── src/               # Source code
├── tests/             # Test files
├── docs/              # Documentation
└── output/            # Generated output files
```

## Development Guidelines

- Always search before creating new files
- Extend existing functionality rather than duplicating
- Commit after each completed task
- Push to GitHub for backup
