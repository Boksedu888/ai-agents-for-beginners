"""Domain models used by the shipping calculator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class Dimensions:
    """Represents the dimensions of a package in inches."""

    length: float
    width: float
    height: float

    def sorted_sides(self) -> Tuple[float, float, float]:
        """Return sides sorted from longest to shortest."""

        sides = sorted([self.length, self.width, self.height], reverse=True)
        return sides[0], sides[1], sides[2]

    def girth(self) -> float:
        """Return the girth used by carriers."""

        longest, second, third = self.sorted_sides()
        return longest + 2 * (second + third)


@dataclass(frozen=True)
class Package:
    """Represents an outbound shipment."""

    dimensions: Dimensions
    actual_weight: float
    billable_weight: float
    is_residential: bool
    is_remote_area: bool
    ahs_irregular: bool = False


@dataclass(frozen=True)
class CarrierConfig:
    """Configuration and surcharge table for a carrier."""

    name: str
    base_rates: Dict[float, float]
    address_surcharge: Dict[str, float]
    fuel_surcharge: float
    surcharges: Dict[str, float]

    def get_base_rate(self, chargeable_weight: float) -> float:
        """Return the base rate for the provided weight."""

        weight_breaks = sorted(self.base_rates.keys())
        for weight in weight_breaks:
            if chargeable_weight <= weight:
                return self.base_rates[weight]
        return self.base_rates[weight_breaks[-1]]

    def get_address_surcharge(self, is_residential: bool) -> float:
        return self.address_surcharge.get("residential" if is_residential else "commercial", 0.0)

    def get_surcharge(self, name: str, default: float = 0.0) -> float:
        return self.surcharges.get(name, default)


@dataclass(frozen=True)
class CarrierQuote:
    """Detailed cost breakdown for a carrier."""

    carrier_name: str
    base_chargeable_weight: float
    base_rate: float
    address_surcharge: float
    surcharge_breakdown: List[Tuple[str, float]]
    remote_area_surcharge: float
    fuel_multiplier: float
    fuel_amount: float
    total: float
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class ComparisonResult:
    """Aggregated quote comparison between carriers."""

    package: Package
    quotes: Tuple[CarrierQuote, ...]

    def as_rows(self) -> Iterable[Tuple[str, float]]:
        for quote in self.quotes:
            yield quote.carrier_name, quote.total
