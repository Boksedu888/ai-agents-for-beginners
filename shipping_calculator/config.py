"""Configuration utilities for the shipping calculator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .models import CarrierConfig


class ConfigurationError(RuntimeError):
    """Raised when the configuration file is invalid."""


def _normalize_base_rates(raw_rates: Dict[str, float]) -> Dict[float, float]:
    normalized: Dict[float, float] = {}
    for key, value in raw_rates.items():
        try:
            normalized[float(key)] = float(value)
        except ValueError as exc:
            raise ConfigurationError(f"Invalid base rate entry '{key}: {value}'") from exc
    if not normalized:
        raise ConfigurationError("Carrier configuration must define at least one base rate.")
    return normalized


def load_carrier_configs(path: str | Path) -> Dict[str, CarrierConfig]:
    """Load and normalize carrier configurations from a JSON file."""

    config_path = Path(path)
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file '{config_path}' does not exist.")

    with config_path.open("r", encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Unable to parse configuration: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError("Configuration root must be a JSON object.")

    carrier_configs: Dict[str, CarrierConfig] = {}
    for carrier_key, raw_config in payload.items():
        if not isinstance(raw_config, dict):
            raise ConfigurationError(f"Carrier '{carrier_key}' configuration must be an object.")

        try:
            base_rates = _normalize_base_rates(raw_config["base_rates"])
            address_surcharge = {
                key: float(value)
                for key, value in raw_config.get("address_surcharge", {}).items()
            }
            fuel_surcharge = float(raw_config.get("fuel_surcharge", 0.0))
            surcharges = {
                key: float(value) for key, value in raw_config.get("surcharges", {}).items()
            }
        except KeyError as exc:
            raise ConfigurationError(
                f"Carrier '{carrier_key}' is missing required field: {exc.args[0]}"
            ) from exc
        except ValueError as exc:
            raise ConfigurationError(
                f"Carrier '{carrier_key}' has a non-numeric configuration value: {exc}"
            ) from exc

        carrier_configs[carrier_key.lower()] = CarrierConfig(
            name=raw_config.get("name", carrier_key),
            base_rates=base_rates,
            address_surcharge=address_surcharge,
            fuel_surcharge=fuel_surcharge,
            surcharges=surcharges,
        )

    if not carrier_configs:
        raise ConfigurationError("Configuration file must contain at least one carrier entry.")

    return carrier_configs
