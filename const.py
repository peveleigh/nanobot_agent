"""Constants for the nanobot integration."""

DOMAIN = "nanobot_agent"

# Configuration keys (match config_flow + configuration.yaml)
CONF_WEBHOOK_ID = "webhook_id"
CONF_NANOBOT_URL = "nanobot_url"          # e.g. http://nanobot-host:8080/ha/inbound
CONF_AGENT_NAME = "agent_name"
CONF_REQUEST_TIMEOUT = "request_timeout"

# Defaults
DEFAULT_AGENT_NAME = "Nanobot"
DEFAULT_TIMEOUT = 30

# Hass data keys
DATA_CLIENT = "client"           # NanobotClient instance
DATA_CALLBACK_URL = "cb_url"     # nanobot → HA callback URL stored after registration
