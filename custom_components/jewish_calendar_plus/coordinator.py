"""
coordinator.py – Jewish Calendar Plus
-------------------------------------
Light LRU cache of Hebrew-month JSON using py-libhdate 1.1+

Public helper
~~~~~~~~~~~~~
    await coordinator.async_get_month(rosh_chodesh_date)

returns (and caches) the month that starts on the given Gregorian
Rosh Ḥodesh.  The calling sensor/card reads the cache via
`coordinator.cache`.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import date, timedelta
from typing import Any, Dict, List

import hdate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Number of months kept in RAM
MAX_MONTHS = 3


# ─────────────────────────────── helpers ────────────────────────────────
def _find_rosh_chodesh(g: date) -> date:
    """Return Gregorian date of Rosh Chodesh for the Hebrew month containing *g*."""
    while hdate.HDateInfo(g).hdate.day != 1:
        g -= timedelta(days=1)
    return g


def _next_rosh_chodesh(rosh: date) -> date:
    g = rosh + timedelta(days=1)
    while hdate.HDateInfo(g).hdate.day != 1:
        g += timedelta(days=1)
    return g


# ─────────────────────────────── coordinator ────────────────────────────
class JewishCalendarCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Caches Hebrew months and provides them on demand."""

    def __init__(self, hass: HomeAssistant, loc_conf: dict) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_HOURS),
        )
        self._location = hdate.Location(
            "User",
            loc_conf["lat"],
            loc_conf["lon"],
            "Asia/Jerusalem",
            0,
        )
        # OrderedDict preserves insert order → simple LRU
        self.cache: "OrderedDict[str, dict]" = OrderedDict()

    # ───────────────── coordinator hook ─────────────────
    async def _async_update_data(self) -> Dict[str, Any]:
        """Refresh current month only (called by HA scheduler)."""
        today_rosh = _find_rosh_chodesh(date.today())
        await self.async_get_month(today_rosh)
        return {}  # we don't expose huge data here

    # ───────────────── public helper ────────────────────
    async def async_get_month(self, rosh: date) -> dict:
        """Return month payload; build & cache if missing."""
        key = rosh.isoformat()
        if key not in self.cache:
            self.cache[key] = await self._build_month(rosh)
            self._enforce_size()
            # Notify listeners (sensors/cards) that cache changed
            self.async_set_updated_data({})
        return self.cache[key]

    # ───────────────── internal builders ────────────────
    async def _build_month(self, rosh_greg: date) -> dict:
        info = hdate.HDateInfo(rosh_greg)
        heb_date = info.hdate
        title = f"{heb_date.month} {heb_date.year}"

        days: List[Dict[str, Any]] = []
        g = rosh_greg
        while hdate.HDateInfo(g).hdate.month == heb_date.month:
            di = hdate.HDateInfo(g)
            days.append(
                {
                    "hd": str(di.hdate),
                    "greg": g.isoformat(),
                    "holiday": ", ".join(str(h) for h in di.holidays) if di.holidays else "",
                    "parasha": str(di.parasha) if di.parasha else "",
                    "omer": di.omer.total_days if di.omer else 0,
                    "zmanim": self._calc_zmanim(g),
                }
            )
            g += timedelta(days=1)

        return {
            "title": title,
            "month": heb_date.month.value if hasattr(heb_date.month, "value") else heb_date.month,
            "year": heb_date.year,
            "days": days,
        }

    # ───────────────── helpers ──────────────────────────
    def _enforce_size(self) -> None:
        """Keep cache ≤ MAX_MONTHS by evicting oldest entry."""
        while len(self.cache) > MAX_MONTHS:
            self.cache.popitem(last=False)

    def _calc_zmanim(self, greg: date) -> Dict[str, str]:
        try:
            z = hdate.Zmanim(self._location, greg)
            return {
                "sunrise": z.sunrise.isoformat(),
                "sunset": z.sunset.isoformat(),
                "candle_lighting": z.candle_lighting(18).isoformat(),
                "havdalah": z.havdalah().isoformat(),
            }
        except Exception as err:  # pragma: no cover
            _LOGGER.debug("Zmanim error for %s: %s", greg, err)
            return {}
