#!/usr/bin/env python3
"""
🌙 Moon Dev: RBI Results Analyzer

Analyzes backtest results from RBI agents (batch runs, multi-asset tests, etc.)
Generates reports, exports to Excel, and creates visualizations.

Usage:
    python scripts/analyze_rbi_results.py <results.json> [options]

Examples:
    # Basic analysis with summary
    python scripts/analyze_rbi_results.py results.json

    # Export to Excel with multiple sheets
    python scripts/analyze_rbi_results.py results.json --excel output.xlsx

    # Generate distribution plots
    python scripts/analyze_rbi_results.py results.json --plots

    # Filter by criteria
    python scripts/analyze_rbi_results.py results.json --min-sharpe 2.0 --min-return 10

    # Generate comprehensive report
    python scripts/analyze_rbi_results.py results.json --report summary.txt
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("❌ pandas not installed. Run: pip install pandas")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("⚠️ matplotlib/seaborn not installed. Plotting disabled.")


class RBIResultsAnalyzer:
    """Analyzes RBI backtest results and generates reports"""

    def __init__(self, results_file: str):
        """
        Args:
            results_file: Path to JSON file with backtest results
        """
        self.results_file = Path(results_file)
        self.raw_data = None
        self.df = None

        print(f"🌙 MOON DEV: RBI Results Analyzer")
        print(f"   Results file: {self.results_file}")

        self._load_results()

    def _load_results(self):
        """Load results from JSON and convert to DataFrame"""
        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, 'r') as f:
            self.raw_data = json.load(f)

        # Extract results array (support different formats)
        results = self.raw_data.get('results', [])

        if not results:
            print("⚠️🌙 MOON DEV: No results found in file")
            self.df = pd.DataFrame()
            return

        # Convert to DataFrame
        self.df = pd.DataFrame(results)

        # Normalize metrics dict into separate columns
        if 'metrics' in self.df.columns:
            metrics_df = pd.json_normalize(self.df['metrics'])
            # Add metric_ prefix to avoid column name conflicts
            metrics_df.columns = ['metric_' + col for col in metrics_df.columns]
            self.df = pd.concat([self.df.drop('metrics', axis=1), metrics_df], axis=1)

        print(f"✅🌙 MOON DEV: Loaded {len(self.df)} test results")

    def filter_successful(self, min_sharpe: Optional[float] = None,
                         min_return: Optional[float] = None,
                         min_trades: Optional[int] = None) -> pd.DataFrame:
        """
        Filter successful strategies by criteria

        Args:
            min_sharpe: Minimum Sharpe Ratio
            min_return: Minimum return %
            min_trades: Minimum number of trades

        Returns:
            Filtered DataFrame
        """
        df_filtered = self.df[self.df['status'] == 'success'].copy()

        if min_sharpe is not None and 'metric_sharpe' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['metric_sharpe'] >= min_sharpe]

        if min_return is not None and 'metric_return' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['metric_return'] >= min_return]

        if min_trades is not None and 'metric_trades' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['metric_trades'] >= min_trades]

        return df_filtered.sort_values('metric_sharpe', ascending=False, errors='ignore')

    def get_top_strategies(self, n: int = 10, sort_by: str = 'sharpe') -> pd.DataFrame:
        """
        Get top N strategies

        Args:
            n: Number of strategies to return
            sort_by: Metric to sort by ('sharpe', 'return', 'trades')

        Returns:
            DataFrame with top strategies
        """
        df_successful = self.df[self.df['status'] == 'success'].copy()

        sort_col = f'metric_{sort_by}'
        if sort_col not in df_successful.columns:
            print(f"⚠️🌙 MOON DEV: Column {sort_col} not found")
            return pd.DataFrame()

        return df_successful.nlargest(n, sort_col)

    def generate_summary_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate comprehensive text summary report

        Args:
            output_path: Optional path to save report (if None, returns string)

        Returns:
            Report as string
        """
        report = []
        report.append("=" * 80)
        report.append("🌙 MOON DEV: BACKTEST RESULTS ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Source file: {self.results_file.name}")
        report.append("")

        # Overall statistics
        report.append("OVERALL STATISTICS")
        report.append("-" * 80)
        report.append(f"Total tests:          {len(self.df)}")

        successful = self.df[self.df['status'] == 'success']
        failed = self.df[self.df['status'] == 'failed']
        errors = self.df[self.df['status'] == 'error']
        timeouts = self.df[self.df['status'] == 'timeout']

        report.append(f"✅ Successful:        {len(successful)} ({len(successful)/len(self.df)*100:.1f}%)")
        report.append(f"❌ Failed:            {len(failed)}")
        report.append(f"💥 Errors:            {len(errors)}")
        report.append(f"⏱️  Timeouts:          {len(timeouts)}")
        report.append("")

        # Performance statistics (successful only)
        if len(successful) > 0:
            report.append("PERFORMANCE METRICS (successful tests only)")
            report.append("-" * 80)

            if 'metric_sharpe' in successful.columns:
                sharpe = successful['metric_sharpe'].dropna()
                if len(sharpe) > 0:
                    report.append(f"Sharpe Ratio:")
                    report.append(f"  Mean:      {sharpe.mean():.2f}")
                    report.append(f"  Median:    {sharpe.median():.2f}")
                    report.append(f"  Max:       {sharpe.max():.2f}")
                    report.append(f"  Min:       {sharpe.min():.2f}")
                    report.append(f"  Std Dev:   {sharpe.std():.2f}")
                    report.append("")

            if 'metric_return' in successful.columns:
                returns = successful['metric_return'].dropna()
                if len(returns) > 0:
                    report.append(f"Return %:")
                    report.append(f"  Mean:      {returns.mean():.2f}%")
                    report.append(f"  Median:    {returns.median():.2f}%")
                    report.append(f"  Max:       {returns.max():.2f}%")
                    report.append(f"  Min:       {returns.min():.2f}%")
                    report.append(f"  Std Dev:   {returns.std():.2f}%")
                    report.append("")

            if 'metric_trades' in successful.columns:
                trades = successful['metric_trades'].dropna()
                if len(trades) > 0:
                    report.append(f"Number of Trades:")
                    report.append(f"  Mean:      {trades.mean():.0f}")
                    report.append(f"  Median:    {trades.median():.0f}")
                    report.append(f"  Max:       {trades.max():.0f}")
                    report.append(f"  Min:       {trades.min():.0f}")
                    report.append("")

        # Top 20 strategies
        if len(successful) > 0 and 'metric_sharpe' in successful.columns:
            report.append("🏆 TOP 20 STRATEGIES (by Sharpe Ratio)")
            report.append("-" * 80)

            # Determine strategy name column
            name_col = 'strategy_name' if 'strategy_name' in successful.columns else 'strategy'

            if name_col in successful.columns:
                report.append(f"{'Rank':<6} {'Strategy':<40} {'Sharpe':<10} {'Return%':<12} {'Trades':<10}")
                report.append("-" * 80)

                top_20 = self.get_top_strategies(n=20, sort_by='sharpe')
                for i, (idx, row) in enumerate(top_20.iterrows(), 1):
                    name = str(row.get(name_col, 'Unknown'))[:38]
                    sharpe = row.get('metric_sharpe', float('nan'))
                    ret = row.get('metric_return', float('nan'))
                    trades = row.get('metric_trades', float('nan'))

                    sharpe_str = f"{sharpe:.2f}" if pd.notna(sharpe) else 'N/A'
                    ret_str = f"{ret:.2f}" if pd.notna(ret) else 'N/A'
                    trades_str = f"{int(trades)}" if pd.notna(trades) else 'N/A'

                    report.append(f"{i:<6} {name:<40} {sharpe_str:<10} {ret_str:<12} {trades_str:<10}")

                report.append("")

        # Premium strategies (Sharpe > 2.0, Return > 0%)
        if len(successful) > 0:
            premium = self.filter_successful(min_sharpe=2.0, min_return=0)
            if len(premium) > 0:
                report.append(f"⭐ PREMIUM STRATEGIES (Sharpe > 2.0, Return > 0%): {len(premium)}")
                report.append("-" * 80)

                name_col = 'strategy_name' if 'strategy_name' in premium.columns else 'strategy'

                if name_col in premium.columns:
                    for i, (idx, row) in enumerate(premium.head(10).iterrows(), 1):
                        name = row.get(name_col, 'Unknown')
                        sharpe = row.get('metric_sharpe', 0)
                        ret = row.get('metric_return', 0)
                        report.append(f"  {i}. {name} - Sharpe: {sharpe:.2f}, Return: {ret:.2f}%")

                report.append("")

        report.append("=" * 80)

        report_text = "\n".join(report)

        # Save if requested
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"📄🌙 MOON DEV: Report saved to {output_path}")

        return report_text

    def export_to_excel(self, output_path: str):
        """
        Export results to Excel with multiple sheets

        Args:
            output_path: Path to Excel file
        """
        try:
            import openpyxl
        except ImportError:
            print("❌ openpyxl not installed. Run: pip install openpyxl")
            return

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # All results
            self.df.to_excel(writer, sheet_name='All_Results', index=False)

            # Successful only
            successful = self.df[self.df['status'] == 'success']
            if len(successful) > 0:
                successful.to_excel(writer, sheet_name='Successful', index=False)

            # Top 50
            if len(successful) > 0 and 'metric_sharpe' in successful.columns:
                top_50 = self.get_top_strategies(n=50, sort_by='sharpe')
                top_50.to_excel(writer, sheet_name='Top_50_Sharpe', index=False)

            # Premium (Sharpe > 2.0, Return > 0%)
            premium = self.filter_successful(min_sharpe=2.0, min_return=0)
            if len(premium) > 0:
                premium.to_excel(writer, sheet_name='Premium_Sharpe_2_Plus', index=False)

        print(f"📊🌙 MOON DEV: Results exported to {output_path}")

    def plot_distributions(self, output_dir: Optional[str] = None):
        """
        Generate distribution plots for metrics

        Args:
            output_dir: Directory to save plots (if None, displays interactively)
        """
        if not PLOTTING_AVAILABLE:
            print("❌🌙 MOON DEV: Plotting libraries not available")
            return

        successful = self.df[self.df['status'] == 'success']

        if len(successful) == 0:
            print("⚠️🌙 MOON DEV: No successful tests to visualize")
            return

        # Setup style
        sns.set_style("whitegrid")
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('🌙 Moon Dev: Backtest Metrics Distributions', fontsize=16)

        # Sharpe Ratio distribution
        if 'metric_sharpe' in successful.columns:
            ax = axes[0, 0]
            sharpe = successful['metric_sharpe'].dropna()
            if len(sharpe) > 0:
                sharpe.hist(bins=50, ax=ax, edgecolor='black', alpha=0.7)
                ax.axvline(sharpe.median(), color='red', linestyle='--', linewidth=2, label=f'Median: {sharpe.median():.2f}')
                ax.axvline(2.0, color='green', linestyle='--', linewidth=2, label='Target: 2.0')
                ax.set_title('Sharpe Ratio Distribution')
                ax.set_xlabel('Sharpe Ratio')
                ax.set_ylabel('Frequency')
                ax.legend()

        # Return % distribution
        if 'metric_return' in successful.columns:
            ax = axes[0, 1]
            returns = successful['metric_return'].dropna()
            if len(returns) > 0:
                returns.hist(bins=50, ax=ax, edgecolor='black', alpha=0.7)
                ax.axvline(returns.median(), color='red', linestyle='--', linewidth=2, label=f'Median: {returns.median():.2f}%')
                ax.axvline(0, color='green', linestyle='--', linewidth=2, label='Break-even')
                ax.set_title('Return % Distribution')
                ax.set_xlabel('Return %')
                ax.set_ylabel('Frequency')
                ax.legend()

        # Number of trades distribution
        if 'metric_trades' in successful.columns:
            ax = axes[1, 0]
            trades = successful['metric_trades'].dropna()
            if len(trades) > 0:
                trades.hist(bins=50, ax=ax, edgecolor='black', alpha=0.7)
                ax.axvline(trades.median(), color='red', linestyle='--', linewidth=2, label=f'Median: {trades.median():.0f}')
                ax.set_title('Number of Trades Distribution')
                ax.set_xlabel('Trades')
                ax.set_ylabel('Frequency')
                ax.legend()

        # Sharpe vs Return scatter
        if 'metric_sharpe' in successful.columns and 'metric_return' in successful.columns:
            ax = axes[1, 1]
            sharpe = successful['metric_sharpe'].dropna()
            returns = successful['metric_return'].dropna()
            common_idx = sharpe.index.intersection(returns.index)

            if len(common_idx) > 0:
                ax.scatter(sharpe[common_idx], returns[common_idx], alpha=0.6, s=50)
                ax.axvline(2.0, color='green', linestyle='--', alpha=0.5, linewidth=2, label='Sharpe Target: 2.0')
                ax.axhline(0, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Break-even')
                ax.set_title('Sharpe Ratio vs Return %')
                ax.set_xlabel('Sharpe Ratio')
                ax.set_ylabel('Return %')
                ax.legend()
                ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_dir:
            output_path = Path(output_dir) / 'distribution_plots.png'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"📈🌙 MOON DEV: Plots saved to {output_path}")
        else:
            plt.show()


