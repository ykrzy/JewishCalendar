"""Sensor platform for Jewish Calendar Plus."""
from __future__ import annotations
import logging

from datetime import date

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DATA_COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    sensors = [
        HebrewDateSensor(coordinator),
        ParashaSensor(coordinator),
        HebrewMonthSensor(coordinator),
    ]
    async_add_entities(sensors)

def _find_rosh_chodesh(g: date) -> date:
    while hdate.HDateInfo(g).hdate.day != 1:
        g -= timedelta(days=1)
    return g


class _JCPSensorBase(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, name, icon):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon


class HebrewDateSensor(_JCPSensorBase):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Hebrew Date", "mdi:calendar-star")

    @property
    def native_value(self):
        today = date.today().isoformat()
        for month in self.coordinator.data.values():
            for d in month["days"]:
                if d["greg"] == today:
                    return d["hd"]
        return None

    @property
    def extra_state_attributes(self):
        # <<< ADD THIS METHOD (or merge if already present) >>>
        return {
            "month_cache": self.coordinator.data
        }

class ParashaSensor(_JCPSensorBase):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Parashat Hashavua", "mdi:book-open-page-variant")

    @property
    def native_value(self):
        today = date.today().isoformat()
        for month in self.coordinator.data.values():
            for d in month["days"]:
                if d["greg"] == today:
                    return d["parasha"] or ""
        return ""
    
class HebrewMonthSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "JCP Active Month"
    _attr_icon = "mdi:calendar-blank"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._anchor = _find_rosh_chodesh(date.today())   # month shown by default

    @property
    def native_value(self):
        # ISO string of anchor – handy if you want it in automations
        return self._anchor.isoformat()

    @property
    def extra_state_attributes(self):
        month = self.coordinator._cache.get(self.native_value) or {}
        return {"month": month}

    async def async_set_anchor(self, rosh: date):
        self._anchor = rosh
        await self.coordinator.async_get_month(rosh)
