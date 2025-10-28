#!/usr/bin/env python3
"""
🌙 Moon Dev: Multi-Asset Strategy Testing Script

Simple CLI wrapper for testing a strategy across multiple cryptocurrency assets.

Usage:
    python scripts/test_strategy_multi_asset.py <strategy_file.py>

Examples:
    # Test strategy on all available assets
    python scripts/test_strategy_multi_asset.py src/data/rbi/03_14_2025/backtests_final/MomentumStrategy_BT.py

    # Specify custom data directory
    python scripts/test_strategy_multi_asset.py strategy.py --data-dir /custom/path/to/ohlcv

    # Control parallelism
    python scripts/test_strategy_multi_asset.py strategy.py --workers 4

    # Save results to specific file
    python scripts/test_strategy_multi_asset.py strategy.py --output results/my_test.json
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.rbi_multi_asset_tester import main

if __name__ == "__main__":
    main()
