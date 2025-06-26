"""Coordinator that pre‑computes Hebrew calendar data using *hdate*."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict

import hdate  # installed automatically from manifest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper functions that rely only on hdate.HDateInfo (no heavy math required)
# ---------------------------------------------------------------------------

def rosh_chodesh_for(greg: date) -> date:
    """Return the Gregorian date of *Rosh Chodesh* for the month that `greg` is in."""
    g = greg
    while hdate.HDateInfo(g).get_hebrew_day() != 1:
        g -= timedelta(days=1)
    return g

def next_month_rosh(greg_rosh: date) -> date:
    """Return Gregorian date of next Hebrew month's Rosh Chodesh."""
    g = greg_rosh + timedelta(days=1)
    while hdate.HDateInfo(g).get_hebrew_day() != 1:
        g += timedelta(days=1)
    return g

# ---------------------------------------------------------------------------
class JewishCalendarCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Download‑less, purely calculative coordinator for the Jewish calendar."""

    def __init__(self, hass: HomeAssistant, loc_conf: dict,):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_HOURS),
        )
        self._loc_conf = loc_conf
        self._location = hdate.Location(
            loc_conf["lat"], loc_conf["lon"], "UserLocation"
        )

    # ─────────────────────────────────────────────────────────────
    async def _async_update_data(self) -> Dict[str, Any]:
        # default refresh pulls 12 future months
        return await self._build_month_cache(12)

    async def async_prefetch(self, months_ahead: int) -> None:
        self.data = await self._build_month_cache(months_ahead)
        self.async_set_updated_data(self.data)

    # ─────────────────────────────────────────────────────────────
    async def _build_month_cache(self, months_ahead: int) -> Dict[str, Any]:
        today = date.today()
        rosh = rosh_chodesh_for(today)
        cache: Dict[str, Any] = {}
        for _ in range(months_ahead + 1):  # include current month
            cache[rosh.isoformat()] = await self._build_month(rosh)
            rosh = next_month_rosh(rosh)
        return cache

    async def _build_month(self, rosh_greg: date) -> Dict[str, Any]:
        """Return structured JSON for one Hebrew month starting at `rosh_greg`."""
        month_info = hdate.HDateInfo(rosh_greg)
        heb_month = month_info.get_hebrew_month()
        heb_year = month_info.get_hebrew_year()
        title = f"{month_info.get_hebrew_month_name_he()} {month_info.get_hebrew_year_he()}"

        # Iterate day‑by‑day until Hebrew month rolls over
        days: list[Dict[str, Any]] = []
        g = rosh_greg
        while hdate.HDateInfo(g).get_hebrew_month() == heb_month:
            info = hdate.HDateInfo(g)
            days.append(
                {
                    "hd": info.hebrew_date_he(),
                    "greg": g.isoformat(),
                    "holiday": info.holiday_description() or "",
                    "parasha": (
                        info.parasha_he()
                        if self._loc_conf["israel"]
                        else info.parasha_he_diaspora()
                    ),
                    "omer": info.omer(),
                    "zmanim": self._calc_zmanim(g),
                }
            )
            g += timedelta(days=1)

        return {
            "title": title,
            "month": heb_month,
            "year": heb_year,
            "days": days,
        }

    def _calc_zmanim(self, greg: date) -> Dict[str, str]:
        try:
            z = hdate.Zmanim(self._location, greg)
            return {
                "sunrise": z.sunrise.isoformat(),
                "sunset": z.sunset.isoformat(),
                "candle_lighting": z.candle_lighting(18).isoformat(),
                "havdalah": z.tzais().isoformat(),
            }
        except Exception as err:
            _LOGGER.debug("Zmanim error for %s: %s", greg, err)
            return {}
