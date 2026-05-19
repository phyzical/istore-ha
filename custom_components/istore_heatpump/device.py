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
        model = "R290"
        serial_number = None
        
        # 1. Use arch_data (Asset Hierarchy) for Model & basic Name
        arch_data = getattr(self.api, "arch_data", None)
        if arch_data and "data" in arch_data:
            # Structure: data -> {parent_id} -> mdmObjects -> Res_WaterHeater -> [ list of devices ]
            struct = arch_data["data"]
            parent_id = self.api.parent_id
            
            if parent_id in struct:
                objects = struct[parent_id].get("mdmObjects", {})
                wh_list = objects.get("Res_WaterHeater", [])
                
                # Find device matching our mdm_id
                my_device = next((d for d in wh_list if d.get("mdmId") == self.api.mdm_id), None)
                
                if my_device:
                    attrs = my_device.get("attributes", {})
                    # 'modelId' e.g. "EnOS_RE_WH_Phnix_PRI_iStore"
                    if "modelId" in attrs:
                        model = attrs["modelId"]
                    # 'name' is often the SN initially
                    if "name" in attrs:
                        name = attrs["name"]

        # 2. Use attrib_data (Device Attributes) for Serial Number & Manufacturer Name
        attrib_data = getattr(self.api, "attrib_data", None)
        if attrib_data and "data" in attrib_data:
            # Structure: data -> {mdm_id} -> sn
            # The API response for attributes often returns data keyed by attribute name if we requested specifics, 
            # OR it returns a dict of `mdmId` -> attributes.
            # Based on typical usage, let's assume `data` is the dict. 
            # But wait, looking at user's step 41, `get_attributes` returns `resp.json()`.
            # We need to be careful about the structure. 
            # If the user has seen: `{"code": 10000, "data": { "vQEo839T": { "sn": "..." } } }`
            
            attr_struct = attrib_data["data"]
            mdm_id = self.api.mdm_id
            
            # Check if mdm_id is a key in data
            if mdm_id in attr_struct:
                device_attrs = attr_struct[mdm_id]
                if "sn" in device_attrs:
                    serial_number = device_attrs["sn"]

        return DeviceInfo(
            identifiers={(DOMAIN, self.api.mdm_id)},
            manufacturer=MANUFACTURER,
            name=name,
            model=model,
            serial_number=serial_number,
            via_device=None,
            connections={(CONNECTION_NETWORK_MAC, self.api.mdm_id)},
            configuration_url=CONFIG_PAGE,
        )
