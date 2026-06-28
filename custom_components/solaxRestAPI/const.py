"""Constants for the SolaX REST API integration."""

from homeassistant.const import Platform

DOMAIN = "solaxRestAPI"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAPPING_FILE = "mapping_file"
CONF_ENTITY_SOURCES = "entity_sources"

DEFAULT_PASSWORD = "SRCSKCLBHB"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_MAPPING_FILE = "solax_type4"

MIN_SCAN_INTERVAL = 5

PLATFORMS: list[Platform] = [Platform.SENSOR]
