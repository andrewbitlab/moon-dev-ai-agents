"""
🌙 Moon Dev's Multi-Asset Strategy Tester

Tests a single backtest strategy across multiple cryptocurrency assets
to identify which markets work best with the strategy logic.

Integrates with native RBI workflow and uses data from /src/data/ohlcv/
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import re


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.backtest_runner import run_backtest_in_conda


class MultiAssetTester:
    """Tests backtest strategies across multiple assets"""

    def __init__(self, data_dir: Optional[str] = None, max_workers: Optional[int] = None,
                 timeout: int = 300, conda_env: str = "tflow"):
        """
        Args:
            data_dir: Directory with OHLCV CSV files (default: /src/data/ohlcv/)
            max_workers: Number of parallel processes (default: CPU count)
            timeout: Timeout per backtest in seconds (default: 300)
            conda_env: Conda environment to use (default: tflow)
        """
        # Default to native Moon-Dev data location
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "ohlcv"

        self.data_dir = Path(data_dir)
        self.max_workers = max_workers or mp.cpu_count()
        self.timeout = timeout
        self.conda_env = conda_env
        self.results = []

        # Find available OHLCV data files
        self.available_assets = self._discover_assets()

        print(f"🌙 MOON DEV: Multi-Asset Strategy Tester")
        print(f"   Data directory: {self.data_dir}")
        print(f"   Available assets: {len(self.available_assets)}")
        for asset, path in self.available_assets.items():
            file_size_mb = path.stat().st_size / (1024 * 1024)
            print(f"      - {asset}: {path.name} ({file_size_mb:.1f} MB)")
        print(f"   Parallel workers: {self.max_workers}")
        print(f"   Timeout per test: {timeout}s")
        print(f"   Conda env: {conda_env}")

    def _discover_assets(self) -> Dict[str, Path]:
        """Discover all available OHLCV CSV files"""
        assets = {}

        if not self.data_dir.exists():
            print(f"⚠️🌙 MOON DEV: Data directory not found: {self.data_dir}")
            return assets

        # Find all CSV files (exclude guidelines.txt)
        for csv_file in self.data_dir.glob("*.csv"):
            # Extract symbol from filename
            # BTCUSDT.csv -> BTCUSDT
            # BTC-USD-15m.csv -> BTC-USD-15m
            symbol = csv_file.stem
            assets[symbol] = csv_file

        print(f"📊🌙 MOON DEV: Discovered {len(assets)} asset data files")
        return assets

    def _create_strategy_variant(self, strategy_path: str, asset: str,
                                  data_file_path: str, temp_dir: str) -> str:
        """
        Create a modified version of the strategy using different data file

        Args:
            strategy_path: Path to original strategy file
            asset: Asset symbol (e.g., 'BTCUSDT')
            data_file_path: Path to the OHLCV CSV for this asset
            temp_dir: Temporary directory for modified strategies

        Returns:
            Path to modified strategy file
        """
        strategy_file = Path(strategy_path)
        output_dir = Path(temp_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # New filename: OriginalStrategy_BTCUSDT.py
        new_filename = f"{strategy_file.stem}_{asset}.py"
        new_path = output_dir / new_filename

        # Load original code
        with open(strategy_file, 'r') as f:
            code = f.read()

        # Replace data paths with new asset data
        # Common patterns in Moon-Dev generated strategies:
        # data_path = "/path/to/data.csv"
        # data = pd.read_csv("/path/to/data.csv")
        # pd.read_csv('/path/to/data.csv')

        patterns_to_replace = [
            # Match: data_path = "..." or data_path = '...'
            (r'data_path\s*=\s*["\'].*?["\']', f'data_path = "{data_file_path}"'),
            # Match: pd.read_csv("...") or pd.read_csv('...')
            (r'pd\.read_csv\(["\'].*?["\']\)', f'pd.read_csv("{data_file_path}")'),
            # Match: bt.Backtest(data, Strategy) where data comes from file
            (r'data\s*=\s*pd\.read_csv\(["\'].*?["\']\)', f'data = pd.read_csv("{data_file_path}")'),
        ]

        data_path_replaced = False
        for pattern, replacement in patterns_to_replace:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code)
                data_path_replaced = True

        # If no data path found, inject after imports
        if not data_path_replaced:
            print(f"⚠️🌙 MOON DEV: No data path found in {strategy_file.name}, injecting...")
            lines = code.split('\n')
            import_end_idx = 0

            # Find end of import section
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#'):
                    import_end_idx = i + 1
                else:
                    break

            # Insert data path after imports
            lines.insert(import_end_idx, f'\n# Data path for {asset} (injected by Multi-Asset Tester)')
            lines.insert(import_end_idx + 1, f'data_path = "{data_file_path}"')
            lines.insert(import_end_idx + 2, '')
            code = '\n'.join(lines)

        # Save modified strategy
        with open(new_path, 'w') as f:
            f.write(code)

        print(f"📝🌙 MOON DEV: Created variant {new_filename}")
        return str(new_path)

    def test_strategy_on_asset(self, strategy_path: str, asset: str,
                                data_path: str, temp_dir: str) -> Dict:
        """
        Test a single strategy on a single asset

        Args:
            strategy_path: Path to strategy file
            asset: Asset symbol
            data_path: Path to OHLCV data file
            temp_dir: Temporary directory

        Returns:
            Dict with test results
        """
        strategy_name = Path(strategy_path).stem

        result = {
            'strategy': strategy_name,
            'asset': asset,
            'data_path': data_path,
            'status': 'unknown',
            'error': None,
            'metrics': {},
            'execution_time': 0,
            'timestamp': datetime.now().isoformat()
        }

        start_time = time.time()

        try:
            print(f"🔄🌙 MOON DEV: [{strategy_name} @ {asset}] Starting backtest...")

            # Create modified strategy with new data path
            modified_strategy = self._create_strategy_variant(
                strategy_path, asset, data_path, temp_dir
            )

            # Run backtest using native Moon-Dev runner
            backtest_result = run_backtest_in_conda(modified_strategy, self.conda_env)

            execution_time = time.time() - start_time
            result['execution_time'] = execution_time

            # Extract results from native runner output
            if backtest_result.get('success'):
                result['status'] = 'success'
                result['stdout'] = backtest_result.get('stdout', '')
                result['stderr'] = backtest_result.get('stderr', '')

                # Parse metrics from output
                metrics = self._parse_backtest_output(backtest_result.get('stdout', ''))
                result['metrics'] = metrics

                sharpe = metrics.get('sharpe', 'N/A')
                ret = metrics.get('return', 'N/A')
                print(f"✅🌙 MOON DEV: [{strategy_name} @ {asset}] Success ({execution_time:.1f}s) - "
                      f"Sharpe: {sharpe}, Return: {ret}%")
            else:
                result['status'] = 'failed'
                result['error'] = backtest_result.get('error', 'Unknown error')
                result['stderr'] = backtest_result.get('stderr', '')
                print(f"❌🌙 MOON DEV: [{strategy_name} @ {asset}] Failed: {result['error']}")

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
            print(f"💥🌙 MOON DEV: [{strategy_name} @ {asset}] Exception: {str(e)}")

        return result

    def _parse_backtest_output(self, output: str) -> Dict:
        """
        Parse backtesting.py output for key metrics

        Looks for patterns like:
        - Sharpe Ratio: 2.34
        - Return [%]: 45.67
        - Max Drawdown [%]: -8.23
        - # Trades: 123
        """
        metrics = {}

        patterns = {
            'return': [
                r'Return\s*\[%\]\s*([+-]?\d+\.?\d*)',
                r'Total Return.*?([+-]?\d+\.?\d*)%',
                r'Return.*?([+-]?\d+\.?\d*)',
            ],
            'sharpe': [
                r'Sharpe Ratio\s*([+-]?\d+\.?\d*)',
                r'Sharpe\s*([+-]?\d+\.?\d*)',
            ],
            'max_drawdown': [
                r'Max\.?\s*Drawdown\s*\[%\]\s*([+-]?\d+\.?\d*)',
                r'Max\.?\s*DD.*?([+-]?\d+\.?\d*)',
            ],
            'trades': [
                r'# Trades\s*(\d+)',
                r'Trades\s*(\d+)',
                r'Number of trades.*?(\d+)',
            ],
            'win_rate': [
                r'Win Rate\s*\[%\]\s*(\d+\.?\d*)',
                r'Win Rate.*?(\d+\.?\d*)%',
            ]
        }

        for metric_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    try:
                        metrics[metric_name] = float(match.group(1))
                        break
                    except:
                        pass

        return metrics

    def test_strategy_on_all_assets(self, strategy_path: str) -> List[Dict]:
        """
        Test a single strategy across all available assets

        Args:
            strategy_path: Path to the strategy file

        Returns:
            List of result dicts
        """
        if not self.available_assets:
            print("❌🌙 MOON DEV: No assets available for testing!")
            return []

        strategy_name = Path(strategy_path).stem

        print(f"\n{'='*80}")
        print(f"🎯🌙 MOON DEV: Multi-Asset Testing for {strategy_name}")
        print(f"{'='*80}")
        print(f"   Strategy: {strategy_path}")
        print(f"   Assets to test: {len(self.available_assets)}")
        print(f"   Parallel workers: {self.max_workers}")
        print(f"   Total tests: {len(self.available_assets)}")
        print(f"{'='*80}\n")

        # Create temporary directory for modified strategies
        temp_dir = tempfile.mkdtemp(prefix=f'moon_dev_multi_asset_{strategy_name}_')
        print(f"📁🌙 MOON DEV: Temp directory: {temp_dir}\n")

        # Create test tasks for each asset
        tasks = [
            (strategy_path, asset, str(data_path), temp_dir)
            for asset, data_path in self.available_assets.items()
        ]

        results = []
        completed = 0
        total = len(tasks)

        # Execute tests in parallel using ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self.test_strategy_on_asset, *task): task
                for task in tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    progress = (completed / total) * 100
                    print(f"\n📊🌙 MOON DEV: Progress: {completed}/{total} ({progress:.1f}%)")

                except Exception as e:
                    print(f"💥🌙 MOON DEV: Exception for task {task[1]}: {str(e)}")
                    completed += 1

        self.results = results
        print(f"\n✅🌙 MOON DEV: Testing complete! {len(results)} tests finished")

        # Cleanup temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"🧹🌙 MOON DEV: Cleaned up temp directory")
        except Exception as e:
            print(f"⚠️🌙 MOON DEV: Could not clean temp dir: {e}")

        return results

    def save_results(self, output_path: str):
        """Save test results to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'timestamp': datetime.now().isoformat(),
            'strategy': self.results[0]['strategy'] if self.results else 'unknown',
            'total_tests': len(self.results),
            'assets_tested': list(self.available_assets.keys()),
            'max_workers': self.max_workers,
            'timeout': self.timeout,
            'conda_env': self.conda_env,
            'results': self.results
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾🌙 MOON DEV: Results saved to {output_path}")
        return output_file

    def print_summary(self):
        """Print comprehensive summary of multi-asset test results"""
        if not self.results:
            print("⚠️🌙 MOON DEV: No results to summarize")
            return

        successful = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] in ['failed', 'error']]

        print(f"\n{'='*80}")
        print(f"📊🌙 MOON DEV: MULTI-ASSET TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Strategy: {self.results[0]['strategy']}")
        print(f"Total tests: {len(self.results)}")
        print(f"✅ Successful: {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        print(f"❌ Failed: {len(failed)}")
        print("")

        # Rank assets by performance (Sharpe Ratio)
        successful_with_metrics = [
            r for r in successful
            if r.get('metrics', {}).get('sharpe') is not None
        ]

        if successful_with_metrics:
            successful_with_metrics.sort(
                key=lambda x: x['metrics'].get('sharpe', -999),
                reverse=True
            )

            print(f"🏆 ASSET RANKING (by Sharpe Ratio):")
            print(f"{'-'*80}")
            print(f"{'Rank':<6} {'Asset':<15} {'Sharpe':<10} {'Return%':<12} {'Trades':<10} {'Win%':<10}")
            print(f"{'-'*80}")

            for i, result in enumerate(successful_with_metrics, 1):
                asset = result['asset']
                metrics = result.get('metrics', {})
                sharpe = metrics.get('sharpe', 'N/A')
                ret = metrics.get('return', 'N/A')
                trades = metrics.get('trades', 'N/A')
                win_rate = metrics.get('win_rate', 'N/A')

                sharpe_str = f"{sharpe:.2f}" if isinstance(sharpe, (int, float)) else str(sharpe)
                ret_str = f"{ret:.2f}" if isinstance(ret, (int, float)) else str(ret)
                trades_str = f"{int(trades)}" if isinstance(trades, (int, float)) else str(trades)
                win_str = f"{win_rate:.1f}" if isinstance(win_rate, (int, float)) else str(win_rate)

                print(f"{i:<6} {asset:<15} {sharpe_str:<10} {ret_str:<12} {trades_str:<10} {win_str:<10}")

            print("")

            # Best and worst assets
            best = successful_with_metrics[0]
            worst = successful_with_metrics[-1]

            print(f"🥇 Best Asset: {best['asset']} (Sharpe: {best['metrics']['sharpe']:.2f}, Return: {best['metrics']['return']:.2f}%)")
            print(f"🥉 Worst Asset: {worst['asset']} (Sharpe: {worst['metrics']['sharpe']:.2f}, Return: {worst['metrics']['return']:.2f}%)")

            # Average metrics across all successful tests
            avg_sharpe = sum(r['metrics']['sharpe'] for r in successful_with_metrics) / len(successful_with_metrics)
            avg_return = sum(r['metrics']['return'] for r in successful_with_metrics) / len(successful_with_metrics)

            print(f"\n📈 Average Performance Across Assets:")
            print(f"   Avg Sharpe: {avg_sharpe:.2f}")
            print(f"   Avg Return: {avg_return:.2f}%")

        else:
            print("⚠️ No successful tests with metrics found")

        print(f"{'='*80}\n")


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("🌙 MOON DEV: Multi-Asset Strategy Tester")
        print("\nUsage: python rbi_multi_asset_tester.py <strategy_file.py> [options]")
        print("\nOptions:")
        print("  --data-dir <path>    : Custom data directory (default: /src/data/ohlcv/)")
        print("  --workers <n>        : Number of parallel workers (default: CPU count)")
        print("  --timeout <seconds>  : Timeout per test (default: 300)")
        print("  --output <file.json> : Save results to JSON file")
        print("\nExample:")
        print("  python rbi_multi_asset_tester.py src/data/rbi/03_14_2025/backtests_final/MomentumStrategy_BT.py")
        return

    strategy_path = sys.argv[1]

    if not Path(strategy_path).exists():
        print(f"❌ Strategy file not found: {strategy_path}")
        return

    # Parse optional arguments
    data_dir = None
    workers = None
    timeout = 300
    output_file = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--data-dir' and i + 1 < len(sys.argv):
            data_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--workers' and i + 1 < len(sys.argv):
            workers = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--timeout' and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Create tester
    tester = MultiAssetTester(
        data_dir=data_dir,
        max_workers=workers,
        timeout=timeout
    )

    # Run tests
    results = tester.test_strategy_on_all_assets(strategy_path)

    # Print summary
    tester.print_summary()

    # Save results if requested
    if output_file:
        tester.save_results(output_file)
    else:
        # Default save location
        strategy_name = Path(strategy_path).stem
        default_output = Path(__file__).parent.parent / "data" / "multi_asset_results" / f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        tester.save_results(str(default_output))


if __name__ == "__main__":
    main()
