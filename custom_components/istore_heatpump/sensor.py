from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSORS = {
    "work_mode": ("PUB_WH.WorkMode", None),
    "top_temperature": ("WH.TopTemp", "°C"),
    "bottom_temperature": ("WH.BottomTemp", "°C"),
    "target_temperature": ("WH.TargetTemp", "°C"),
    "target_temp_min": ("WH.TargetTempMin", "°C"),
    "target_temp_max": ("WH.TargetTempMax", "°C"),

    "ambient_temperature": ("PUB_WH.EnvirTemp", "°C"),
    "coil_temperature": ("PUB_WH.CoilTemp", "°C"),
    "suction_temperature": ("PUB_WH.SuctionTemp", "°C"),
    "compressor_status": ("PUB_WH.CompressorStatus", None),
    "mode": ("WH.OnOff", None),
    "running_state": ("WH.OnOff", None),
    "booster": ("PUB_WH.Booster", None),
    "timer1_on_time": ("PRI_RE_WH.Timer1OnTime", None),
    "timer1_off_time": ("PRI_RE_WH.Timer1OffTime", None),
    "timer1_on_enabled": ("PRI_RE_WH.Timer1On", None),
    "timer1_off_enabled": ("PRI_RE_WH.Timer1Off", None),

    "timer2_on_time": ("PRI_RE_WH.Timer2OnTime", None),
    "timer2_off_time": ("PRI_RE_WH.Timer2OffTime", None),
    "timer2_on_enabled": ("PRI_RE_WH.Timer2On", None),
    "timer2_off_enabled": ("PRI_RE_WH.Timer2Off", None),

    "target_temp_min": ("WH.TargetTempMin", "°C"),
    "target_temp_max": ("WH.TargetTempMax", "°C"),

    "work_mode": ("PUB_WH.WorkMode", None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up iStore sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = [
        IStoreSensor(coordinator, api, point, name, unit)
        for name, (point, unit) in SENSORS.items()
    ]
    async_add_entities(entities, update_before_add=True)


class IStoreSensor(CoordinatorEntity, SensorEntity):
    """Representation of a single iStore sensor point."""

    def __init__(self, coordinator, api, key, name, unit):
        super().__init__(coordinator)
        self.api = api
        self.key = key

        # Display name in UI
        self._attr_name = name.replace("_", " ").title()

        # Unit
        self._attr_native_unit_of_measurement = unit

        # --- FIX: UNIQUE ID MUST DIFFER EVEN IF SAME KEY ---
        safe_key = key.lower().replace(".", "_")
        safe_name = name.lower()
        self._attr_unique_id = f"istore_{api.mdm_id}_{safe_name}_{safe_key}"

        # Keep your custom entity_id
        self.entity_id = f"sensor.istore_{safe_name}"
        
    @property
    def device_info(self):
        return self.api.device_info

    @property
    def native_value(self):
        """Return the current sensor value."""
        data = self.coordinator.data
        if not data:
            return None

        try:
            value = data[self.api.mdm_id]["points"][self.key]["value"]
        except Exception:
            return None

        # Convert sensor status values to strings
        if self._attr_name.lower() == "booster":
            if value == 1:
                return "On"
            elif value == 2:
                return "Off"
            else:
                return "Unknown"

        if self._attr_name.lower() == "work mode":
            if value == 0:
                return "Standby"
            elif value == 1:
                return "Heating"
            elif value == 2:
                return "Eco"
            elif value == 3:
                return "Hybrid"
            elif value == 4:
                return "Boost"
            else:
                return value   # fallback for unknown values

        return value