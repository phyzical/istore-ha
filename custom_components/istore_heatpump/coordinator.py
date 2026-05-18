from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class iStoreCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        self.api = api

        super().__init__(
            hass,
            _LOGGER,
            name="iStore Heat Pump",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        """Fetch latest data from iStore API."""
        try:
            data = await self.api.get_measurements()
            return data["data"]  # the dict keyed by mdm_id
        except Exception as e:
            _LOGGER.error("iStore update failed: %s", e)
            raise
