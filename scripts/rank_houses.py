"""Demo: run the housing arbitrage ranking engine on dummy data.

Usage:
    python -m scripts.rank_houses
"""

from __future__ import annotations

from decimal import Decimal

from src.realestate.sample_data import sample_listings, sample_references
from src.realestate.scoring import rank_listings


def _fmt_eur(value: Decimal) -> str:
    """Format a Decimal as a thousands-separated EUR string."""
    return f"€{value:,.0f}"


def main() -> None:
    """Score the sample listings and print a ranked table."""
    ranked = rank_listings(sample_listings(), sample_references())

    print("Housing arbitrage ranking (dummy data)\n")
    for item in ranked:
        lst = item.listing
        bd = item.breakdown
        print(
            f"#{item.rank}  {lst.address}, {lst.city}  "
            f"[{lst.source}]"
        )
        print(
            f"    vraagprijs {_fmt_eur(lst.asking_price)} "
            f"({_fmt_eur(lst.price_per_m2)}/m²)  |  "
            f"marktwaarde {_fmt_eur(bd.market_value)}"
        )
        print(
            f"    score {bd.composite}  "
            f"(arb {bd.arbitrage_score} / flip {bd.flip_score} / "
            f"split {bd.split_score})"
        )
        print(
            f"    renovatie {_fmt_eur(bd.renovation_cost)}  "
            f"verwachte winst {_fmt_eur(bd.projected_profit)}  "
            f"ROI {bd.projected_roi:.1%}"
        )
        print(
            f"    splitsen: {item.split.verdict.value} "
            f"(~{item.split.estimated_units} units, "
            f"score {item.split.score})"
        )
        for reason in item.split.reasons:
            print(f"      - {reason}")
        print()


if __name__ == "__main__":
    main()
