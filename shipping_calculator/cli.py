"""Command line interface for the shipping calculator."""

from __future__ import annotations

import argparse
import textwrap
from typing import Iterable, Sequence

from .calculator import compare_carriers
from .config import ConfigurationError, load_carrier_configs
from .models import Dimensions, Package


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shipping-calculator",
        description="Compare FedEx and UPS parcel charges under complex surcharge rules.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Example:
              python -m shipping_calculator \
                --config shipping_calculator/sample_config.json \
                --length 97 --width 15 --height 10 \
                --actual-weight 55 --billable-weight 60 \
                --address-type residential --remote-area
            """
        ),
    )
    parser.add_argument("--config", required=True, help="Path to the JSON configuration file.")
    parser.add_argument("--length", type=float, required=True, help="Longest side in inches.")
    parser.add_argument("--width", type=float, required=True, help="Middle side in inches.")
    parser.add_argument("--height", type=float, required=True, help="Shortest side in inches.")
    parser.add_argument("--actual-weight", type=float, required=True, help="Actual weight in lbs.")
    parser.add_argument(
        "--billable-weight",
        type=float,
        help="Billable/Dimensional weight in lbs (defaults to actual weight).",
    )
    parser.add_argument(
        "--address-type",
        choices=("residential", "commercial"),
        default="commercial",
        help="Destination address type for delivery surcharge.",
    )
    parser.add_argument(
        "--ahs-irregular",
        action="store_true",
        help="Flag that the package uses soft or irregular packaging that triggers AHS handling.",
    )
    parser.add_argument(
        "--remote-area",
        action="store_true",
        help="Apply remote area surcharge when enabled in the configuration.",
    )
    parser.add_argument(
        "--currency",
        default="$",
        help="Currency symbol used when printing results (default: $).",
    )
    return parser


def format_currency(value: float, symbol: str) -> str:
    return f"{symbol}{value:,.2f}"


def render_quote_rows(quote, symbol: str) -> Sequence[str]:
    rows = [
        f"基础运费重量: {quote.base_chargeable_weight:.2f} lbs",
        f"基础运费: {format_currency(quote.base_rate, symbol)}",
        f"地址派送费: {format_currency(quote.address_surcharge, symbol)}",
    ]
    if quote.remote_area_surcharge:
        rows.append(f"偏远地区附加费: {format_currency(quote.remote_area_surcharge, symbol)}")

    if quote.surcharge_breakdown:
        rows.append("附加费:")
        for label, amount in quote.surcharge_breakdown:
            rows.append(f"  - {label}: {format_currency(amount, symbol)}")
    else:
        rows.append("附加费: 无")

    rows.append(
        f"燃油附加费 ({(quote.fuel_multiplier - 1) * 100:.2f}%): {format_currency(quote.fuel_amount, symbol)}"
    )
    rows.append(f"总价: {format_currency(quote.total, symbol)}")

    if quote.warnings:
        rows.append("注意事项:")
        for warning in quote.warnings:
            rows.append(f"  - {warning}")

    return rows


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    billable_weight = args.billable_weight if args.billable_weight is not None else args.actual_weight
    package = Package(
        dimensions=Dimensions(length=args.length, width=args.width, height=args.height),
        actual_weight=args.actual_weight,
        billable_weight=billable_weight,
        is_residential=args.address_type == "residential",
        is_remote_area=args.remote_area,
        ahs_irregular=args.ahs_irregular,
    )

    try:
        carrier_configs = load_carrier_configs(args.config)
    except ConfigurationError as exc:
        parser.error(str(exc))

    quotes = compare_carriers(package, carrier_configs.values())

    print("=======================")
    print("美国本土 FedEx / UPS 邮费比价")
    print("=======================")
    print(
        f"包裹信息: {package.dimensions.length}x{package.dimensions.width}x{package.dimensions.height} inch, "
        f"实重 {package.actual_weight} lbs, 计费重 {package.billable_weight} lbs"
    )
    print(f"地址类型: {'住宅' if package.is_residential else '商业'}, 偏远地区: {'是' if package.is_remote_area else '否'}")
    if package.ahs_irregular:
        print("提示: 包裹使用软包装或不规则包装，已启用AHS不规则费用。")
    print()

    for quote in quotes:
        print(f"-- {quote.carrier_name} --")
        for row in render_quote_rows(quote, args.currency):
            print(row)
        print()

    if len(quotes) >= 2:
        best = quotes[0]
        runner_up = quotes[1]
        diff = runner_up.total - best.total
        print(
            f"最低报价: {best.carrier_name} ({format_currency(best.total, args.currency)})，"
            f"比下一个报价节省 {format_currency(diff, args.currency)}"
        )
    else:
        print("提示: 仅载入了一个承运商配置，无法比较。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
