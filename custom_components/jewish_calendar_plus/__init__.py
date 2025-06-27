"""Init for Jewish Calendar Plus integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    DATA_COORDINATOR,
    CONF_ISRAEL,
    SERVICE_PREFETCH,
    ATTR_MONTHS_AHEAD,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "calendar"]

async def async_setup(hass: HomeAssistant, _config) -> bool:
    """Set up via YAML (noop)."""
    return True

async def _svc_navigate(call):
    rosh = datetime.date.fromisoformat(call.data["rosh_chodesh"])
    sensor = hass.data[DOMAIN][entry.entry_id]["sensor"]  # store ref on setup
    await sensor.async_set_anchor(rosh)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the integration from a config entry."""
    # Delay import until requirements installed
    from .coordinator import JewishCalendarCoordinator  # pylint: disable=import-error

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

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok