from __future__ import annotations

import base64
import logging
import aiohttp

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

_LOGGER = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Authentication helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _get_public_key(session: aiohttp.ClientSession) -> tuple[str, str]:
    """Return (publicKey_b64, strategy) from the iStore public-key endpoint."""
    url = f"https://home.istore.net.au/hossain-bff/framework/v1.0/user/public-key"
    async with session.get(url) as resp:
        body = await resp.json(content_type=None)
        if body.get("code") != 0:
            raise Exception(f"public-key API error: {body}")
        data = body["data"]
        return data["publicKey"], data["strategy"]


def _encrypt_password(public_key_b64: str, password: str) -> str:
    """Encrypt password with the server's RSA public key.

    iStore uses RSA OAEP with SHA-256 for BOTH the main hash AND the MGF1 hash.
    """
    key_der = base64.b64decode(public_key_b64)
    public_key = serialization.load_der_public_key(key_der, backend=default_backend())
    encrypted = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")


async def _login(
    session: aiohttp.ClientSession, strategy: str, username: str, encrypted_password: str
) -> tuple[str, str]:
    """POST /user/login — returns (access_token, org_id)."""
    url = f"https://home.istore.net.au/hossain-bff/framework/v1.0/user/login"
    payload = {
        "strategy": strategy,
        "account": username,
        "password": encrypted_password,
    }
    async with session.post(url, json=payload) as resp:
        body = await resp.json(content_type=None)
        _LOGGER.debug("login response: %s", body)
        if body.get("code") != 0:
            raise Exception(f"login failed: {body.get('message', body)}")
        data = body["data"]
        access_token = data["accessToken"]
        org_id = data["organizations"][0]["id"]
        return access_token, org_id


async def _set_session(
    session: aiohttp.ClientSession, access_token: str, org_id: str
) -> str:
    """POST /user/set-session — returns companyId."""
    url = f"https://home.istore.net.au/hossain-bff/framework/v1.0/user/set-session"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with session.post(url, json={"orgId": org_id}, headers=headers) as resp:
        body = await resp.json(content_type=None)
        _LOGGER.debug("set-session response: %s", body)
        if body.get("code") != 0:
            raise Exception(f"set-session failed: {body.get('message', body)}")
        return body["data"]["companyId"]


async def _get_app_id(session: aiohttp.ClientSession, access_token: str) -> str:
    """GET /user/category/app/resource/list — extract appId for Univers_EMS in Smart Grid."""
    url = f"https://home.istore.net.au/app-portal/web/v1/user/category/app/resource/list?basicType=0"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with session.get(url, headers=headers) as resp:
        body = await resp.json(content_type=None)
        _LOGGER.debug("app/resource/list response: %s", body)
        # Note: This specific endpoint returns 200 for success, unlike others that return 0
        if body.get("code") not in (0, 200):
            raise Exception(f"app resource list failed: {body.get('message', body)}")

        categories = body["data"]["categories"]
        for cat in categories:
            if cat.get("name") == "Smart Grid":
                for app in cat.get("apps", []):
                    if app.get("code") == "Univers_EMS":
                        return app["id"]
        raise Exception("Could not find Univers_EMS app under Smart Grid category")


