import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

POWER_POINT = "WH.OnOff"
BOOSTER_POINT = "PUB_WH.Booster"


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data["istore_heatpump"][entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]

    entities = [
        IStorePowerSwitch(coordinator, api),
        IStoreBoosterSwitch(coordinator, api),
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


class IStorePowerSwitch(BaseIStoreSwitch):
    control_point = POWER_POINT
    name_suffix = "Power"


class IStoreBoosterSwitch(BaseIStoreSwitch):
    control_point = BOOSTER_POINT
    name_suffix = "Booster"
