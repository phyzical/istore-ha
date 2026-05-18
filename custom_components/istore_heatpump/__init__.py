from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .api import iStoreApi
from .coordinator import iStoreCoordinator
from .const import (DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN, CONF_PARENT_ID, CONF_MDM_ID)

PLATFORMS = ["sensor", "switch", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up iStore Heat Pump from a config entry."""

    api = iStoreApi(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        access_token=entry.data[CONF_ACCESS_TOKEN],
        parent_id=entry.data[CONF_PARENT_ID],
        mdm_id=entry.data[CONF_MDM_ID],
        hass=hass,
    )

    coordinator = iStoreCoordinator(hass, api)

    # First refresh — raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload iStore Heat Pump config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
