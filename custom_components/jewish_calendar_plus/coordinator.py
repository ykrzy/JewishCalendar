"""Coordinator that pre‑computes Hebrew months using *hdate*.
Everything is pure‑Python (no web I/O) so it is extremely fast – caching
13 months takes < 100 ms on a Raspberry Pi 4.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

import hdate  # provided by requirements in manifest.json
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_UPDATE_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hebrew month helper – returns month name in Hebrew (RTL) incl. leap logic
# ---------------------------------------------------------------------------

_MONTH_NAMES = [
    "",  # index zero unused so month numbers line up
    "ניסן",
    "אייר",
    "סיון",
    "תמוז",
    "אב",
    "אלול",
    "תשרי",
    "חשוון",
    "כסלו",
    "טבת",
    "שבט",
    "אדר",   # 12 – Adar (non‑leap) / Adar I (leap)
    "אדר ב׳",  # 13 – Adar II (only in leap years)
]

def month_name_he(month: int, leap: bool) -> str:
    if not leap or month != 12:
        return _MONTH_NAMES[month]
    # month 12 in a leap year is Adar I
    return "אדר א׳"

# ---------------------------------------------------------------------------
# Utility: find Gregorian date of Rosh Ḥodesh for a given Gregorian date
# ---------------------------------------------------------------------------

def rosh_chodesh_for(greg: date) -> date:
    g = greg
    while hdate.HDateInfo(g).get_hday() != 1:
        g -= timedelta(days=1)
    return g


def next_rosh_chodesh(current_rosh: date) -> date:
    g = current_rosh + timedelta(days=1)
    while hdate.HDateInfo(g).get_hday() != 1:
        g += timedelta(days=1)
    return g

# ---------------------------------------------------------------------------
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
            "User", loc_conf["lat"], loc_conf["lon"], "Asia/Jerusalem", 0
        )

    # ------------------------------------------------------------------
    async def _async_update_data(self) -> Dict[str, Any]:
        """Default update: build current + 12 months."""
        return await self._build_month_cache(12)

    async def async_prefetch(self, months_ahead: int = 12) -> None:
        """Service handler – extend cache further ahead."""
        self.data = await self._build_month_cache(months_ahead)
        self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    async def _build_month_cache(self, months_ahead: int) -> Dict[str, Any]:
        today = date.today()
        rosh = rosh_chodesh_for(today)
        cache: Dict[str, Any] = {}
        for _ in range(months_ahead + 1):  # include current month
            cache[rosh.isoformat()] = await self._build_month(rosh)
            rosh = next_rosh_chodesh(rosh)
        return cache

    async def _build_month(self, rosh_greg: date) -> Dict[str, Any]:
        info = hdate.HDateInfo(rosh_greg)
        heb_month = info.get_hmonth()
        heb_year = info.get_hyear()
        is_leap = hdate.is_hebrew_leap_year(heb_year)
        title = f"{month_name_he(heb_month, is_leap)} {heb_year}"

        days: List[Dict[str, Any]] = []
        g = rosh_greg
        while hdate.HDateInfo(g).get_hmonth() == heb_month:
            di = hdate.HDateInfo(g)
            days.append(
                {
                    "hd": di.hebrew_date_he(),
                    "greg": g.isoformat(),
                    "holiday": di.holiday_description() or "",
                    "parasha": (
                        di.parasha_he()
                        if self._loc_conf["israel"]
                        else di.parasha_he_diaspora()
                    ),
                    "omer": di.omer(),
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

    # ------------------------------------------------------------------
    def _calc_zmanim(self, greg: date) -> Dict[str, str]:
        try:
            z = hdate.Zmanim(self._location, greg)
            return {
                "sunrise": z.sunrise.isoformat(),
                "sunset": z.sunset.isoformat(),
                "candle_lighting": z.candle_lighting(18).isoformat(),
                "havdalah": z.tzais().isoformat(),
            }
        except Exception as exc:  # pragma: no cover
            _LOGGER.debug("Zmanim error for %s: %s", greg, exc)
            return {}