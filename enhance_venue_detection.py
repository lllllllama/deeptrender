"""
Enhanced Venue Detection for arXiv Papers

This script improves venue detection by:
1. Extracting conference info from comments field
2. Using enhanced pattern matching
3. Cross-validating with multiple sources
4. Reprocessing existing arXiv papers

Usage:
    python enhance_venue_detection.py --reprocess
    python enhance_venue_detection.py --test
"""

import sys
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import get_raw_repository, get_structured_repository
from agents.structuring_agent import StructuringAgent


# Enhanced venue patterns with year extraction
VENUE_PATTERNS_ENHANCED = {
    "NeurIPS": [
        r"NeurIPS['\s]*(\d{2,4})",
        r"NIPS['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+NeurIPS['\s]*(\d{2,4})?",
        r"Neural Information Processing Systems['\s]*(\d{2,4})?",
    ],
    "ICLR": [
        r"ICLR['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+ICLR['\s]*(\d{2,4})?",
        r"International Conference on Learning Representations['\s]*(\d{2,4})?",
    ],
    "ICML": [
        r"ICML['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+ICML['\s]*(\d{2,4})?",
        r"International Conference on Machine Learning['\s]*(\d{2,4})?",
    ],
    "CVPR": [
        r"CVPR['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+CVPR['\s]*(\d{2,4})?",
        r"Computer Vision and Pattern Recognition['\s]*(\d{2,4})?",
    ],
    "ICCV": [
        r"ICCV['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+ICCV['\s]*(\d{2,4})?",
        r"International Conference on Computer Vision['\s]*(\d{2,4})?",
    ],
    "ECCV": [
        r"ECCV['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+ECCV['\s]*(\d{2,4})?",
        r"European Conference on Computer Vision['\s]*(\d{2,4})?",
    ],
    "ACL": [
        r"ACL['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+ACL['\s]*(\d{2,4})?",
        r"Association for Computational Linguistics['\s]*(\d{2,4})?",
    ],
    "EMNLP": [
        r"EMNLP['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+EMNLP['\s]*(\d{2,4})?",
    ],
    "NAACL": [
        r"NAACL['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+NAACL['\s]*(\d{2,4})?",
    ],
    "AAAI": [
        r"AAAI['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+AAAI['\s]*(\d{2,4})?",
    ],
    "IJCAI": [
        r"IJCAI['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+IJCAI['\s]*(\d{2,4})?",
    ],
    "CoRL": [
        r"CoRL['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+CoRL['\s]*(\d{2,4})?",
    ],
    "AISTATS": [
        r"AISTATS['\s]*(\d{2,4})",
        r"accepted\s+(?:by|at|to)\s+AISTATS['\s]*(\d{2,4})?",
    ],
}


def extract_venue_from_comments(comments: str) -> Tuple[Optional[str], Optional[int], float]:
    """
    Extract venue and year from comments field

    Args:
        comments: Comments string from arXiv

    Returns:
        (venue_name, year, confidence)
    """
    if not comments:
        return (None, None, 0.0)

    # Try each venue pattern
    for venue_name, patterns in VENUE_PATTERNS_ENHANCED.items():
        for pattern in patterns:
            match = re.search(pattern, comments, re.IGNORECASE)
            if match:
                # Extract year if captured
                year = None
                if match.groups():
                    year_str = match.group(1)
                    if year_str:
                        try:
                            year_int = int(year_str)
                            # Convert 2-digit year to 4-digit
                            if year_int < 100:
                                year = 2000 + year_int
                            else:
                                year = year_int
                        except:
                            pass

                # Determine confidence based on pattern type
                confidence = 0.9 if "accepted" in pattern.lower() else 0.7

                return (venue_name, year, confidence)

    return (None, None, 0.0)


def extract_venue_from_journal_ref(journal_ref: str) -> Tuple[Optional[str], Optional[int], float]:
    """
    Extract venue from journal reference field

    Args:
        journal_ref: Journal reference string

    Returns:
        (venue_name, year, confidence)
    """
    if not journal_ref:
        return (None, None, 0.0)

    for venue_name, patterns in VENUE_PATTERNS_ENHANCED.items():
        for pattern in patterns:
            match = re.search(pattern, journal_ref, re.IGNORECASE)
            if match:
                year = None
                if match.groups():
                    year_str = match.group(1)
                    if year_str:
                        try:
                            year_int = int(year_str)
                            if year_int < 100:
                                year = 2000 + year_int
                            else:
                                year = year_int
                        except:
                            pass

                return (venue_name, year, 0.8)

    return (None, None, 0.0)


