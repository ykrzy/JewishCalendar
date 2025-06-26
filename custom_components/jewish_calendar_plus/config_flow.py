# file: config_flow.py 
"""Config flow for Jewish Calendar Plus integration."""

from __future__ import annotations
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import DOMAIN, CONF_ISRAEL

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_LATITUDE): vol.Coerce(float),
    vol.Required(CONF_LONGITUDE): vol.Coerce(float),
    vol.Required(CONF_ISRAEL, default=True): bool,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Use HA’s configured time zone
            user_input["time_zone"] = str(self.hass.config.time_zone)
            return self.async_create_entry(title="Jewish Calendar Plus", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
        )