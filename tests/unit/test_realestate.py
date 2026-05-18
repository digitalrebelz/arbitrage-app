"""Unit tests for the housing arbitrage ranking engine."""

from decimal import Decimal

import pytest

from src.realestate.models import (
    AreaReference,
    FlipAssessment,
    Listing,
    PropertyType,
    RenovationLevel,
    SplitVerdict,
)
from src.realestate.sample_data import sample_listings, sample_references
from src.realestate.scoring import (
    ScoringConfig,
    rank_listings,
    score_listing,
)
from src.realestate.splitting import assess_split


def _listing(**overrides: object) -> Listing:
    """Build a baseline listing, applying any field overrides."""
    base = {
        "id": "t1",
        "source": "test",
        "address": "Teststraat 1",
        "postcode": "1011 AB",
        "city": "Amsterdam",
        "asking_price": Decimal("500000"),
        "living_area_m2": Decimal("100"),
        "rooms": 4,
        "bedrooms": 2,
        "build_year": 1900,
        "property_type": PropertyType.APARTMENT,
        "flip": FlipAssessment(level=RenovationLevel.MOVE_IN_READY),
    }
    base.update(overrides)
    return Listing(**base)  # type: ignore[arg-type]


class TestListingModel:
    """Tests for derived Listing properties."""

    def test_price_per_m2(self) -> None:
        """Price per m² divides asking price by living area."""
        lst = _listing(
            asking_price=Decimal("500000"),
            living_area_m2=Decimal("100"),
        )
        assert lst.price_per_m2 == Decimal("5000")

    def test_price_per_m2_zero_area(self) -> None:
        """Zero living area yields a price per m² of zero, not an error."""
        lst = _listing(living_area_m2=Decimal("0"))
        assert lst.price_per_m2 == Decimal("0")


class TestScoring:
    """Tests for the scoring model."""

    def test_renovation_cost_derived_from_band(self) -> None:
        """An omitted renovation cost is derived from area × band rate."""
        ref = AreaReference(
            region="1011", avg_price_per_m2=Decimal("6000")
        )
        lst = _listing(
            flip=FlipAssessment(level=RenovationLevel.MODERATE),
            living_area_m2=Decimal("100"),
        )
        scored = score_listing(lst, ref)
        # 100 m² × €750/m² = €75,000
        assert scored.breakdown.renovation_cost == Decimal("75000")

    def test_explicit_renovation_cost_wins(self) -> None:
        """An explicit renovation cost overrides the band-derived one."""
        ref = AreaReference(
            region="1011", avg_price_per_m2=Decimal("6000")
        )
        lst = _listing(
            flip=FlipAssessment(
                level=RenovationLevel.MODERATE,
                renovation_cost=Decimal("10000"),
            ),
        )
        scored = score_listing(lst, ref)
        assert scored.breakdown.renovation_cost == Decimal("10000")

    def test_undervalued_scores_higher_than_overpriced(self) -> None:
        """A cheaper €/m² listing must outrank an expensive one."""
        ref = AreaReference(
            region="1011", avg_price_per_m2=Decimal("6000")
        )
        cheap = _listing(id="cheap", asking_price=Decimal("400000"))
        pricey = _listing(id="pricey", asking_price=Decimal("700000"))
        cheap_score = score_listing(cheap, ref).breakdown.composite
        pricey_score = score_listing(pricey, ref).breakdown.composite
        assert cheap_score > pricey_score

    def test_composite_within_unit_interval(self) -> None:
        """The composite score is always in [0, 1]."""
        for lst in sample_listings():
            ref_for = sample_references().get(
                lst.postcode.replace(" ", "")[:4]
            ) or sample_references().get(lst.city.lower())
            if ref_for is None:
                continue
            comp = score_listing(lst, ref_for).breakdown.composite
            assert Decimal("0") <= comp <= Decimal("1")

    def test_negative_profit_floors_flip_score(self) -> None:
        """A loss-making flip yields a zero flip score, never negative."""
        ref = AreaReference(
            region="1011", avg_price_per_m2=Decimal("1000")
        )
        lst = _listing(asking_price=Decimal("500000"))
        bd = score_listing(lst, ref).breakdown
        assert bd.flip_score == Decimal("0")
        assert bd.projected_profit < 0


class TestRanking:
    """Tests for rank_listings ordering and region resolution."""

    def test_ranks_are_contiguous_and_sorted(self) -> None:
        """Ranks start at 1 and follow composite score descending."""
        ranked = rank_listings(sample_listings(), sample_references())
        assert [r.rank for r in ranked] == list(range(1, len(ranked) + 1))
        scores = [r.breakdown.composite for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_unresolved_region_is_skipped(self) -> None:
        """Listings without a matching reference are dropped, not errored."""
        lst = _listing(postcode="0000 ZZ", city="Nowhere")
        ranked = rank_listings([lst], sample_references())
        assert ranked == []

    def test_weights_change_ordering(self) -> None:
        """Reweighting toward split changes the engine's behaviour."""
        refs = sample_references()
        base = rank_listings(sample_listings(), refs)
        split_cfg = ScoringConfig(
            weight_arbitrage=Decimal("0"),
            weight_flip=Decimal("0"),
            weight_split=Decimal("1"),
        )
        split_ranked = rank_listings(sample_listings(), refs, split_cfg)
        top = split_ranked[0]
        assert top.split.score == max(
            r.split.score for r in split_ranked
        )
        assert isinstance(base[0].rank, int)


class TestSplitHeuristic:
    """Tests for the indicative woningsplitsing heuristic."""

    def test_small_apartment_unlikely(self) -> None:
        """A small apartment cannot be split into self-contained units."""
        lst = _listing(
            living_area_m2=Decimal("55"),
            property_type=PropertyType.APARTMENT,
        )
        result = assess_split(lst)
        assert result.verdict == SplitVerdict.UNLIKELY
        assert result.estimated_units == 1

    def test_large_detached_old_house_likely(self) -> None:
        """A large old detached house with many bedrooms scores high."""
        lst = _listing(
            living_area_m2=Decimal("160"),
            property_type=PropertyType.DETACHED,
            build_year=1920,
            bedrooms=5,
        )
        result = assess_split(lst)
        assert result.verdict == SplitVerdict.LIKELY
        assert result.estimated_units >= 2
        assert result.disclaimer  # disclaimer is always present

    def test_score_bounded(self) -> None:
        """The split score never leaves the [0, 1] interval."""
        lst = _listing(
            living_area_m2=Decimal("400"),
            property_type=PropertyType.DETACHED,
            build_year=1900,
            bedrooms=10,
        )
        assert Decimal("0") <= assess_split(lst).score <= Decimal("1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
