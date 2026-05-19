import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)


class iStoreApi:
    def __init__(self, access_token, parent_id, mdm_id, hass):
        self.access_token = access_token
        self.parent_id = parent_id
        self.mdm_id = mdm_id
        self.hass = hass

    # ---------------------------------------------------------
    # 1. Validate parent_id and mdm_id (Asset Hierarchy API)
    # ---------------------------------------------------------
    async def get_architecture(self):
        url = (
            "https://home.istore.net.au/encompassbffservice/"
            "encompass-bff/asset-service/v1.0/asset-hierarchy"
        )

        payload = {
            "mdmIds": self.parent_id,
            "mdmTypes": "Res_WaterHeater",
            "attributes": "name,mdmType",
            "locale": "en-US",
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload) as resp:
                text = await resp.text()
                _LOGGER.debug("ARCHITECTURE RESPONSE: %s", text)

                if resp.status != 200:
                    raise Exception(f"iStore hierarchy API failed: {resp.status}")

                return await resp.json()

    # ---------------------------------------------------------
    # 2. Read measurement points (temperatures, compressor, on/off)
    # ---------------------------------------------------------
    async def get_measurements(self):
        url = (
            "https://home.istore.net.au/encompassbffservice/"
            "encompass-bff/anti-timeseries/v1.0/measurement-points"
        )

        POINTS = [
            "WH.OnOff",
            "WH.TargetTemp",
            "WH.TopTemp",
            "WH.BottomTemp",
            "PUB_WH.CompressorStatus",
            "PUB_WH.EnvirTemp",
            "PUB_WH.SuctionTemp",
            "PUB_WH.CoilTemp",
            "PUB_WH.Booster",
            "PRI_RE_WH.Timer1On",
            "PRI_RE_WH.Timer1OnTime",
            "PRI_RE_WH.Timer1Off",
            "PRI_RE_WH.Timer1OffTime",
            "PRI_RE_WH.Timer2On",
            "PRI_RE_WH.Timer2OnTime",
            "PRI_RE_WH.Timer2Off",
            "PRI_RE_WH.Timer2OffTime",
            "PUB_WH.WorkMode",
            "WH.TargetTempMin",
            "WH.TargetTempMax",
        ]

        payload = f"mdmIds={self.mdm_id}&pointIds=" + ",".join(POINTS)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload) as resp:
                text = await resp.text()
                _LOGGER.debug("MEASUREMENTS RESPONSE: %s", text)

                if resp.status != 200:
                    _LOGGER.error("iStore measurement API returned %s", resp.status)
                    return None

                return await resp.json()

    # ---------------------------------------------------------
    # 3. Control (On / Off)
    # ---------------------------------------------------------
    async def set_onoff(self, point, value):
        """Control WH.OnOff or PUB_WH.Booster."""
        url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"

        if point == "Power":
            control_point = "WH.OnOff"
        elif point == "Booster":
            control_point = "PUB_WH.Booster"
        else:
            return

        payload = [
            {
                "assetId": self.mdm_id,
                "controlPointId": control_point,
                "value": value
            }
        ]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                return await resp.json()



    # async def set_target_temperature(self, value):
    #     url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"
    #     headers = {
    #         "Authorization": f"Bearer {self.access_token}",
    #         "Content-Type": "application/json",
    #     }
    #     payload = [
    #         {
    #             "assetId": self.mdm_id,
    #             "controlPointId": "WH.TargetTemp",
    #             "value": value
    #         }
    #     ]

    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(url, headers=headers, json=payload) as resp:
    #             return await resp.json()



    # async def set_target_min(self, value):
    #     url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"
    #     headers = {
    #         "Authorization": f"Bearer {self.access_token}",
    #         "Content-Type": "application/json",
    #     }
    #     payload = [
    #         {
    #             "assetId": self.mdm_id,
    #             "controlPointId": "WH.TargetTempMin",
    #             "value": value
    #         }
    #     ]

    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(url, headers=headers, json=payload) as resp:
    #             return await resp.json()



    # async def set_target_max(self, value):
    #     url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"
    #     headers = {
    #         "Authorization": f"Bearer {self.access_token}",
    #         "Content-Type": "application/json",
    #     }
    #     payload = [
    #         {
    #             "assetId": self.mdm_id,
    #             "controlPointId": "WH.TargetTempMax",
    #             "value": value
    #         }
    #     ]

    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(url, headers=headers, json=payload) as resp:
    #             return await resp.json()




    
