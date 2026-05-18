"""Housing arbitrage ranking engine.

Pure, deterministic scoring over normalised listings. No network and no
scraping live here: the engine consumes :class:`Listing` objects plus
:class:`AreaReference` data and produces a ranked list. All monetary
maths uses :class:`~decimal.Decimal`.

Scoring model
-------------
* ``arbitrage`` - how far below the area-average €/m² the asking price
  sits (the core "m²-arbitrage" signal).
* ``flip`` - return on investment after an indicative renovation, with
  buy/sell transaction costs.
* ``split`` - upside from a feasible woningsplitsing (indicative).

The three components are normalised to 0..1 and combined with
configurable weights into a single composite score used for ranking.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from pydantic import BaseModel, Field

from src.realestate.models import (
    AreaReference,
    Listing,
    RenovationLevel,
    ScoreBreakdown,
    ScoredListing,
)
from src.realestate.splitting import assess_split

# Indicative renovation cost per m² of living area, by condition band
# (EUR). Deliberately conservative ballpark figures; override per listing
# via ``FlipAssessment.renovation_cost`` when a real quote is available.
_RENO_COST_PER_M2: dict[RenovationLevel, Decimal] = {
    RenovationLevel.MOVE_IN_READY: Decimal("0"),
    RenovationLevel.COSMETIC: Decimal("250"),
    RenovationLevel.MODERATE: Decimal("750"),
    RenovationLevel.HEAVY: Decimal("1400"),
    RenovationLevel.GUT: Decimal("2200"),
}

_EUR = Decimal("1")


class ScoringConfig(BaseModel):
    """Tunable weights and cost assumptions for the ranking engine."""

    # Buy-side transaction costs as a fraction of the purchase price.
    # Default ~13% ≈ overdrachtsbelasting (investeerderstarief) + notaris
    # + aankoopmakelaar. Configurable: legal rates change and differ per
    # buyer profile, so this is an assumption, not a fixed legal figure.
    transaction_cost_pct: Decimal = Field(default=Decimal("0.13"))

    # Sell-side costs as a fraction of the after-repair value.
    selling_cost_pct: Decimal = Field(default=Decimal("0.03"))

    # Composite weights. They need not sum to 1; the result is normalised
    # by their total.
    weight_arbitrage: Decimal = Field(default=Decimal("0.45"))
    weight_flip: Decimal = Field(default=Decimal("0.40"))
    weight_split: Decimal = Field(default=Decimal("0.15"))

    # Discount at which the arbitrage score saturates to 1.0 (e.g. 0.40
    # = 40% below area average is already a perfect arbitrage signal).
    arbitrage_cap: Decimal = Field(default=Decimal("0.40"))

    # ROI at which the flip score saturates to 1.0.
    flip_roi_cap: Decimal = Field(default=Decimal("0.30"))


def _renovation_cost(listing: Listing) -> Decimal:
    """Return the explicit renovation cost or derive it from the band."""
    if listing.flip.renovation_cost is not None:
        return listing.flip.renovation_cost
    rate = _RENO_COST_PER_M2[listing.flip.level]
    return (rate * listing.living_area_m2).quantize(_EUR)


def _market_value(listing: Listing, ref: AreaReference) -> Decimal:
    """Return fair market value at area-average €/m² for living area."""
    return (ref.avg_price_per_m2 * listing.living_area_m2).quantize(_EUR)


def _resolve_reference(
    listing: Listing, references: dict[str, AreaReference]
) -> AreaReference | None:
    """Find a reference by postcode prefix (PC4) then by city.

    Args:
        listing: Listing whose region must be resolved.
        references: Mapping of region key -> :class:`AreaReference`.

    Returns:
        The matching reference, or ``None`` if no region matches.
    """
    pc4 = listing.postcode.replace(" ", "")[:4]
    if pc4 in references:
        return references[pc4]
    city_key = listing.city.strip().lower()
    return references.get(city_key)


def score_listing(
    listing: Listing,
    reference: AreaReference,
    config: ScoringConfig | None = None,
) -> ScoredListing:
    """Score a single listing against its area reference.

    Args:
        listing: The normalised listing to score.
        reference: Area-average €/m² reference for the listing's region.
        config: Optional scoring configuration; defaults are used if
            omitted.

    Returns:
        A :class:`ScoredListing` (rank is left at 0; set by
        :func:`rank_listings`).
    """
    cfg = config or ScoringConfig()

    market_value = _market_value(listing, reference)
    arv = market_value  # a renovated home is assumed to reach area avg
    reno = _renovation_cost(listing)
    buy_costs = (listing.asking_price * cfg.transaction_cost_pct).quantize(_EUR)
    sell_costs = (arv * cfg.selling_cost_pct).quantize(_EUR)
    total_in = listing.asking_price + reno + buy_costs
    profit = (arv - total_in - sell_costs).quantize(_EUR)
    roi = profit / total_in if total_in > 0 else Decimal("0")

    if market_value > 0:
        discount = (market_value - listing.asking_price) / market_value
    else:
        discount = Decimal("0")
    arb_score = _clamp(discount / cfg.arbitrage_cap)
    flip_score = _clamp(roi / cfg.flip_roi_cap)

    split = assess_split(listing)
    split_score = split.score

    weight_total = (
        cfg.weight_arbitrage + cfg.weight_flip + cfg.weight_split
    )
    composite = (
        cfg.weight_arbitrage * arb_score
        + cfg.weight_flip * flip_score
        + cfg.weight_split * split_score
    ) / weight_total

    breakdown = ScoreBreakdown(
        arbitrage_score=arb_score.quantize(Decimal("0.0001")),
        flip_score=flip_score.quantize(Decimal("0.0001")),
        split_score=split_score.quantize(Decimal("0.0001")),
        composite=composite.quantize(Decimal("0.0001")),
        market_value=market_value,
        after_repair_value=arv,
        renovation_cost=reno,
        transaction_costs=buy_costs + sell_costs,
        projected_profit=profit,
        projected_roi=roi.quantize(Decimal("0.0001")),
    )
    return ScoredListing(listing=listing, breakdown=breakdown, split=split)


def rank_listings(
    listings: Iterable[Listing],
    references: dict[str, AreaReference],
    config: ScoringConfig | None = None,
) -> list[ScoredListing]:
    """Score and rank listings best-first.

    Listings whose region cannot be resolved against ``references`` are
    skipped (they cannot be fairly compared on €/m²).

    Args:
        listings: Normalised listings to evaluate.
        references: Mapping of region key (PC4 prefix or lower-cased
            city) to :class:`AreaReference`.
        config: Optional scoring configuration.

    Returns:
        Scored listings sorted by composite score descending, with
        ``rank`` populated starting at 1.
    """
    cfg = config or ScoringConfig()
    scored: list[ScoredListing] = []
    for listing in listings:
        reference = _resolve_reference(listing, references)
        if reference is None:
            continue
        scored.append(score_listing(listing, reference, cfg))

    scored.sort(key=lambda s: s.breakdown.composite, reverse=True)
    for index, item in enumerate(scored, start=1):
        item.rank = index
    return scored


def _clamp(value: Decimal) -> Decimal:
    """Clamp a Decimal to the closed interval [0, 1]."""
    if value < 0:
        return Decimal("0")
    if value > 1:
        return Decimal("1")
    return value