async def _get_site_id(
    session: aiohttp.ClientSession, access_token: str, app_id: str
) -> str:
    """POST /user/app/asset/tree — extract siteId for 'Istore home owner' device."""
    url = (
        f"https://home.istore.net.au/app-portal/web/v1/user/app/asset/tree"
        f"?appId={app_id}&needAssociateAsset=true&resourceTypes=all"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    async with session.post(url, data="null", headers=headers) as resp:
        body = await resp.json(content_type=None)
        _LOGGER.debug("asset/tree response: %s", body)
        if body.get("code") not in (0, 200):
            raise Exception(f"asset tree failed: {body.get('message', body)}")

        # $.data.children[?(@)].children[?(@.name=='Istore home owner')].children[?(@)].id
        for top_child in body["data"].get("children", []):
            for mid_child in top_child.get("children", []):
                if mid_child.get("name") == "Istore home owner":
                    for leaf in mid_child.get("children", []):
                        site_id = leaf.get("id")
                        if site_id:
                            return site_id
        raise Exception("Could not find site under 'Istore home owner'")


async def _get_device_id(
    session: aiohttp.ClientSession, access_token: str, site_id: str
) -> str:
    """POST /asset-hierarchy — extract mdmId for Res_WaterHeater under the given siteId."""
    url = f"https://home.istore.net.au/encompassbffservice/encompass-bff/asset-service/v1.0/asset-hierarchy"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = (
        f"mdmIds={site_id}&mdmTypes=Res_WaterHeater"
        "&attributes=name%2CmdmType&locale=en-US"
    )
    async with session.post(url, data=payload, headers=headers) as resp:
        body = await resp.json(content_type=None)
        _LOGGER.debug("asset-hierarchy response: %s", body)
        if body.get("code") != 10000:
            raise Exception(f"asset hierarchy failed: {body.get('msg', body)}")

        site_data = body["data"].get(site_id, {})
        wh_list = site_data.get("mdmObjects", {}).get("Res_WaterHeater", [])
        if not wh_list:
            raise Exception(f"No Res_WaterHeater device found under site {site_id}")
        return wh_list[0]["mdmId"]


# ──────────────────────────────────────────────────────────────────────────────
# Public auth entry-point
# ──────────────────────────────────────────────────────────────────────────────

async def authenticate(username: str, password: str) -> dict:
    """
    Full login flow.

    Returns a dict with keys:
        access_token, parent_id (siteId), mdm_id (device mdmId)
    """
    async with aiohttp.ClientSession() as session:
        # 1. get public key
        pub_key_b64, strategy = await _get_public_key(session)

        # 2. Encrypt password (PKCS#1 v1.5)
        encrypted_pw = _encrypt_password(pub_key_b64, password)

        # 3. Login
        access_token, org_id = await _login(session, strategy, username, encrypted_pw)

        # 4. Set session  (also validates org membership)
        await _set_session(session, access_token, org_id)

        # 5. Get App ID
        app_id = await _get_app_id(session, access_token)
        _LOGGER.debug("Univers_EMS appId: %s", app_id)

        # 6. Get site ID / parent ID
        parent_id = await _get_site_id(session, access_token, app_id)
        _LOGGER.debug("site_id (parent_id): %s", parent_id)

        # 7. Get device mdmId
        mdm_id = await _get_device_id(session, access_token, parent_id)
        _LOGGER.debug("device mdm_id: %s", mdm_id)

    return {
        "access_token": access_token,
        "parent_id": parent_id,
        "mdm_id": mdm_id,
    }


# ──────────────────────────────────────────────────────────────────────────────
# API client
# ──────────────────────────────────────────────────────────────────────────────

class iStoreApi:
    def __init__(self, username: str, password: str, access_token: str, parent_id: str, mdm_id: str, hass):
        self.username = username
        self.password = password
        self.access_token = access_token
        self.parent_id = parent_id
        self.mdm_id = mdm_id
        self.hass = hass

    async def re_authenticate(self):
        """Re-run the full auth flow and refresh stored credentials."""
        _LOGGER.info("iStore: re-authenticating…")
        creds = await authenticate(self.username, self.password)
        self.access_token = creds["access_token"]
        self.parent_id = creds["parent_id"]
        self.mdm_id = creds["mdm_id"]
        _LOGGER.info("iStore: re-authentication successful")

    # -------------------------------------------------------------------------
    # Asset hierarchy (used during config validation)
    # -------------------------------------------------------------------------
    async def get_architecture(self):
        url = (
            f"https://home.istore.net.au/encompassbffservice/encompass-bff/asset-service/v1.0/asset-hierarchy"
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
                return await resp.json(content_type=None)

                return await resp.json()

    # ---------------------------------------------------------
    # 2. Read device attributes (DeviceState,modelName,name,sn,manufacturerName,macCode)
    # ---------------------------------------------------------
    async def get_attributes(self):
        url = (
            "https://home.istore.net.au/encompassbffservice/"
            "encompass-bff/anti-timeseries/v1.0/attributes?"
            "attributes=DeviceState,modelName,name,sn,manufacturerName,macCode"
        )

        payload = {
            "withI18n": "true",
            "mdmIds": self.mdm_id,
            "locale": "en-US",
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload) as resp:
                text = await resp.text()
                _LOGGER.debug("ATTRIBUTES RESPONSE: %s", text)

                if resp.status != 200:
                    raise Exception(f"iStore attributes API failed: {resp.status}")

                return await resp.json()

    # ---------------------------------------------------------
    # 3. Read measurement points (temperatures, compressor, on/off)
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
            "PUB_WH.4WayStatus",
            "PUB_WH.FanSpeed",
            "PUB_WH.DefrostStatus",
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

                if resp.status == 401:
                    _LOGGER.warning("iStore 401 on measurements — re-authenticating")
                    await self.re_authenticate()
                    # Retry once with new token
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    async with session.post(url, headers=headers, data=payload) as retry:
                        if retry.status != 200:
                            _LOGGER.error("iStore measurement API returned %s after re-auth", retry.status)
                            return None
                        return await retry.json(content_type=None)

                if resp.status != 200:
                    _LOGGER.error("iStore measurement API returned %s", resp.status)
                    return None

                return await resp.json(content_type=None)

    # -------------------------------------------------------------------------
    # Control (On / Off / Booster)
    # -------------------------------------------------------------------------
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
                "value": value,
            }
        ]
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 401:
                    _LOGGER.warning("iStore 401 on control — re-authenticating")
                    await self.re_authenticate()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    async with session.post(url, headers=headers, json=payload) as retry:
                        return await retry.json(content_type=None)
                return await resp.json(content_type=None)


    async def update_asset_name(self, name):
        """Update the asset name on the iStore server."""
        url = "https://home.istore.net.au/hossain-bff/monitor/v1.0/asset/update"
        payload = {
            "assetId": self.mdm_id,
            "name": name
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                text = await resp.text()
                _LOGGER.debug("UPDATE NAME RESPONSE: %s", text)
                
                if resp.status != 200:
                    raise Exception(f"Failed to update asset name: {resp.status}")
                
                res_json = await resp.json()
                if res_json.get("code") not in [0, 10000]:
                    raise Exception(f"Update failed with code: {res_json.get('code')}")
                     
                return True
                

    async def set_points(self, points_dict):
        """
        Send multiple control points in one request.
        points_dict: { "ControlPointId": value, ... }
        """
        url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"
        
        payload = []
        for point, value in points_dict.items():
            payload.append({
                "assetId": self.mdm_id,
                "controlPointId": point,
                "value": value
            })
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                text = await resp.text()
                _LOGGER.debug("SET POINTS RESPONSE: %s", text)
                if resp.status != 200:
                     _LOGGER.error("Failed to set points: %s", text)
                return await resp.json()

    # -------------------------------------------------------------------------
    # Timer control
    # -------------------------------------------------------------------------
    async def set_timer(self, control_point: str, value):
        """Control a timer point (e.g. PRI_RE_WH.Timer1On)."""
        url = "https://home.istore.net.au/hossain-bff/connect/v1.0/device/control"
        payload = [
            {
                "assetId": self.mdm_id,
                "controlPointId": control_point,
                "value": value,
            }
        ]
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 401:
                    _LOGGER.warning("iStore 401 on timer control — re-authenticating")
                    await self.re_authenticate()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    async with session.post(url, headers=headers, json=payload) as retry:
                        return await retry.json(content_type=None)
                return await resp.json(content_type=None)
       

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
        
