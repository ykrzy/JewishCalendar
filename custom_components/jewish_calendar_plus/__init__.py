"""Init for Jewish Calendar Plus integration."""
from __future__ import annotations

import datetime as dt
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    DATA_COORDINATOR,
    CONF_ISRAEL,
    SERVICE_PREFETCH,
    ATTR_MONTHS_AHEAD,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "calendar"]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up via YAML (noop)."""
    return True


# ────────────────────────────────────────────────────────────
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the integration from a config entry."""
    from .coordinator import JewishCalendarCoordinator  # imported late for deps

    # 1 – Create the coordinator
    coordinator = JewishCalendarCoordinator(
        hass,
        {
            "lat": entry.data[CONF_LATITUDE],
            "lon": entry.data[CONF_LONGITUDE],
            "israel": entry.data[CONF_ISRAEL],
        },
    )
    await coordinator.async_config_entry_first_refresh()

    # 2 – Store integration-wide objects
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,   # will add month_sensor below
    }

    # 3 – Forward to sensor / calendar platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 4 – Grab the month-sensor reference after platforms loaded
    #     (entity_id is deterministic because we create exactly one)
    month_sensor = hass.states.async_entity_ids("sensor").get(
        f"sensor.jcp_active_month_{entry.entry_id}"
    )
    hass.data[DOMAIN][entry.entry_id]["month_sensor"] = hass.data["entity_components"][
        "sensor"
    ].get_entity(month_sensor)

    # 5 – Service: prefetch N months
    async def _svc_prefetch(call: ServiceCall) -> None:
        months = call.data.get(ATTR_MONTHS_AHEAD, 6)
        await coordinator.async_prefetch(months)

    if SERVICE_PREFETCH not in hass.services.async_services().get(DOMAIN, {}):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PREFETCH,
            _svc_prefetch,
        )

    # 6 – Service: navigate to specific Rosh Chodesh
    async def _svc_navigate(call: ServiceCall) -> None:
        rosh = dt.date.fromisoformat(call.data["rosh_chodesh"])
        await coordinator.async_get_month(rosh)
        await hass.data[DOMAIN][entry.entry_id]["month_sensor"].async_set_anchor(rosh)

    if "navigate" not in hass.services.async_services().get(DOMAIN, {}):
        hass.services.async_register(
            DOMAIN,
            "navigate",
            _svc_navigate,
        )

    return True


# ────────────────────────────────────────────────────────────
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
