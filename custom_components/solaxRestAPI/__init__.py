"""The SolaX REST API integration."""

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.config_entries import ConfigEntry

from .api import SolaXRestAPIClient
from .const import CONF_MAPPING_FILE, DEFAULT_MAPPING_FILE, PLATFORMS
from .coordinator import SolaXRestAPIConfigEntry, SolaXRestAPIDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: SolaXRestAPIConfigEntry) -> bool:
    """Set up SolaX REST API from a config entry."""
    mapping_file = entry.options.get(
        CONF_MAPPING_FILE,
        entry.data.get(CONF_MAPPING_FILE, DEFAULT_MAPPING_FILE),
    )
    client = SolaXRestAPIClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PASSWORD],
    )
    coordinator = SolaXRestAPIDataUpdateCoordinator(hass, entry, client, mapping_file)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolaXRestAPIConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, object]:
    """Return diagnostic data for the integration."""
    coordinator: SolaXRestAPIDataUpdateCoordinator = entry.runtime_data
    return {
        "host": entry.data[CONF_HOST],
        "mapping_file": coordinator.mapping_file,
        "rest_api_fetch_succeeded": coordinator.last_data_fetch_success,
        "last_update_time": (
            coordinator.last_data_fetch_time.isoformat()
            if coordinator.last_data_fetch_time is not None
            else None
        ),
        "last_error": coordinator.last_data_fetch_error,
        "has_last_payload": coordinator.data is not None,
    }


async def _async_reload_entry(
    hass: HomeAssistant, entry: SolaXRestAPIConfigEntry
) -> None:
    """Reload config entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)
