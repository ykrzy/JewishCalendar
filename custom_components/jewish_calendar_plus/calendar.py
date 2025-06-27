"""Calendar entity exposing holidays to Home‑Assistant."""
from __future__ import annotations
import logging
from datetime import date, datetime
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEvent,
)

from .const import DOMAIN, DATA_COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([JewishCalendarEntity(coordinator)])


class JewishCalendarEntity(CoordinatorEntity, CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Jewish Calendar"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "jcp_calendar"

    # ------------------------------------------------------------------
    # CalendarEntity abstract methods
    # ------------------------------------------------------------------
    async def async_get_events(self, hass, start_date, end_date):
        events: List[CalendarEvent] = []
        start_d = start_date.date()
        end_d = end_date.date()
        for month in self.coordinator.data.values():
            for d in month["days"]:
                g_dt = datetime.fromisoformat(d["greg"])
                g_d = g_dt.date()
                if start_d <= g_d <= end_d and d["holiday"]:
                    events.append(CalendarEvent(g_dt, g_dt, d["holiday"]))
        return events


    @property
    def event(self):
        today = date.today()
        for month in self.coordinator.data.values():
            for d in month["days"]:
                g = datetime.fromisoformat(d["greg"]).date()
                if g >= today and d["holiday"]:
                    return CalendarEvent(g, g, d["holiday"])
        return None