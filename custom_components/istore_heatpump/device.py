from homeassistant.helpers.device_registry import DeviceInfo, CONNECTION_NETWORK_MAC
from .const import DOMAIN, MANUFACTURER, CONFIG_PAGE

class IStoreDevice:
    """Simple wrapper that returns DeviceInfo for the heat pump."""
    def __init__(self, api, name: str = None):
        self.api = api
        self.name = name or "iStore Heat Pump"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        # Default values
        name = self.name
        model = None
        serial_number = None
        
        # 1. Use arch_data (Asset Hierarchy) for Model & basic Name
        arch_data = getattr(self.api, "arch_data", None)
        if arch_data and "data" in arch_data:

            struct = arch_data["data"]
            parent_id = self.api.parent_id
            
            if parent_id in struct:
                objects = struct[parent_id].get("mdmObjects", {})
                wh_list = objects.get("Res_WaterHeater", [])
                
                # Find device matching our mdm_id
                my_device = next((d for d in wh_list if d.get("mdmId") == self.api.mdm_id), None)
                
                if my_device:
                    attrs = my_device.get("attributes", {})
                    model = attrs.get("modelId", model)
                    name = attrs.get("name", name)

        # 2. Use attrib_data (Device Attributes) for Serial Number & Manufacturer Name
        attrib_data = getattr(self.api, "attrib_data", None)
        if attrib_data and "data" in attrib_data:

            attr_struct = attrib_data["data"]
            mdm_id = self.api.mdm_id
            
            if mdm_id in attr_struct:
                device_attrs = attr_struct[mdm_id]
                serial_number = device_attrs.get("sn", serial_number)

        return DeviceInfo(
            identifiers={(DOMAIN, self.api.mdm_id)},
            manufacturer=MANUFACTURER,
            name=name,
            model=model,
            serial_number=serial_number,
            via_device=None,
            configuration_url=CONFIG_PAGE,
        )
