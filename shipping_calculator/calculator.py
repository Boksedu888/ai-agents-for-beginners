"""Core business logic for FedEx and UPS comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .models import CarrierConfig, CarrierQuote, Package


@dataclass(frozen=True)
class EvaluationContext:
    """Derived facts about the shipment used to trigger surcharges."""

    longest_side: float
    second_longest_side: float
    shortest_side: float
    girth: float
    ahs_length: bool
    ahs_overweight: bool
    oversize: bool
    overlimit: bool


AHSL_DESCRIPTION = "AHS超长（需额外人工处理）"
AHSO_DESCRIPTION = "AHS超重"
AHSI_DESCRIPTION = "AHS不规则包装"
OVERSIZE_DESCRIPTION = "Oversize 超尺寸"
OVERLIMIT_DESCRIPTION = "超限包裹"
def derive_context(package: Package) -> EvaluationContext:
    length, width, height = package.dimensions.sorted_sides()
    girth = package.dimensions.girth()
    ahs_length = length > 48 or width > 30 or girth > 105
    oversize = length > 96 or girth > 130
    overlimit = (
        package.actual_weight > 150
        or length > 108
        or girth > 165
    )
    ahs_overweight = package.actual_weight > 50
    return EvaluationContext(
        longest_side=length,
        second_longest_side=width,
        shortest_side=height,
        girth=girth,
        ahs_length=ahs_length,
        ahs_overweight=ahs_overweight,
        oversize=oversize,
        overlimit=overlimit,
    )


def _fedex_base_weight(package: Package, context: EvaluationContext) -> float:
    """Calculate the base weight FedEx will use for billing."""

    weight = package.billable_weight
    if context.oversize:
        return max(weight, 90)
    if context.ahs_length:
        return max(weight, 40)
    return weight


def _gather_surcharges(
    package: Package, context: EvaluationContext, config: CarrierConfig
) -> List[Tuple[str, float]]:
    """Generate a list of surcharge descriptions and amounts."""

    surcharges: List[Tuple[str, float]] = []

    if context.ahs_length:
        fee = config.get_surcharge("ahs_length")
        if fee:
            surcharges.append((AHSL_DESCRIPTION, fee))

    if context.ahs_overweight:
        fee = config.get_surcharge("ahs_overweight")
        if fee:
            surcharges.append((AHSO_DESCRIPTION, fee))

    if package.ahs_irregular:
        fee = config.get_surcharge("ahs_irregular")
        if fee:
            surcharges.append((AHSI_DESCRIPTION, fee))

    if context.oversize:
        key = "oversize_residential" if package.is_residential else "oversize_commercial"
        fee = config.get_surcharge(key)
        if not fee:
            fee = config.get_surcharge("oversize")
        if fee:
            surcharges.append((OVERSIZE_DESCRIPTION, fee))

    if context.overlimit:
        fee = config.get_surcharge("overlimit")
        if fee:
            surcharges.append((OVERLIMIT_DESCRIPTION, fee))

    return surcharges


def evaluate_carrier(package: Package, config: CarrierConfig) -> CarrierQuote:
    """Compute the total for a carrier given package information."""

    context = derive_context(package)

    if config.name.lower().startswith("fedex"):
        base_weight = _fedex_base_weight(package, context)
    else:
        base_weight = package.billable_weight

    base_rate = config.get_base_rate(base_weight)
    address_surcharge = config.get_address_surcharge(package.is_residential)
    surcharge_breakdown = _gather_surcharges(package, context, config)

    remote_area_surcharge = config.get_surcharge("remote_area") if package.is_remote_area else 0.0

    subtotal = base_rate + address_surcharge + remote_area_surcharge
    for _label, value in surcharge_breakdown:
        subtotal += value

    fuel_multiplier = 1.0 + config.fuel_surcharge
    fuel_amount = subtotal * config.fuel_surcharge
    total = subtotal * fuel_multiplier

    warnings: List[str] = []
    if context.overlimit:
        warnings.append(
            "包裹触发超限条件（重量>150lbs、最长边>108inch 或 长+2x(宽+高)>165inch），FedEx/UPS可能拒收且无法申诉。"
        )
    elif context.oversize:
        warnings.append(
            "包裹触发Oversize附加费，建议确认客户是否接受高额附加成本。"
        )

    return CarrierQuote(
        carrier_name=config.name,
        base_chargeable_weight=base_weight,
        base_rate=base_rate,
        address_surcharge=address_surcharge,
        surcharge_breakdown=surcharge_breakdown,
        remote_area_surcharge=remote_area_surcharge,
        fuel_multiplier=fuel_multiplier,
        fuel_amount=fuel_amount,
        total=total,
        warnings=tuple(warnings),
    )


def compare_carriers(package: Package, configs: Iterable[CarrierConfig]) -> Tuple[CarrierQuote, ...]:
    """Return quotes for every configured carrier."""

    quotes = [evaluate_carrier(package, config) for config in configs]
    quotes.sort(key=lambda quote: quote.total)
    return tuple(quotes)
