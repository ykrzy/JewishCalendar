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
    ]
    async_add_entities(sensors)


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