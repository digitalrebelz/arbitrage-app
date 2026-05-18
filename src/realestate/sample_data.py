"""Dummy listings and area references for the ranking engine.

These stand in for a future source-agnostic ingestion layer (Jaap,
Pararius, Zoekallehuizen, ...). They let the ranking engine be exercised
end-to-end without any scraping.
"""

from __future__ import annotations

from decimal import Decimal

from src.realestate.models import (
    AreaReference,
    FlipAssessment,
    Listing,
    PropertyType,
    RenovationLevel,
)


def sample_references() -> dict[str, AreaReference]:
    """Return reference €/m² keyed by PC4 prefix and by city name."""
    refs = [
        AreaReference(
            region="1011",
            avg_price_per_m2=Decimal("8200"),
            period="2026-Q1",
            source="sample",
        ),
        AreaReference(
            region="3024",
            avg_price_per_m2=Decimal("4100"),
            period="2026-Q1",
            source="sample",
        ),
        AreaReference(
            region="groningen",
            avg_price_per_m2=Decimal("3300"),
            period="2026-Q1",
            source="sample",
        ),
    ]
    return {r.region: r for r in refs}


def sample_listings() -> list[Listing]:
    """Return a small, varied set of dummy listings from mixed sources."""
    return [
        Listing(
            id="jaap-1",
            source="jaap",
            url="https://www.jaap.nl/example/1",
            address="Prinsengracht 100",
            postcode="1011 AB",
            city="Amsterdam",
            asking_price=Decimal("675000"),
            living_area_m2=Decimal("95"),
            rooms=4,
            bedrooms=2,
            build_year=1890,
            energy_label="E",
            property_type=PropertyType.APARTMENT,
            description="Karakteristiek grachtenpand, gedateerde keuken.",
            flip=FlipAssessment(
                level=RenovationLevel.MODERATE,
                notes="Keuken en badkamer vervangen, vloer schuren.",
            ),
        ),
        Listing(
            id="pararius-7",
            source="pararius",
            url="https://www.pararius.nl/example/7",
            address="Schiedamseweg 12",
            postcode="3024 XL",
            city="Rotterdam",
            asking_price=Decimal("245000"),
            living_area_m2=Decimal("130"),
            plot_area_m2=Decimal("140"),
            rooms=6,
            bedrooms=4,
            build_year=1932,
            energy_label="F",
            property_type=PropertyType.SEMI_DETACHED,
            description="Ruime woning, casco op de bovenverdieping.",
            flip=FlipAssessment(
                level=RenovationLevel.HEAVY,
                notes="Grondige renovatie, indeling geschikt voor opdelen.",
            ),
        ),
        Listing(
            id="zah-22",
            source="zoekallehuizen",
            url="https://www.zoekallehuizen.nl/example/22",
            address="Hereweg 250",
            postcode="9725 AK",
            city="Groningen",
            asking_price=Decimal("310000"),
            living_area_m2=Decimal("88"),
            rooms=4,
            bedrooms=3,
            build_year=1975,
            energy_label="C",
            property_type=PropertyType.TERRACED,
            description="Instapklare tussenwoning, recent gerenoveerd.",
            flip=FlipAssessment(level=RenovationLevel.MOVE_IN_READY),
        ),
        Listing(
            id="jaap-9",
            source="jaap",
            url="https://www.jaap.nl/example/9",
            address="Korreweg 5",
            postcode="9718 AB",
            city="Groningen",
            asking_price=Decimal("199000"),
            living_area_m2=Decimal("105"),
            rooms=5,
            bedrooms=4,
            build_year=1925,
            energy_label="G",
            property_type=PropertyType.DETACHED,
            description="Verouderd vrijstaand pand, ideaal kluswoning.",
            flip=FlipAssessment(
                level=RenovationLevel.GUT,
                renovation_cost=Decimal("180000"),
                notes="Volledig strippen; groot perceel, splitsbaar.",
            ),
        ),
    ]
