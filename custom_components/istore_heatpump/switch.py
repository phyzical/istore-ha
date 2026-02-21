import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import TIMER_GROUPS
import logging

_LOGGER = logging.getLogger(__name__)

POWER_POINT = "WH.OnOff"
BOOSTER_POINT = "PUB_WH.Booster"


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data["istore_heatpump"][entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]

    entities = [
        IStorePowerSwitch(coordinator, api),
        IStoreBoosterSwitch(coordinator, api),
        IStoreTimerSwitch(coordinator, api, "timer1"),
        IStoreTimerSwitch(coordinator, api, "timer2"),
    ]

    async_add_entities(entities)


class BaseIStoreSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for iStore switches."""

    control_point = None  # override
    name_suffix = None    # override

    def __init__(self, coordinator, api):
        super().__init__(coordinator)
        self.api = api
        self._attr_name = f"iStore {self.name_suffix}"
        safe_key = self.control_point.lower().replace(".", "_")
        self._attr_unique_id = f"istore_{api.mdm_id}_{safe_key}"

        # Force sensor ID to be nicer
        safe_name = self.name_suffix.lower().replace(" ", "_")
        self.entity_id = f"switch.istore_{safe_name}"

    @property
    def is_on(self):
        """Check if switch is ON based on coordinator data."""
        data = self.coordinator.data
        if not data:
            return None

        try:
            value = data[self.api.mdm_id]["points"][self.control_point]["value"]

            # POWER (0/1)
            if self.control_point == POWER_POINT:
                return value == 1

            # BOOSTER (1=ON, 2=OFF)
            if self.control_point == BOOSTER_POINT:
                return value == 1

        except Exception:
            return None

    async def async_turn_on(self):
        """Turn switch on."""
        if self.control_point == POWER_POINT:
            await self.api.set_onoff("Power", 1)
        elif self.control_point == BOOSTER_POINT:
            await self.api.set_onoff("Booster", 1)

        await asyncio.sleep(12)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        """Turn switch off."""
        if self.control_point == POWER_POINT:
            await self.api.set_onoff("Power", 0)
        elif self.control_point == BOOSTER_POINT:
            await self.api.set_onoff("Booster", 2)

        await asyncio.sleep(12)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return self.api.device_info


class IStorePowerSwitch(BaseIStoreSwitch):
    control_point = POWER_POINT
    name_suffix = "Power"


class IStoreBoosterSwitch(BaseIStoreSwitch):
    control_point = BOOSTER_POINT
    name_suffix = "Booster"


class IStoreTimerSwitch(BaseIStoreSwitch):
    def __init__(self, coordinator, api, timer_key):
        self.timer_key = timer_key
        
        # Override what BaseIStoreSwitch set
        if timer_key == "timer1":
            self.control_point = TIMER_GROUPS["timer1"]["switch_on"] # Primary point for state check
            self.name_suffix = "Timer 1"
        else:
            self.control_point = TIMER_GROUPS["timer2"]["switch_on"]
            self.name_suffix = "Timer 2"
        
        super().__init__(coordinator, api)

        self._attr_name = f"iStore {self.name_suffix}"
        
        # Calculate safe unique_id
        safe_key = self.control_point.lower().replace(".", "_")
        self._attr_unique_id = f"istore_{api.mdm_id}_{safe_key}_switch"

    @property
    def is_on(self):
        """Check if switch is ON."""
        data = self.coordinator.data
        if not data:
            return None
        try:
            # We use the 'switch_on' point as the representative state
            value = data[self.api.mdm_id]["points"][self.control_point]["value"]
            return value == 1
        except Exception:
            return None

    async def async_turn_on(self):
        await self._set_state(1)

    async def async_turn_off(self):
        await self._set_state(0)

    async def _set_state(self, value):
        """value: 1 (on) or 0 (off)"""
        group = TIMER_GROUPS[self.timer_key]
        data = self.coordinator.data[self.api.mdm_id]["points"]

        try:
            curr_time_on = data[group["time_on"]]["value"]
            curr_time_off = data[group["time_off"]]["value"]
        except KeyError:
             _LOGGER.error("Cannot toggle timer, missing data")
             return

        # We set BOTH switch_on and switch_off to the new value (0 or 1)
        # And we re-send the times.
        payload = {
            group["switch_on"]: value,
            group["switch_off"]: value,
            group["time_on"]: curr_time_on,
            group["time_off"]: curr_time_off,
        }

        _LOGGER.debug(f"Setting {self.timer_key} switch to {value}, payload: {payload}")
        await self.api.set_points(payload)
        
        await asyncio.sleep(12)
        await self.coordinator.async_request_refresh()
