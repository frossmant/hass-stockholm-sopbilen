#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
import ssl
import urllib.parse
import urllib.request

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Exposed so config_flow.py can reuse them
CONF_ADDRESS = "address"
DEFAULT_NAME = "Stockholm Sopbilen"

BASE_URL = (
    "https://www.stockholmvattenochavfall.se/"
    "villa-och-radhus/avfallstjanster/nar-kommer-sopbilen/Search"
)

# Optional scan interval hint (HA can override)
SCAN_INTERVAL = timedelta(hours=1)

# =====================================================
# Shared HTTP + JSON parsing
# =====================================================


def fetch_sopbilen_raw(address: str) -> str:
    """Fetch raw response text from Sopbilen API using urllib (blocking)."""
    params = urllib.parse.urlencode({"address": address})
    url = f"{BASE_URL}?{params}"

    _LOGGER.debug("Fetching Sopbilen data from URL: %s", url)

    context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(url, context=context) as resp:
            status = getattr(resp, "status", None)
            text = resp.read().decode("utf-8", errors="replace")
            _LOGGER.debug("Sopbilen HTTP status: %s", status)
            if status is not None and status != 200:
                raise RuntimeError(f"HTTP {status} from Sopbilen API")
            return text
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Error fetching Sopbilen data: {e}") from e


def _parse_sopbilen_data(data):
    """Parse Sopbilen JSON into (fractions, earliest_datetime).

    fractions: dict[fraction_name, {execution_date, weekday, frequency}]
    earliest_datetime: datetime | None
    """
    fractions: dict[str, dict] = {}
    earliest_dt: datetime | None = None

    if isinstance(data, dict):
        iterable = data.items()
    elif isinstance(data, list):
        iterable = enumerate(data)
    else:
        _LOGGER.error("Unexpected JSON top-level type: %s", type(data))
        return fractions, None

    for name, entries in iterable:
        if not isinstance(entries, list) or not entries:
            continue

        entry = entries[0]
        if not isinstance(entry, dict):
            continue

        exec_date = entry.get("ExecutionDate")
        weekday = entry.get("Weekday")
        frequency = entry.get("FetchFrequency")

        fractions[str(name)] = {
            "execution_date": exec_date,
            "weekday": weekday,
            "frequency": frequency,
        }

        if not exec_date:
            continue

        parsed_dt: datetime | None = None

        # Try ISO first, then a couple of fallbacks
        for fmt in (None, "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                if fmt is None:
                    parsed_dt = datetime.fromisoformat(exec_date)
                else:
                    parsed_dt = datetime.strptime(exec_date, fmt)
                break
            except Exception:
                continue

        if parsed_dt is None:
            _LOGGER.debug(
                "Could not parse ExecutionDate '%s' for fraction '%s'",
                exec_date,
                name,
            )
            continue

        if earliest_dt is None or parsed_dt < earliest_dt:
            earliest_dt = parsed_dt

    return fractions, earliest_dt


# =====================================================
# Home Assistant sensor platform
# =====================================================

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=3600): cv.positive_int,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Set up Stockholm Sopbilen sensor via YAML."""
    address: str = config[CONF_ADDRESS]
    name: str = config[CONF_NAME]

    _LOGGER.warning(
        "Sopbilen async_setup_platform CALLED for address '%s' (name='%s')",
        address,
        name,
    )

    sensor = StockholmSopbilenSensor(hass, name, address)
    async_add_entities([sensor], update_before_add=True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Stockholm Sopbilen sensor from a config entry (GUI)."""
    address: str = entry.data["address"]
    name: str = entry.title or DEFAULT_NAME

    _LOGGER.info(
        "Setting up Stockholm Sopbilen sensor from config entry: name='%s', address='%s'",
        name,
        address,
    )

    sensor = StockholmSopbilenSensor(hass, name, address)
    async_add_entities([sensor], update_before_add=True)


