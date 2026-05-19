from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

from .const import (DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN, CONF_PARENT_ID, CONF_MDM_ID)
from .api import authenticate

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error raised when API connection fails."""


class InvalidAuth(HomeAssistantError):
    """Error for invalid authentication."""


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                creds = await authenticate(username, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as exc:
                _LOGGER.error("iStore config flow error: %s", exc)
                # Try to give a nicer error for auth failures vs connectivity
                msg = str(exc).lower()
                if "login failed" in msg or "invalid" in msg or "401" in msg:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            else:
                # Persist username, password, and discovered IDs
                return self.async_create_entry(
                    title="iStore Heat Pump",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_ACCESS_TOKEN: creds["access_token"],
                        CONF_PARENT_ID: creds["parent_id"],
                        CONF_MDM_ID: creds["mdm_id"],
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
