from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
import logging

_LOGGER = logging.getLogger(__name__)

from .api import iStoreApi
from .coordinator import iStoreCoordinator
from .const import (DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_ACCESS_TOKEN, CONF_PARENT_ID, CONF_MDM_ID)

from .device import IStoreDevice
PLATFORMS = ["sensor", "switch", "binary_sensor", "text"]

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


    # Fetch device details (architecture) to populate DeviceInfo
    try:
        api.arch_data = await api.get_architecture()
    except Exception as e:
        _LOGGER.warning("Failed to fetch architecture for DeviceInfo: %s", e)
        api.arch_data = None

    # Fetch device details (attributes) to populate DeviceInfo
    try:
        api.attrib_data = await api.get_attributes()
        _LOGGER.info(f"[Init] attrib_data: {api.attrib_data}")
    except Exception as e:
        _LOGGER.warning("Failed to fetch attributes for DeviceInfo: %s", e)
        api.attrib_data = None
    
    # Create device helper and attach device_info to api so entities can access it
    istore_device = IStoreDevice(api)
    api.device_info = istore_device.device_info

    coordinator = iStoreCoordinator(hass, api)

    # First refresh
    await coordinator.async_config_entry_first_refresh()

    # Store data PROPERLY
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "device": istore_device,
    }

    # Load sensor + switch platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload iStore."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
