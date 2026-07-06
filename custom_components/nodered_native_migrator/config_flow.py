from __future__ import annotations

from homeassistant import config_entries

from .const import (
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