def test_venue_extraction():
    """Test venue extraction on sample comments"""
    test_cases = [
        "15 pages, 4 figures, 11 tables, accepted by NeurIPS'23",
        "AcceurIPS 2023",
        "16 pages, 9 figures, AAAI'26 (accepted)",
        "CVPR 2024",
        "To appear in ICLR 2025",
        "26 Pages, 10 Figures, 4 Tables",  # No venue
    ]

    print("=" * 70)
    print("Testing Venue Extraction")
    print("=" * 70)

    for i, comment in enumerate(test_cases, 1):
        venue, year, confidence = extract_venue_from_comments(comment)
        print(f"\n{i}. Comment: {comment}")
        print(f"   Result: venue={venue}, year={year}, confidence={confidence:.2f}")
        if venue:
            print(f"   [SUCCESS] Extracted venue information")
        else:
            print(f"   [NO VENUE] Could not extract venue")

    print("\n" + "=" * 70)


def reprocess_arxiv_papers(dry_run: bool = False):
    """
    Reprocess all arXiv papers to extract venue information

    Args:
        dry_run: If True, only show what would be updated without actually updating
    """
    raw_repo = get_raw_repository()
    structured_repo = get_structured_repository()

    print("=" * 70)
    print("Reprocessing arXiv Papers for Venue Detection")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will update database)'}")
    print()

    # Get all arXiv papers
    arxiv_papers = raw_repo.get_raw_papers_by_source("arxiv")
    print(f"Found {len(arxiv_papers)} arXiv papers")
    print()

    # Statistics
    stats = {
        "total": len(arxiv_papers),
        "with_comments": 0,
        "with_journal_ref": 0,
        "venue_found": 0,
        "venue_updated": 0,
        "venues": {},
    }

    # Process each paper
    for i, raw_paper in enumerate(arxiv_papers, 1):
        venue_name = None
        year = None
        confidence = 0.0
        source = None

        # Try comments
        if raw_paper.comments:
            stats["with_comments"] += 1
            v, y, c = extract_venue_from_comments(raw_paper.comments)
            if v and c > confidence:
                venue_name, year, confidence, source = v, y, c, "comments"

        # Try journal_ref field
        if raw_paper.journal_ref:
            stats["with_journal_ref"] += 1
            v, y, c = extract_venue_from_journal_ref(raw_paper.journal_ref)
            if v and c > confidence:
                venue_name, year, confidence, source = v, y, c, "journal_ref"

        # If venue found
        if venue_name:
            stats["venue_found"] += 1
            stats["venues"][venue_name] = stats["venues"].get(venue_name, 0) + 1

            if i <= 5:  # Show first 5 examples
                print(f"[{i}] {raw_paper.title[:60]}...")
                print(f"    Venue: {venue_name} {year if year else ''} (confidence: {confidence:.2f}, source: {source})")
                if source == "comments":
                    print(f"    Comments: {raw_paper.comments[:80]}...")
                elif source == "journal_ref":
                    print(f"    Journal: {raw_paper.journal_ref[:80]}...")
                print()

            # Update database if not dry run
            if not dry_run:
                try:
                    # Find corresponding structured paper by raw_id
                    with structured_repo._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT paper_id FROM paper_sources
                            WHERE raw_id = ?
                        """, (raw_paper.raw_id,))
                        result = cursor.fetchone()

                        if result:
                            paper_id = result['paper_id']

                            # Get or create venue
                            venue = structured_repo.get_venue_by_name(venue_name)
                            if not venue:
                                # Create new venue
                                from scraper.models import Venue
                                new_venue = Venue(
                                    canonical_name=venue_name,
                                    venue_type="conference",
                                    domain=None
                                )
                                venue_id = structured_repo.save_venue(new_venue)
                            else:
                                venue_id = venue.venue_id

                            # Update paper venue
                            cursor.execute("""
                                UPDATE papers
                                SET venue_id = ?, venue_type = 'conference'
                                WHERE paper_id = ?
                            """, (venue_id, paper_id))
                            conn.commit()
                            stats["venue_updated"] += 1

                except Exception as e:
                    print(f"    [ERROR] Failed to update: {e}")

    # Print statistics
    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)
    print(f"Total papers: {stats['total']}")
    print(f"With comments: {stats['with_comments']} ({stats['with_comments']/stats['total']*100:.1f}%)")
    print(f"With journal_ref: {stats['with_journal_ref']} ({stats['with_journal_ref']/stats['total']*100:.1f}%)")
    print(f"Venue found: {stats['venue_found']} ({stats['venue_found']/stats['total']*100:.1f}%)")

    if not dry_run:
        print(f"Venue updated: {stats['venue_updated']}")

    print("\nVenue distribution:")
    for venue, count in sorted(stats['venues'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {venue}: {count}")

    print("=" * 70)

    return stats


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhance venue detection for arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test venue extraction on sample comments"
    )

    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess all arXiv papers"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no database changes)"
    )

    args = parser.parse_args()

    if args.test:
        test_venue_extraction()
    elif args.reprocess:
        reprocess_arxiv_papers(dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
