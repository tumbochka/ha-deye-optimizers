"""Constants for the Deye Cloud Optimizers integration."""

from datetime import timedelta

DOMAIN = "deye_optimizers"

CONF_PASSWORD_HASH = "password_hash"
CONF_DATA_CENTER = "data_center"
CONF_TOKEN = "token"

# deyecloud.com data centers, as used by the web app's "switch_org" step.
DATA_CENTERS = ["eu", "am", "india"]
DEFAULT_DATA_CENTER = "eu"

BASE_URL = "https://www.deyecloud.com"
CLIENT_ID = "test"  # the client id the deyecloud.com web app itself uses

SCAN_INTERVAL = timedelta(minutes=5)

DEVICE_TYPE_OPTIMIZER = "OPTIMIZER"
DEVICE_TYPE_CONCENTRATOR = "OPTIMIZER_CONCENTRATOR"
