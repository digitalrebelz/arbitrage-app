"""Housing arbitrage: source-agnostic ranking engine.

Ranks for-sale listings on m²-price arbitrage versus the area average,
an indicative flip ROI and an indicative woningsplitsing signal. The
engine is pure and deterministic; ingestion (Jaap, Pararius,
Zoekallehuizen, ...) is intentionally out of scope here.
"""

from src.realestate.models import (
    AreaReference,
    FlipAssessment,
    Listing,
    PropertyType,
    RenovationLevel,
    ScoreBreakdown,
    ScoredListing,
    SplitAssessment,
    SplitVerdict,
)
from src.realestate.scoring import (
    ScoringConfig,
    rank_listings,
    score_listing,
)
from src.realestate.splitting import assess_split

__all__ = [
    "AreaReference",
    "FlipAssessment",
    "Listing",
    "PropertyType",
    "RenovationLevel",
    "ScoreBreakdown",
    "ScoredListing",
    "SplitAssessment",
    "SplitVerdict",
    "ScoringConfig",
    "rank_listings",
    "score_listing",
    "assess_split",
]
