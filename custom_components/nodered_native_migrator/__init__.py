from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ALLOWED_MODES,
    CONF_DEFAULT_MODE,
    CONF_DEFAULT_OUTPUT_FILE,
    CONF_FILTER_DOMAIN,
    DATA_LAST_REPORT,
    DEFAULT_MODE,
    DEFAULT_OUTPUT_FILE,
    DOMAIN,
    SERVICE_BUILD_OVERVIEW,
    SERVICE_CONVERT_FLOW,
)
from .converter import convert_node_red_file, generate_overview_dashboard

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = {**entry.data, **entry.options}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = data

    async def _handle_convert(call: ServiceCall) -> None:
        filter_domain = call.data.get(CONF_FILTER_DOMAIN, data.get(CONF_FILTER_DOMAIN, ""))
        default_output = data.get(CONF_DEFAULT_OUTPUT_FILE, DEFAULT_OUTPUT_FILE)
        default_mode = data.get(CONF_DEFAULT_MODE, DEFAULT_MODE)

        nodered_file = call.data["nodered_file"]
        output_file = call.data.get("output_file", default_output)
        mode = call.data.get("mode", default_mode)

        try:
            result = await hass.async_add_executor_job(
                convert_node_red_file,
                nodered_file,
                output_file,
                mode,
                filter_domain or None,
            )
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Conversion failed: {err}") from err

        report = {
            "created": result.created,
            "skipped": result.skipped,
            "output_file": result.output_file,
            "integration_index_file": result.integration_index_file,
        }
        hass.data[DOMAIN][DATA_LAST_REPORT] = report

        _LOGGER.info("Node-RED migration completed: %s", report)

    async def _handle_dashboard(call: ServiceCall) -> None:
        report = hass.data[DOMAIN].get(DATA_LAST_REPORT, {})
        index_file = call.data.get("integration_index_file") or report.get("integration_index_file")
        output_file = call.data.get("output_file", "dashboards/nodered_migrated_overview.yaml")

        if not index_file:
            raise HomeAssistantError(
                "No integration index available. Run convert_flow_file first or pass integration_index_file."
            )

        try:
            dashboard_path = await hass.async_add_executor_job(
                generate_overview_dashboard,
                index_file,
                output_file,
            )
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Dashboard generation failed: {err}") from err

        _LOGGER.info("Dashboard YAML generated: %s", dashboard_path)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CONVERT_FLOW,
        _handle_convert,
        schema=vol.Schema(
            {
                vol.Required("nodered_file"): cv.string,
                vol.Optional("output_file"): cv.string,
                vol.Optional("mode", default=DEFAULT_MODE): vol.In(ALLOWED_MODES),
                vol.Optional(CONF_FILTER_DOMAIN, default=""): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_BUILD_OVERVIEW,
        _handle_dashboard,
        schema=vol.Schema(
            {
                vol.Optional("integration_index_file"): cv.string,
                vol.Optional("output_file", default="dashboards/nodered_migrated_overview.yaml"): cv.string,
            }
        ),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_CONVERT_FLOW)
        hass.services.async_remove(DOMAIN, SERVICE_BUILD_OVERVIEW)

    return True
