# =============================================================
# file: coordinator.py
# =============================================================
"""Coordinator that pre‑computes Hebrew months and events."""

from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict

from hebcal import HDate, HebrewCalendar, Location, Zmanim

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, DEFAULT_UPDATE_HOURS

_LOGGER = logging.getLogger(__name__)

class JewishCalendarCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Collect and cache Hebrew calendar data."""

    def __init__(self, hass: HomeAssistant, loc_conf: dict, session) -> None:
        self._loc_conf = loc_conf
        self._location = Location(
            loc_conf["lat"], loc_conf["lon"], loc_conf["tz"], "UserLocation"
        )
        self.session = session
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_HOURS),
        )

    # ---------------------------------------------------------------------
    # public helpers
    # ---------------------------------------------------------------------
    async def async_prefetch(self, months_ahead: int) -> None:
        """Fill cache up to given months ahead and write state update."""
        await self._async_update_data(months_ahead)
        self.async_set_updated_data(self.data)

    # ---------------------------------------------------------------------
    # Data generation
    # ---------------------------------------------------------------------
    async def _async_update_data(self, months_ahead: int = 12) -> Dict[str, Any]:
        today = date.today()
        current = HDate(today).start_of_hebrew_month()

        months: list[HDate] = [current]
        for _ in range(months_ahead):
            months.append(months[-1].next_hebrew_month())

        payload: Dict[str, Any] = {}
        for m in months:
            payload[m.greg().isoformat()] = await self._build_month_async(m)
        return payload

    async def _build_month_async(self, rosh: HDate) -> Dict[str, Any]:
        month_days = []
        hd = rosh.clone()
        while hd.month == rosh.month:
            greg = hd.greg()
            day_dict = {
                "hd": hd.hebrew(),
                "greg": greg.isoformat(),
                "holiday": HebrewCalendar.get_holiday_description(hd, self._location),
                "parasha": HebrewCalendar.get_parasha(hd, israel=self._loc_conf["israel"]),
                "zmanim": self._calc_zmanim(greg),
            }
            month_days.append(day_dict)
            hd = hd.next()

        return {
            "title": f"{rosh.getMonthName()} {rosh.getFullYearGematriya()}",
            "month": rosh.month,
            "year": rosh.year,
            "days": month_days,
        }

    def _calc_zmanim(self, greg: date) -> Dict[str, str]:
        try:
            z = Zmanim(self._location, greg)
            return {
                "sunrise": z.sunrise.isoformat(),
                "sunset": z.sunset.isoformat(),
                "candle_lighting": z.candle_lighting(18).isoformat(),
                "havdalah": z.tzais().isoformat(),
            }
        except Exception as err:  # pragma: no cover – runtime safety
            _LOGGER.debug("Zmanim error: %s", err)
            return {}