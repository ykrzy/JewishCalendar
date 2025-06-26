"""Init for Jewish Calendar Plus integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_TIME_ZONE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.platform import async_forward_entry_setups

from .const import (
    DOMAIN,
    DATA_COORDINATOR,
    CONF_ISRAEL,
    SERVICE_PREFETCH,
    ATTR_MONTHS_AHEAD,
)
from .coordinator import JewishCalendarCoordinator

PLATFORMS = ["sensor", "calendar"]

_LOGGER = logging.getLogger(__name__)

def _get_location(entry: ConfigEntry) -> dict:
    data = entry.data
    return {
        "lat": data[CONF_LATITUDE],
        "lon": data[CONF_LONGITUDE],
        "tz": data[CONF_TIME_ZONE],
        "israel": data[CONF_ISRAEL],
    }

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up via YAML is not supported."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jewish Calendar Plus from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    coordinator = JewishCalendarCoordinator(hass, _get_location(entry), session)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    async def _handle_prefetch(call: ServiceCall) -> None:
        months = call.data.get(ATTR_MONTHS_AHEAD, 6)
        await coordinator.async_prefetch(months)

    if SERVICE_PREFETCH not in hass.services.async_services().get(DOMAIN, {}):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PREFETCH,
            _handle_prefetch,
            schema=None,
        )

    await async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await async_forward_entry_setups(entry, [])
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok