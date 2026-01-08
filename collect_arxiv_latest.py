"""
arXiv Latest Data Collection Script

Features:
1. Collect recent arXiv papers (last N days)
2. Support multiple AI categories
3. Auto-save to database
4. Show progress and statistics
5. Support resume from interruption

Usage:
    python collect_arxiv_latest.py --days 7 --max-results 1000
    python collect_arxiv_latest.py --days 30 --categories cs.LG cs.CV
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.arxiv_client import create_arxiv_client, DEFAULT_CATEGORIES
from database import get_raw_repository


def collect_latest_papers(
    days: int = 7,
    categories: list = None,
    max_results: int = 1000,
    verbose: bool = True
):
    """
    Collect latest arXiv papers

    Args:
        days: Collect papers from last N days
        categories: arXiv category list
        max_results: Maximum number of papers
        verbose: Show detailed information

    Returns:
        Collection statistics
    """
    # Initialize
    client = create_arxiv_client(delay=3.0)
    repo = get_raw_repository()
    categories = categories or DEFAULT_CATEGORIES

    print("=" * 70)
    print("arXiv Latest Data Collection")
    print("=" * 70)
    print(f"Time range: Last {days} days")
    print(f"Categories: {', '.join(categories)}")
    print(f"Target: {max_results} papers")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Collect papers
    papers = client.search_recent(
        categories=categories,
        days=days,
        max_results=max_results
    )

    if not papers:
        print("WARNING: No papers fetched")
        return {
            "fetched": 0,
            "saved": 0,
            "duplicates": 0,
            "errors": 0
        }

    print(f"\nSUCCESS: Fetched {len(papers)} papers")
    print("\n" + "=" * 70)
    print("Saving to database...")
    print("=" * 70)

    # Save to database
    saved = 0
    duplicates = 0
    errors = 0

    for i, paper in enumerate(papers, 1):
        try:
            repo.save_raw_paper(paper)
            saved += 1

            if verbose and i % 10 == 0:
                print(f"   Progress: {i}/{len(papers)} ({i/len(papers)*100:.1f}%)")

        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint failed" in error_msg:
                duplicates += 1
            else:
                errors += 1
                if verbose:
                    print(f"   ERROR: Failed to save: {paper.title[:50]}... - {e}")

    # Statistics
    print("\n" + "=" * 70)
    print("Collection Statistics")
    print("=" * 70)
    print(f"Fetched: {len(papers)} papers")
    print(f"Saved: {saved} papers")
    print(f"Duplicates: {duplicates} papers")
    print(f"Errors: {errors} papers")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Show samples
    if papers and verbose:
        print("\nSample Papers:")
        print("-" * 70)
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper.title}")
            print(f"   Year: {paper.year}")
            print(f"   Categories: {paper.categories}")
            print(f"   Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
            if paper.comments:
                print(f"   Comments: {paper.comments[:80]}...")

    return {
        "fetched": len(papers),
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors
    }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Collect latest arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect papers from last 7 days
  python collect_arxiv_latest.py --days 7

  # Collect cs.LG and cs.CV papers from last 30 days
  python collect_arxiv_latest.py --days 30 --categories cs.LG cs.CV

  # Collect papers from last 14 days, max 2000 papers
  python collect_arxiv_latest.py --days 14 --max-results 2000
        """
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Collect papers from last N days (default: 7)"
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help=f"arXiv category list (default: {' '.join(DEFAULT_CATEGORIES)})"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Maximum number of papers (default: 1000)"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Quiet mode, no detailed output"
    )

    args = parser.parse_args()

    # Execute collection
    try:
        stats = collect_latest_papers(
            days=args.days,
            categories=args.categories,
            max_results=args.max_results,
            verbose=not args.quiet
        )

        # Return status code
        if stats["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nWARNING: Collection interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nERROR: Collection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
