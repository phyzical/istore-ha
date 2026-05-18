from homeassistant.helpers.entity import Entity
from .const import DOMAIN

class IStoreEntity(Entity):
    """Base class that links an entity to the heat pump device."""
    def __init__(self, hass, api, point):
        self.hass = hass
        self.api = api
        self.point = point

    @property
    def device_info(self):
        # the device object is stored per entry; we retrieve it here
        entry_id = self.hass.data[DOMAIN].get(self.api.mdm_id)
        if entry_id:
            return self.hass.data[DOMAIN][entry_id]["device"].device_info
        return None