class StockholmSopbilenSensor(SensorEntity):
    """Representation of a Stockholm Sopbilen sensor."""

    _attr_icon = "mdi:trash-can"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, hass: HomeAssistant, name: str, address: str) -> None:
        self.hass = hass
        self._attr_name = name
        self._address = address

        self._attr_native_value = None  # date or None
        self._fractions: dict[str, dict] = {}
        self._raw_json = None
        self._last_update_success: bool = False

    @property
    def unique_id(self) -> str:
        slug = (
            self._address.lower()
            .replace(" ", "_")
            .replace(",", "")
        )
        return f"stockholm_sopbilen_{slug}"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "address": self._address,
            "fractions": self._fractions,
            "raw_json": self._raw_json,
            "last_update_success": self._last_update_success,
        }

    async def async_update(self) -> None:
        """Fetch JSON and update sensor using shared urllib logic."""
        self._last_update_success = False

        _LOGGER.debug("async_update called for Sopbilen address '%s'", self._address)

        # Run blocking urllib in executor
        try:
            text = await self.hass.async_add_executor_job(
                fetch_sopbilen_raw,
                self._address,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "Error fetching Sopbilen data for '%s': %s",
                self._address,
                err,
            )
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            _LOGGER.error(
                "Invalid JSON returned from Sopbilen API for '%s': %s",
                self._address,
                text[:300],
            )
            return

        self._raw_json = data

        fractions, earliest_dt = _parse_sopbilen_data(data)
        self._fractions = fractions

        if earliest_dt is not None:
            # DATE sensor => native_value must be a date object
            self._attr_native_value = earliest_dt.date()
            self._last_update_success = True
            _LOGGER.info(
                "Sopbilen next pickup for '%s' is %s",
                self._address,
                self._attr_native_value,
            )
        else:
            _LOGGER.warning(
                "No valid ExecutionDate found in Sopbilen data for '%s'",
                self._address,
            )
            self._attr_native_value = None
            self._last_update_success = False


# =====================================================
# Debug CLI Mode (uses same fetch_sopbilen_raw)
# =====================================================

def debug_fetch(address: str) -> None:
    """Standalone test client using same urllib logic as HA."""
    print("=== Stockholm Sopbilen DEBUG ===", flush=True)
    print(f"Address: {address}", flush=True)

    try:
        text = fetch_sopbilen_raw(address)
    except Exception as e:
        print(f"❌ Error contacting API: {e}", flush=True)
        return

    print("\n--- Raw response preview (first 400 chars) ---", flush=True)
    print(text[:400], flush=True)
    print("---------------------------------------------\n", flush=True)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("❌ Invalid JSON returned (see preview above)", flush=True)
        return

    fractions, earliest_dt = _parse_sopbilen_data(data)

    print("📦 Fractions parsed:", flush=True)
    if not fractions:
        print("  (No fractions found)", flush=True)
    else:
        for name, info in fractions.items():
            print(f"  🗑️ {name}", flush=True)
            print(f"     • Date:      {info.get('execution_date')}", flush=True)
            print(f"     • Weekday:   {info.get('weekday')}", flush=True)
            print(f"     • Frequency: {info.get('frequency')}\n", flush=True)

    if earliest_dt:
        print(f"🗓️ Next pickup: {earliest_dt.date()}", flush=True)
    else:
        print("⚠️ No valid pickup dates found.", flush=True)


# =====================================================
# Command-line entry point
# =====================================================

if __name__ == "__main__":
    import sys

    print("Stockholm Sopbilen sensor.py running as script", flush=True)
    print(f"sys.argv = {sys.argv}", flush=True)

    if len(sys.argv) < 3:
        print("\nUsage:\n  python3 sensor.py debug \"Your Address Here\"", flush=True)
        sys.exit(1)

    mode = sys.argv[1].lower()
    addr = " ".join(sys.argv[2:])

    if mode == "debug":
        debug_fetch(addr)
    else:
        print(f"Unknown mode: {mode}", flush=True)
        print('Use: python3 sensor.py debug "address"', flush=True)
