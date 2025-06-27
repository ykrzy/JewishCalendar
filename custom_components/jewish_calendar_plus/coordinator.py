from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

import hdate  # installed from manifest requirements
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Helper: find Rosh Chodesh (day 1) backwards / forwards
# ─────────────────────────────────────────────────────────────

def _find_rosh_chodesh(g: date) -> date:
    """Return Gregorian date of Rosh Chodesh for the Hebrew month containing *g*."""
    while hdate.HDateInfo(g).hdate.day != 1:
        g -= timedelta(days=1)
    return g


def _next_rosh_chodesh(current_rosh: date) -> date:
    g = current_rosh + timedelta(days=1)
    while hdate.HDateInfo(g).hdate.day != 1:
        g += timedelta(days=1)
    return g

# ─────────────────────────────────────────────────────────────
class JewishCalendarCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Shared cache for Hebrew calendar data."""

    def __init__(self, hass: HomeAssistant, loc_conf: dict) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_HOURS),
        )
        self._loc_conf = loc_conf
        self._location = hdate.Location(
            "User",
            loc_conf["lat"],
            loc_conf["lon"],
            "Asia/Jerusalem",
            0,
        )

    # ── coordinator hook ──
    async def _async_update_data(self) -> Dict[str, Any]:
        return await self._build_cache(12)

    async def async_prefetch(self, months_ahead: int = 12) -> None:
        self.data = await self._build_cache(months_ahead)
        self.async_set_updated_data(self.data)

    # ── core builders ──
    async def _build_cache(self, months_ahead: int) -> Dict[str, Any]:
        today = date.today()
        rosh = _find_rosh_chodesh(today)
        cache: Dict[str, Any] = {}
        for _ in range(months_ahead + 1):
            cache[rosh.isoformat()] = await self._build_month(rosh)
            rosh = _next_rosh_chodesh(rosh)
        return cache

    async def _build_month(self, rosh_greg: date) -> Dict[str, Any]:
        info = hdate.HDateInfo(rosh_greg)
        heb_date = info.hdate  # HebrewDate object
        title = f"{heb_date.month} {heb_date.year}"

        days: List[Dict[str, Any]] = []
        g = rosh_greg
        while hdate.HDateInfo(g).hdate.month == heb_date.month:
            di = hdate.HDateInfo(g)
            days.append(
                {
                    "hd": str(di.hdate),  # full Hebrew date in Hebrew
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

    # ── auxiliary ──
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
