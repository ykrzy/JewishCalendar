"""Config flow for Jewish Calendar Plus integration."""
from __future__ import annotations
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_TIME_ZONE
from homeassistant.core import callback

from .const import DOMAIN, CONF_ISRAEL

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LATITUDE): vol.Coerce(float),
        vol.Required(CONF_LONGITUDE): vol.Coerce(float),
        vol.Required(CONF_TIME_ZONE): str,
        vol.Required(CONF_ISRAEL, default=True): bool,
    }
)

class JewishCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Jewish Calendar Plus", data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
