DOMAIN = "istore_heatpump"
MANUFACTURER = "iStore"
CONFIG_PAGE = "https://home.istore.net.au/"

TIMER_GROUPS = {
    "timer1": {
        "switch_on": "PRI_RE_WH.Timer1On",
        "switch_off": "PRI_RE_WH.Timer1Off",
        "time_on": "PRI_RE_WH.Timer1OnTime",
        "time_off": "PRI_RE_WH.Timer1OffTime",
    },
    "timer2": {
        "switch_on": "PRI_RE_WH.Timer2On",
        "switch_off": "PRI_RE_WH.Timer2Off",
        "time_on": "PRI_RE_WH.Timer2OnTime",
        "time_off": "PRI_RE_WH.Timer2OffTime",
    }
}
