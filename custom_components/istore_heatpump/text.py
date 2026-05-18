from homeassistant.components.text import TextEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, TIMER_GROUPS
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up iStore text entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]

    entities = [IStoreDeviceNameText(coordinator, api)]
    
    # Timer 1
    entities.append(IStoreTimerText(coordinator, api, "timer1", "on"))
    entities.append(IStoreTimerText(coordinator, api, "timer1", "off"))
    
    # Timer 2
    entities.append(IStoreTimerText(coordinator, api, "timer2", "on"))
    entities.append(IStoreTimerText(coordinator, api, "timer2", "off"))

    async_add_entities(entities)


class IStoreDeviceNameText(CoordinatorEntity, TextEntity):
    """Representation of the iStore Device Name as an editable text entity."""

    def __init__(self, coordinator, api):
        super().__init__(coordinator)
        self.api = api
        self._attr_name = "Device Name"
        self._attr_unique_id = f"istore_{api.mdm_id}_device_name"
        self._attr_icon = "mdi:rename-box"
        self.entity_id = f"text.istore_{api.mdm_id}_name"
        self._local_value = None

    @property
    def native_value(self):
        """Return the value reported by the text entity."""
        if self._local_value is not None:
            return self._local_value
        
        # Get data from arch_data
        arch_data = getattr(self.api, "arch_data", None)
        if arch_data and "data" in arch_data:
            
            struct = arch_data["data"]
            parent_id = self.api.parent_id
            if parent_id in struct:
                objects = struct[parent_id].get("mdmObjects", {})
                wh_list = objects.get("Res_WaterHeater", [])
                my_device = next((d for d in wh_list if d.get("mdmId") == self.api.mdm_id), None)
                if my_device and "attributes" in my_device:
                    return my_device["attributes"].get("name")
        
        return None

    @property
    def device_info(self):
        return self.api.device_info

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        if not value:
            return

        try:
            # Update iStore
            await self.api.update_asset_name(value)
            self._local_value = value
            self.async_write_ha_state()

            # Update Device Registry
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get_device(identifiers={(DOMAIN, self.api.mdm_id)})
            if device:
                dev_reg.async_update_device(device.id, name=value)
            
            # Update local cache in api.arch_data
            arch_data = getattr(self.api, "arch_data", None)
            if arch_data and "data" in arch_data:
                struct = arch_data["data"]
                parent_id = self.api.parent_id
                if parent_id in struct:
                    objects = struct[parent_id].get("mdmObjects", {})
                    wh_list = objects.get("Res_WaterHeater", [])
                    my_device = next((d for d in wh_list if d.get("mdmId") == self.api.mdm_id), None)
                    if my_device and "attributes" in my_device:
                        my_device["attributes"]["name"] = value
            
        except Exception as e:
            _LOGGER.error("Failed to update device name: %s", e)
            raise
class IStoreTimerText(CoordinatorEntity, TextEntity):
    """Representation of an iStore Timer as a text entity (HH:MM)."""
    
    _attr_pattern = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"
    _attr_native_min = 5
    _attr_native_max = 5

    def __init__(self, coordinator, api, timer_key, time_type):
        """
        timer_key: "timer1" or "timer2"
        time_type: "on" or "off" (e.g. Timer1OnTime vs Timer1OffTime)
        """
        super().__init__(coordinator)
        self.api = api
        self.timer_key = timer_key
        self.time_type = time_type
        
        # Determine the specific key for this entity
        cls_group = TIMER_GROUPS[timer_key]
        if time_type == "on":
            self.control_point = cls_group["time_on"]
            name_suffix = "On"
        else:
            self.control_point = cls_group["time_off"]
            name_suffix = "Off"

        if timer_key == "timer1":
            timer_num = 1
        else:
            timer_num = 2

        self._attr_name = f"T{timer_num} {name_suffix}"
        
        # Unique ID - Use same logic as before but maybe ensure distinct from old TimeEntity?
        # Actually standard unique_id logic is fine based on control point.
        # But wait, TimeEntity used `istore_{api.mdm_id}_{safe_key}`.
        # If we use same unique_id, HA might get confused about type change.
        # It's safer to ensure it's treated as a new entity or we accept the migration (which might just fail until removed).
        
        safe_key = self.control_point.lower().replace(".", "_")
        self._attr_unique_id = f"istore_{api.mdm_id}_{safe_key}_text" 
        
        # Entity ID
        # safe_name = f"timer{timer_num}_{time_type}_time" # This was old default
        # If we change platform, we probably want `text.istore_timer1_on` etc.
        safe_name = f"timer{timer_num}_{time_type}"
        self.entity_id = f"text.istore_{safe_name}"

    @property
    def native_value(self) -> str | None:
        """Return the current time value as HH:MM string."""
        data = self.coordinator.data
        if not data:
            return None
            
        try:
            # Value comes in as "HH:MM" string
            val_str = data[self.api.mdm_id]["points"][self.control_point]["value"]
            if not val_str or ":" not in val_str:
                return None
            
            # Already in HH:MM format from API usually
            return str(val_str)
        except Exception:
            return None

    @property
    def device_info(self):
        return self.api.device_info

    async def async_set_value(self, value: str) -> None:
        """Update the time."""
        
        # Basic validation (regex handled by frontend but good to check)
        # We assume value is valid HH:MM
        
        # Gather all 4 values for this timer group
        group = TIMER_GROUPS[self.timer_key]
        data = self.coordinator.data[self.api.mdm_id]["points"]

        # Current values
        try:
            curr_switch_on = data[group["switch_on"]]["value"]
            curr_switch_off = data[group["switch_off"]]["value"]
            curr_time_on = data[group["time_on"]]["value"]
            curr_time_off = data[group["time_off"]]["value"]
        except KeyError:
            _LOGGER.error("Cannot set time, missing data in coordinator")
            return

        # Prepare payload dictionary
        payload = {
            group["switch_on"]: curr_switch_on,
            group["switch_off"]: curr_switch_off,
            group["time_on"]: curr_time_on,
            group["time_off"]: curr_time_off,
        }
        
        # Overwrite the one we are changing
        payload[self.control_point] = value
        
        _LOGGER.debug("Setting timer %s values (text): %s", self.timer_key, payload)
        
        # Send to API
        await self.api.set_points(payload)
        
        await asyncio.sleep(2) # Give it a moment
        await self.coordinator.async_request_refresh()
