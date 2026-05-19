import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .api import iStoreApi


class CannotConnect(HomeAssistantError):
    """Error raised when API connection fails."""


class InvalidAuth(HomeAssistantError):
    """Error for invalid authentication."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            access_token = user_input["access_token"]
            parent_id = user_input["parent_id"]
            mdm_id = user_input["mdm_id"]

            api = iStoreApi(access_token, parent_id, mdm_id, self.hass)

            try:
                arch = await api.get_architecture()

                # Validate response format
                if "data" not in arch or parent_id not in arch["data"]:
                    raise InvalidAuth

                # Validate Res_WaterHeater exists
                objs = arch["data"][parent_id].get("mdmObjects", {})
                if "Res_WaterHeater" not in objs:
                    raise InvalidAuth

                # Validate mdm_id exists inside Res_WaterHeater
                mdm_list = objs["Res_WaterHeater"]
                found = any(obj.get("mdmId") == mdm_id for obj in mdm_list)

                if not found:
                    raise InvalidAuth

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as e:
                # Print full error to logs
                import logging
                logging.getLogger(__name__).error("Config flow error: %s", e)
                errors["base"] = "cannot_connect"

            if not errors:
                # Successfully validated
                return self.async_create_entry(
                    title="iStore Heat Pump",
                    data=user_input,
                )

        # Form schema
        data_schema = vol.Schema(
            {
                vol.Required("access_token"): str,
                vol.Required("parent_id"): str,
                vol.Required("mdm_id"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
