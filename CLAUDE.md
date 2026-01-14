# CLAUDE.md - Tool_premodel

> **Documentation Version**: 1.0
> **Last Updated**: 2026-01-14
> **Project**: Tool_premodel
> **Description**: Polymarket 15-minute binary option pricing model and market maker behavior reverse engineering
> **Features**: GitHub auto-backup, Task agents, technical debt prevention

This file provides essential guidance to Claude Code when working with code in this repository.

## Project Overview

This project aims to research Polymarket's 15-minute cryptocurrency prediction markets through:

1. **Data Engineering**: Automated pipelines collecting real-time crypto prices (Binance/Bybit) and Polymarket order book data
2. **Mathematical Modeling**: Binary options pricing with Greeks analysis (Delta, Gamma, Theta, Vega)
3. **Visualization**: 3D pricing surface visualization showing time, price, and contract value relationships

### Key Research Areas
- **Linear Decay Zone**: Price corrections with 3+ minutes remaining
- **Lock-in Effect Zone**: Minimal price movement near expiry when far from strike
- **Extreme Reversal Zone (Gamma Risk)**: Price collapse when strike is breached near expiry

## Critical Rules

### Absolute Prohibitions
- **NEVER** create new files in root directory - use `src/` structure
- **NEVER** write output files to root - use `output/` directory
- **NEVER** create documentation files unless explicitly requested
- **NEVER** create duplicate files (e.g., `manager_v2.py`, `enhanced_xyz.py`)
- **NEVER** use `find`, `grep`, `cat`, `head`, `tail` commands - use Read, Grep, Glob tools instead

### Mandatory Requirements
- **COMMIT** after every completed task
- **GITHUB BACKUP** - Push to GitHub after every commit: `git push origin main`
- **USE TASK AGENTS** for long-running operations (>30 seconds)
- **TODOWRITE** for complex tasks (3+ steps)
- **READ FILES FIRST** before editing
- **SEARCH FIRST** before creating new files - check for existing similar functionality

### Pre-Task Compliance Check

Before starting any task, verify:
- [ ] Files go in proper module structure (`src/`), not root
- [ ] Use Task agents for >30 second operations
- [ ] TodoWrite for 3+ step tasks
- [ ] Search for existing implementations before creating new files
- [ ] Commit after each completed task

## Project Structure

```
Tool_premodel/
├── CLAUDE.md          # This file - rules for Claude Code
├── README.md          # Project documentation
├── .gitignore         # Git ignore patterns
├── src/               # Source code
│   ├── main.py        # Main entry point
│   ├── data/          # Data collection modules
│   ├── models/        # Pricing models
│   └── utils/         # Utility functions
├── tests/             # Test files
├── docs/              # Documentation
└── output/            # Generated output files
```

## Common Commands

```bash
# Run main script
python src/main.py

# Run tests
pytest tests/

# Check git status
git status

# Push to GitHub backup
git push origin main
```

## Technical Debt Prevention

### Before Creating ANY New File:
1. **Search First** - Use Grep/Glob to find existing implementations
2. **Analyze Existing** - Read and understand current patterns
3. **Decision**: Can extend existing? -> DO IT | Must create new? -> Document why
4. **Follow Patterns** - Use established project patterns
5. **Validate** - Ensure no duplication

### Wrong Approach:
```python
# Creating new file without searching first
Write(file_path="new_feature.py", content="...")
```

### Correct Approach:
```python
# 1. SEARCH FIRST
Grep(pattern="feature.*implementation", include="*.py")
# 2. READ EXISTING FILES
Read(file_path="existing_feature.py")
# 3. EXTEND EXISTING FUNCTIONALITY
Edit(file_path="existing_feature.py", old_string="...", new_string="...")
```

---

**Prevention is better than consolidation - build clean from the start.**
