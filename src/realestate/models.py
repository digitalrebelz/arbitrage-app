"""Domain models for the housing arbitrage ranking engine.

Source-agnostic: a :class:`Listing` may originate from Funda, Jaap,
Pararius, Zoekallehuizen or any other portal. The ranking engine never
talks to a scraper; it consumes already-normalised listings plus
reference data. Money is always :class:`~decimal.Decimal`.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """Coarse property typology relevant for flip/split potential."""

    APARTMENT = "apartment"  # appartement
    TERRACED = "terraced"  # tussenwoning
    CORNER = "corner"  # hoekwoning
    SEMI_DETACHED = "semi_detached"  # twee-onder-een-kap
    DETACHED = "detached"  # vrijstaand
    OTHER = "other"


class RenovationLevel(str, Enum):
    """Indicative condition band.

    In the full system this is inferred by a vision LLM from photos and
    floor plans. The ranking engine treats it as a structured input.
    """

    MOVE_IN_READY = "move_in_ready"  # instapklaar
    COSMETIC = "cosmetic"  # opfrissen: schilderwerk, vloer
    MODERATE = "moderate"  # keuken + badkamer vervangen
    HEAVY = "heavy"  # grondige renovatie
    GUT = "gut"  # casco / strippen


class SplitVerdict(str, Enum):
    """Indicative outcome of the woningsplitsing heuristic."""

    LIKELY = "likely"
    MAYBE = "maybe"
    UNLIKELY = "unlikely"
    UNKNOWN = "unknown"


class AreaReference(BaseModel):
    """Reference price per m² for a region (CBS/Kadaster/NVM style)."""

    region: str = Field(..., description="Region key: postcode prefix or city")
    avg_price_per_m2: Decimal = Field(
        ..., description="Average sale price per m² of living area (EUR)"
    )
    period: str = Field(default="", description="Reference period, e.g. '2026-Q1'")
    source: str = Field(default="", description="Data source label")


class FlipAssessment(BaseModel):
    """Structured renovation input for one listing."""

    level: RenovationLevel = Field(..., description="Condition band")
    renovation_cost: Decimal | None = Field(
        default=None,
        description="Explicit total renovation cost (EUR); derived if omitted",
    )
    notes: str = Field(default="", description="Free-text rationale")


class Listing(BaseModel):
    """A normalised for-sale listing from any source."""

    id: str = Field(..., description="Stable id within the source")
    source: str = Field(..., description="Source label: jaap|pararius|funda|...")
    url: str = Field(default="", description="Original listing URL")

    address: str = Field(..., description="Street and number")
    postcode: str = Field(..., description="Dutch postcode, e.g. '1011AB'")
    city: str = Field(..., description="City")

    asking_price: Decimal = Field(..., description="Asking price (EUR)")
    living_area_m2: Decimal = Field(..., description="Woonoppervlak (m²)")
    plot_area_m2: Decimal | None = Field(
        default=None, description="Perceeloppervlak (m²)"
    )

    rooms: int = Field(..., description="Total number of rooms")
    bedrooms: int | None = Field(default=None, description="Number of bedrooms")
    build_year: int | None = Field(default=None, description="Construction year")
    energy_label: str | None = Field(
        default=None, description="Energy label A-G"
    )
    property_type: PropertyType = Field(
        default=PropertyType.OTHER, description="Property typology"
    )

    description: str = Field(default="", description="Raw listing description")
    flip: FlipAssessment = Field(..., description="Indicative renovation input")

    @property
    def price_per_m2(self) -> Decimal:
        """Return the asking price per m² of living area (0 if unknown)."""
        if self.living_area_m2 <= 0:
            return Decimal("0")
        return self.asking_price / self.living_area_m2


class SplitAssessment(BaseModel):
    """Indicative woningsplitsing feasibility.

    This is a rough signal only and never a legal guarantee.
    """

    verdict: SplitVerdict = Field(..., description="Indicative verdict")
    score: Decimal = Field(..., description="Heuristic score in 0..1")
    estimated_units: int = Field(
        ..., description="Plausible number of self-contained units"
    )
    reasons: list[str] = Field(
        default_factory=list, description="Human-readable rationale"
    )
    disclaimer: str = Field(
        default=(
            "Indicatief. Definitieve splitsing vereist toetsing aan de "
            "gemeentelijke huisvestingsverordening en een splitsings- of "
            "omgevingsvergunning. Verifieer altijd bij de gemeente."
        ),
        description="Mandatory legal disclaimer",
    )


class ScoreBreakdown(BaseModel):
    """Transparent component scores and the financial model behind them."""

    arbitrage_score: Decimal = Field(
        ..., description="Undervaluation vs area average, normalised 0..1"
    )
    flip_score: Decimal = Field(
        ..., description="Post-renovation ROI, normalised 0..1"
    )
    split_score: Decimal = Field(
        ..., description="Split upside contribution, 0..1"
    )
    composite: Decimal = Field(..., description="Weighted final score, 0..1")

    market_value: Decimal = Field(..., description="Fair value at area avg €/m²")
    after_repair_value: Decimal = Field(..., description="Value once renovated")
    renovation_cost: Decimal = Field(..., description="Renovation cost used (EUR)")
    transaction_costs: Decimal = Field(
        ..., description="Buy + sell costs used (EUR)"
    )
    projected_profit: Decimal = Field(..., description="Projected profit (EUR)")
    projected_roi: Decimal = Field(
        ..., description="Profit / total invested, as a fraction"
    )


class ScoredListing(BaseModel):
    """A listing with its computed score, split assessment and rank."""

    listing: Listing = Field(..., description="The scored listing")
    breakdown: ScoreBreakdown = Field(..., description="Score components")
    split: SplitAssessment = Field(..., description="Indicative split signal")
    rank: int = Field(default=0, description="1 = best opportunity")