def main():
    """Main CLI function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="🌙 Moon Dev: Analyze RBI backtest results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'results_file',
        type=str,
        help='Path to JSON results file'
    )

    parser.add_argument(
        '--excel',
        type=str,
        metavar='FILE',
        help='Export results to Excel file'
    )

    parser.add_argument(
        '--report',
        type=str,
        metavar='FILE',
        help='Generate summary report to text file'
    )

    parser.add_argument(
        '--plots',
        action='store_true',
        help='Generate distribution plots'
    )

    parser.add_argument(
        '--plot-dir',
        type=str,
        metavar='DIR',
        help='Directory to save plots (default: shows interactively)'
    )

    parser.add_argument(
        '--min-sharpe',
        type=float,
        metavar='N',
        help='Filter by minimum Sharpe Ratio'
    )

    parser.add_argument(
        '--min-return',
        type=float,
        metavar='N',
        help='Filter by minimum return %'
    )

    parser.add_argument(
        '--min-trades',
        type=int,
        metavar='N',
        help='Filter by minimum number of trades'
    )

    args = parser.parse_args()

    # Create analyzer
    analyzer = RBIResultsAnalyzer(args.results_file)

    # Apply filters if specified
    if args.min_sharpe or args.min_return or args.min_trades:
        print(f"\n🔍🌙 MOON DEV: Applying filters...")
        filtered = analyzer.filter_successful(
            min_sharpe=args.min_sharpe,
            min_return=args.min_return,
            min_trades=args.min_trades
        )
        print(f"   Filtered to {len(filtered)} strategies")

    # Generate report
    report = analyzer.generate_summary_report(output_path=args.report)
    print(report)

    # Export to Excel
    if args.excel:
        analyzer.export_to_excel(args.excel)

    # Generate plots
    if args.plots:
        analyzer.plot_distributions(output_dir=args.plot_dir)


if __name__ == "__main__":
    main()
