from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .api import iStoreApi
from .coordinator import iStoreCoordinator
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up iStore Heat Pump."""

    access_token = entry.data["access_token"]
    parent_id = entry.data["parent_id"]
    mdm_id = entry.data["mdm_id"]

    api = iStoreApi(access_token, parent_id, mdm_id, hass)
    coordinator = iStoreCoordinator(hass, api)

    # First refresh
    await coordinator.async_config_entry_first_refresh()

    # Store data PROPERLY
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # Load sensor + switch platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "switch", "binary_sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload iStore."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "switch", "binary_sensor"])

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
