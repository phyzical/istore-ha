# iStore Heat Pump – Home Assistant Custom Integration

A Home Assistant custom integration for iStore Hot Water System (R290).
Provides full monitoring + control using the official iStore API. This integration can only be used with the iStore Heat Pumps system that has already fitted in the wifi module, and able to connect with the Univers EMS mobile app. Most iStore Hot Water System that installed posted November 2025 should comes with the wifi module.

### Sample of Home Assistant Dashboard

<img src="images/dashboard.png" height="400">

## Features

### Live Monitoring

- Top temperature  
- Bottom temperature  
- Target temperature  
- TargetMin & TargetMax  
- Ambient / Coil / Suction temperature  
- Compressor status  
- System running state  
- Booster state  
- Work mode (Eco / Boost / Hybrid / etc.)  
- Timer 1 and Timer 2 schedules  
  - Enabled / disabled  
  - On / Off time  

---

## Full Control

- Power ON/OFF  
- Booster ON/OFF  
- Set Target Temperature  (must be between min and max temperature)
- Set Min/Max Temperature  (10-75 degrees)

---

## Installation

### HACS Install (Custom Repository)

1. Open HACS in Home Assistant.
2. Go to Integrations, then click the 3-dot menu and select Custom repositories.
3. Add this repository URL and set category to Integration.
4. Search for iStore Heat Pump in HACS and install it.
5. Restart Home Assistant.
6. Go to Settings -> Devices & Services -> Add Integration -> iStore Heat Pump.

### Manual Install

1. Copy the **custom_components/istore_heatpump** folder from this repository into:
/config/custom_components/istore_heatpump/

2. Restart Home Assistant

3. Go to:
Settings → Devices & Services → Add Integration → “iStore Heat Pump”

---

## Configuration

The integration requires 3 inputs:

| Field        | Description                                          |
| ------------ | ---------------------------------------------------- |
| access_token | From browser Network tab (`Bearer APP_PORTAL_S_...`) |
| parent_id    | From asset-hierarchy API (`parentId`)                |
| mdm_id       | Device ID (`mdmId`, e.g. J8PqiKt2)                   |

To acquire the above parameters, please follow the following steps:

1. Open a desktop web browser (eg. Google Chrome) and open the URL <https://home.istore.net.au/>

2. Right click on the web page (any white space), then click "Inspect", this opens the Developer Console

3. Go to "Network" tab in the Developer Console, then check the "Preserve log" box
![Step 3](images/step3.png)

4. Login using the same credential as the Univers EMS mobile app where you have setup to control the iStore R290 hot water system

5. After login to iStore, navigate to "Device Monitoring" on the left menu, the click on "Device Type" drop down, and choose "Water Heater"
![Step 5](images/step5.png)

6. Find the "asset-hierarchy" in the list below (in the Network tab of Developer Console) and click on it. Then select the "Response" tab on the right. Check on the json data where it should has "Res_WaterHeater", and under attributes, there's "mdmId" and "parentId". These are the mdm_id and parent_id. Note: if the asset-hierarchy doesn't have the mdmId and parentId, just refresh the web page and try again.
![Step 6](images/step6.png)

7. Click on "Application" tab on the top of the Developer Console, then expand "Local storage" -> "<https://home.istore.net.au>", and find the "access_token_key" on the right hand side list, the key should looks like APP_PORTAL_X_XXXXXXXXXX, this is the access_token.
![Step 7](images/step7.png)

### Please do not log out from iStore website, you can simply close the web page / web browser. If you log out, the access token will no longer be valid

1. After acquire all the 3 parameters, you can now "Add Integration" in Home Assistant and add the iStore Heat Pump custom component using the 3 parameters.
![Step 8](images/step8.png)

---

## Sensors

| Entity                               | API Point               | Description                          |
| ------------------------------------ | ----------------------- | ------------------------------------ |
| sensor.istore_top_temperature        | WH.TopTemp              | Tank top temperature                 |
| sensor.istore_bottom_temperature     | WH.BottomTemp           | Tank bottom temperature              |
| sensor.istore_target_temperature     | WH.TargetTemp           | Current target temperature           |
| sensor.istore_target_temperature_min | WH.TargetTempMin        | Minimum target limit                 |
| sensor.istore_target_temperature_max | WH.TargetTempMax        | Maximum target limit                 |
| sensor.istore_ambient_temperature    | PUB_WH.EnvirTemp        | Ambient temperature                  |
| sensor.istore_coil_temperature       | PUB_WH.CoilTemp         | Coil temperature                     |
| sensor.istore_suction_temperature    | PUB_WH.SuctionTemp      | Suction temperature                  |
| sensor.istore_compressor_status      | PUB_WH.CompressorStatus | Compressor on/off                    |
| sensor.istore_booster_state          | PUB_WH.Booster          | Booster state (1=On, 2=Off)          |
| sensor.istore_work_mode              | PUB_WH.WorkMode         | Work mode (Eco, Boost, Hybrid, etc.) |
| sensor.istore_timer1_on              | PRI_RE_WH.Timer1On      | Timer 1 enabled                      |
| sensor.istore_timer1_on_time         | PRI_RE_WH.Timer1OnTime  | Timer 1 ON time                      |
| sensor.istore_timer1_off             | PRI_RE_WH.Timer1Off     | Timer 1 disabled                     |
| sensor.istore_timer1_off_time        | PRI_RE_WH.Timer1OffTime | Timer 1 OFF time                     |
| sensor.istore_timer2_on              | PRI_RE_WH.Timer2On      | Timer 2 enabled                      |
| sensor.istore_timer2_on_time         | PRI_RE_WH.Timer2OnTime  | Timer 2 ON time                      |
| sensor.istore_timer2_off             | PRI_RE_WH.Timer2Off     | Timer 2 disabled                     |
| sensor.istore_timer2_off_time        | PRI_RE_WH.Timer2OffTime | Timer 2 OFF time                     |

---

## Notes

- Since this is using iStore API to control the hot water system, it will take up to 15 seconds for any changes (eg. On/Off, change temperature, Booster etc.)
- Sensor data are updated every 30 seconds
- It use the same access token, so make sure you do not "logout" the web page where you acquire the access token. However, you can safely just close the browser or web page without logging out. The access token will not expire as long as you dont actively logout the session that you originally acquire the access token.

---

## Disclaimer

This is a community-built integration and is not affiliated with iStore.
Use at your own risk.
