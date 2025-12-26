"""CLI entrypoint for auction analysis."""
import argparse
import sys
import logging

from .pipeline import run_analysis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Auction + Keeper Value Analysis Pipeline"
    )
    parser.add_argument(
        '--start',
        type=int,
        default=2014,
        help='First season to analyze (default: 2014)'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=2024,
        help='Last season to analyze (default: 2024)'
    )
    parser.add_argument(
        '--out',
        type=str,
        default='./out',
        help='Output directory (default: ./out)'
    )
    parser.add_argument(
        '--baseline',
        type=int,
        default=2014,
        help='Baseline season for normalization (default: 2014)'
    )
    
    args = parser.parse_args()
    
    try:
        results = run_analysis(
            start_year=args.start,
            end_year=args.end,
            output_dir=args.out,
            baseline_season=args.baseline
        )
        
        logger.info("Analysis completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())


