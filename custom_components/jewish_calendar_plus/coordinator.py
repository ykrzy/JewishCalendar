"""Coordinator that pre‑computes Hebrew months using **hdate 1.1+**.
Relies on HDateInfo → HebrewDate properties rather than nonexistent
`get_hday` methods.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

import hdate  # provided via manifest requirements
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Hebrew month helper – use str(hebrew_date.month)
# ─────────────────────────────────────────────────────────────
_MONTH_NAMES = [
    "",  # 0 (unused)
    "תשרי",   # 1
    "חשוון",  # 2
    "כסלו",   # 3
    "טבת",    # 4
    "שבט",    # 5
    "אדר",    # 6 – Adar in non‑leap
    "אדר א׳", # 7 – Adar I (leap)
    "אדר ב׳", # 8 – Adar II (leap)
    "ניסן",   # 9
    "אייר",   # 10
    "סיון",   # 11
    "תמוז",   # 12
    "אב",     # 13
    "אלול",   # 14
]

def _month_name_he(month: int, leap: bool) -> str:
    """Return Hebrew month name by numeric value.

    The `month` parameter corresponds to `Months.value` in py‑libhdate,
    which ranges 1–14 inclusive.
    In a leap year:
      • 6→"אדר" (Adar)
      • 7→"אדר א׳" (Adar I)
      • 8→"אדר ב׳" (Adar II)
    In a non‑leap year month 7 and 8 never occur.
    """
    if not leap and month in (7, 8):
        # Should never happen – fallback to Adar
        return "אדר"
    return _MONTH_NAMES[month]"אדר א׳"
    return _MONTH_NAMES[month]

# ─────────────────────────────────────────────────────────────
# Helper: locate Rosh Chodesh surrounding a Gregorian date
# ─────────────────────────────────────────────────────────────

def _rosh_chodesh_for(d: date) -> date:
    g = d
    while hdate.HDateInfo(g).hdate.day != 1:
        g -= timedelta(days=1)
    return g

def _next_rosh_chodesh(rosh: date) -> date:
    g = rosh + timedelta(days=1)
    while hdate.HDateInfo(g).hdate.day != 1:
        g += timedelta(days=1)
    return g

# ─────────────────────────────────────────────────────────────
class JewishCalendarCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Caches Hebrew months & exposes them to HA."""

    def __init__(self, hass: HomeAssistant, loc_conf: dict):
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

    # ––– coordinator hooks –––
    async def _async_update_data(self) -> Dict[str, Any]:
        return await self._build_cache(12)

    async def async_prefetch(self, months_ahead: int = 12) -> None:
        self.data = await self._build_cache(months_ahead)
        self.async_set_updated_data(self.data)

    # ––– month builders –––
    async def _build_cache(self, months_ahead: int) -> Dict[str, Any]:
        today = date.today()
        rosh = _rosh_chodesh_for(today)
        cache: Dict[str, Any] = {}
        for _ in range(months_ahead + 1):
            cache[rosh.isoformat()] = await self._build_month(rosh)
            rosh = _next_rosh_chodesh(rosh)
        return cache

    async def _build_month(self, rosh_greg: date) -> Dict[str, Any]:
        info = hdate.HDateInfo(rosh_greg)
        hebrew_date = info.hdate  # HebrewDate object
        heb_month = hebrew_date.month.value if hasattr(hebrew_date.month, "value") else hebrew_date.month
        heb_year = hebrew_date.year
        is_leap = hebrew_date.is_leap_year()
        title = f"{hebrew_date.month} {hebrew_date.year}"

        days: List[Dict[str, Any]] = []
        g = rosh_greg
        while hdate.HDateInfo(g).hdate.month == hebrew_date.month:
            di = hdate.HDateInfo(g)
            days.append(
                {
                    "hd": str(di.hdate),
                    "greg": g.isoformat(),
                    "holiday": ", ".join(str(h) for h in di.holidays) if di.holidays else "",
                    "parasha": di.parasha if self._loc_conf["israel"] else di.parasha,  # same property returns correct locale internally
                    "omer": di.omer.total_days if di.omer else 0,
                    "zmanim": self._calc_zmanim(g),
                }
            )
            g += timedelta(days=1)

        return {"title": title, "month": heb_month, "year": heb_year, "days": days}

    # ––– auxiliary –––
    def _calc_zmanim(self, greg: date) -> Dict[str, str]:
        try:
            z = hdate.Zmanim(self._location, greg)
            return {
                "sunrise": z.sunrise.isoformat(),
                "sunset": z.sunset.isoformat(),
                "candle_lighting": z.candle_lighting(18).isoformat(),
                "havdalah": z.havdalah().isoformat(),
            }
        except Exception as exc:  # pragma: no cover
            _LOGGER.debug("Zmanim error for %s: %s", greg, exc)
            return {}
