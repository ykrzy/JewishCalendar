"""Init for Jewish Calendar Plus integration."""
from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.platform import async_forward_entry_setups
from .const import (
    DOMAIN,
    DATA_COORDINATOR,
    CONF_ISRAEL,
    SERVICE_PREFETCH,
    ATTR_MONTHS_AHEAD,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "calendar"]

# ─────────────────────────────────────────────────────────────
async def async_setup(hass: HomeAssistant, config) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Import here so that hdate dependency is installed first
    from .coordinator import JewishCalendarCoordinator

    coord = JewishCalendarCoordinator(
        hass,
        {
            "lat": entry.data[CONF_LATITUDE],
            "lon": entry.data[CONF_LONGITUDE],
            "israel": entry.data[CONF_ISRAEL],
        },
    )
    await coord.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_COORDINATOR: coord}

    async def _service_prefetch(call: ServiceCall):
        await coord.async_prefetch(call.data.get(ATTR_MONTHS_AHEAD, 6))

    if SERVICE_PREFETCH not in hass.services.async_services().get(DOMAIN, {}):
        hass.services.async_register(DOMAIN, SERVICE_PREFETCH, _service_prefetch)

    await async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await async_forward_entry_setups(entry, [])
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
