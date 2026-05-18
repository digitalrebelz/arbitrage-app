"""Indicative woningsplitsing (house-splitting) heuristic.

This produces a rough feasibility signal only. A binding answer always
requires the municipality's huisvestingsverordening and a splitsings- or
omgevingsvergunning, which differ per gemeente. The heuristic therefore
returns a verdict plus reasons, never a hard yes/no.
"""

from __future__ import annotations

from decimal import Decimal

from src.realestate.models import (
    Listing,
    PropertyType,
    SplitAssessment,
    SplitVerdict,
)

# Rule-of-thumb minimum size for a self-contained unit (m²). Many Dutch
# municipalities use a comparable floor; the exact value varies locally.
_MIN_UNIT_M2 = Decimal("40")


def assess_split(listing: Listing) -> SplitAssessment:
    """Estimate whether a listing could be split into multiple units.

    The score combines living area, property type, construction era and
    bedroom count into a 0..1 signal. It is intentionally conservative
    and indicative only.

    Args:
        listing: The normalised listing to assess.

    Returns:
        A :class:`SplitAssessment` with verdict, score and reasons.
    """
    reasons: list[str] = []
    score = Decimal("0")

    area = listing.living_area_m2
    units = int(area // _MIN_UNIT_M2) if area > 0 else 0

    if units >= 2:
        score += Decimal("0.40")
        reasons.append(
            f"Oppervlak {area} m² → circa {units} zelfstandige units "
            f"bij minimaal {_MIN_UNIT_M2} m² per unit."
        )
    else:
        reasons.append(
            f"Oppervlak {area} m² is te klein voor zelfstandige splitsing."
        )

    if listing.property_type in (
        PropertyType.DETACHED,
        PropertyType.SEMI_DETACHED,
    ):
        score += Decimal("0.25")
        reasons.append(
            "Vrijstaand / twee-onder-een-kap: eigen entree en "
            "nutsvoorzieningen zijn doorgaans eenvoudiger te realiseren."
        )
    elif listing.property_type == PropertyType.APARTMENT:
        score -= Decimal("0.10")
        reasons.append(
            "Appartement: splitsing vaak beperkt door splitsingsakte / VvE."
        )

    if listing.build_year is not None and listing.build_year < 1945:
        score += Decimal("0.10")
        reasons.append(
            "Vooroorlogs pand: vaak gunstige indeling voor opdeling."
        )

    if listing.bedrooms is not None and listing.bedrooms >= 4:
        score += Decimal("0.15")
        reasons.append(
            f"{listing.bedrooms} slaapkamers: ruimte voor twee woonlagen "
            "of aparte units."
        )

    score = max(Decimal("0"), min(score, Decimal("1")))

    if units < 2:
        verdict = SplitVerdict.UNLIKELY
    elif score >= Decimal("0.60"):
        verdict = SplitVerdict.LIKELY
    elif score >= Decimal("0.35"):
        verdict = SplitVerdict.MAYBE
    else:
        verdict = SplitVerdict.UNLIKELY

    return SplitAssessment(
        verdict=verdict,
        score=score.quantize(Decimal("0.01")),
        estimated_units=max(units, 1),
        reasons=reasons,
    )
