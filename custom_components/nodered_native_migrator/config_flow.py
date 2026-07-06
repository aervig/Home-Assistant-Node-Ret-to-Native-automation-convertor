from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    ALLOWED_MODES,
    CONF_DEFAULT_MODE,
    CONF_DEFAULT_OUTPUT_FILE,
    CONF_FILTER_DOMAIN,
    DEFAULT_MODE,
    DEFAULT_OUTPUT_FILE,
    DOMAIN,
)


class NodeRedNativeMigratorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        defaults = {
            CONF_FILTER_DOMAIN: "",
            CONF_DEFAULT_OUTPUT_FILE: DEFAULT_OUTPUT_FILE,
            CONF_DEFAULT_MODE: DEFAULT_MODE,
        }
        return self.async_create_entry(title="Node-RED Native Migrator", data=defaults)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NodeRedNativeMigratorOptionsFlow(config_entry)


class NodeRedNativeMigratorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FILTER_DOMAIN,
                    default=self._config_entry.options.get(
                        CONF_FILTER_DOMAIN,
                        self._config_entry.data.get(CONF_FILTER_DOMAIN, ""),
                    ),
                ): cv.string,
                vol.Optional(
                    CONF_DEFAULT_OUTPUT_FILE,
                    default=self._config_entry.options.get(
                        CONF_DEFAULT_OUTPUT_FILE,
                        self._config_entry.data.get(CONF_DEFAULT_OUTPUT_FILE, DEFAULT_OUTPUT_FILE),
                    ),
                ): cv.string,
                vol.Optional(
                    CONF_DEFAULT_MODE,
                    default=self._config_entry.options.get(
                        CONF_DEFAULT_MODE,
                        self._config_entry.data.get(CONF_DEFAULT_MODE, DEFAULT_MODE),
                    ),
                ): vol.In(ALLOWED_MODES),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
