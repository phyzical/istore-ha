from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    async_add_entities([IStoreRunningBinarySensor(coordinator, api)], True)


class IStoreRunningBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for heat pump running state."""

    def __init__(self, coordinator, api):
        super().__init__(coordinator)
        self.api = api
        self._attr_name = "Running State"
        self._attr_unique_id = f"istore_{api.mdm_id}_running"

    @property
    def is_on(self):
        data = self.coordinator.data
        if not data:
            return False

        try:
            # CompressorStatus == 1 means running
            return data[self.api.mdm_id]["points"]["PUB_WH.CompressorStatus"]["value"] == 1
        except Exception:
            return False
