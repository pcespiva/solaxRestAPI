"""Coordinator for the SolaX REST API integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SolaXRestAPIClient, SolaXRestAPIError
from .const import CONF_ENTITY_SOURCES, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .mapping import load_sensor_definitions

_LOGGER = logging.getLogger(__name__)

type SolaXRestAPIConfigEntry = ConfigEntry[SolaXRestAPIDataUpdateCoordinator]


class SolaXRestAPIDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching SolaX local data."""

    config_entry: SolaXRestAPIConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SolaXRestAPIConfigEntry,
        client: SolaXRestAPIClient,
        mapping_file: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.mapping_file = mapping_file or "solax_type4"
        self.mapping_definitions = load_sensor_definitions(self.mapping_file)
        self.last_data_fetch_success: bool | None = None
        self.last_data_fetch_error: str | None = None
        self.last_data_fetch_time: datetime | None = None
        self.grid_import_total: float = 0.0
        self.grid_export_total: float = 0.0
        self.scan_interval_seconds: int = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {client.host}",
            update_interval=timedelta(seconds=self.scan_interval_seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the inverter."""
        try:
            data = await self.client.async_get_realtime_data()
        except SolaXRestAPIError as err:
            self.last_data_fetch_success = False
            self.last_data_fetch_error = str(err)
            self.last_data_fetch_time = dt_util.utcnow()
            raise UpdateFailed(err) from err

        self.last_data_fetch_success = True
        self.last_data_fetch_error = None
        self.last_data_fetch_time = dt_util.utcnow()
        
        entity_sources = self.config_entry.options.get(
            CONF_ENTITY_SOURCES,
            self.config_entry.data.get(CONF_ENTITY_SOURCES, {}),
        )
        if isinstance(entity_sources, dict):
            grid_power_entity_id = entity_sources.get("grid_power")
            if isinstance(grid_power_entity_id, str):
                state = self.hass.states.get(grid_power_entity_id)
                if state is not None and state.state != "unknown":
                    try:
                        grid_power_w = float(state.state)
                        delta_kwh = (grid_power_w * self.scan_interval_seconds) / 3600000
                        if delta_kwh > 0:
                            self.grid_import_total += delta_kwh
                        else:
                            self.grid_export_total += abs(delta_kwh)
                    except (ValueError, TypeError):
                        pass
        
        return data
