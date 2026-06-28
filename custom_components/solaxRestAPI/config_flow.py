"""Config flow for the SolaX REST API integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import SolaXRestAPIClient, SolaXRestAPIError
from .const import (
    CONF_ENTITY_SOURCES,
    CONF_MAPPING_FILE,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAPPING_FILE,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .mapping import get_available_mappings, load_sensor_definitions, select_mapping_file

_LOGGER = logging.getLogger(__name__)


def _mapping_selector(default_mapping: str) -> SelectSelector:
    """Return a selector for the available mapping profiles."""
    options = [
        SelectOptionDict(value=mapping["id"], label=mapping["name"])
        for mapping in get_available_mappings()
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _user_schema(
    user_input: dict[str, Any] | None = None,
    default_mapping: str | None = None,
) -> vol.Schema:
    """Return user setup schema."""
    user_input = user_input or {}
    default_mapping = default_mapping or DEFAULT_MAPPING_FILE
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): cv.string,
            vol.Required(
                CONF_PASSWORD,
                default=user_input.get(CONF_PASSWORD, DEFAULT_PASSWORD),
            ): cv.string,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            vol.Required(
                CONF_MAPPING_FILE,
                default=user_input.get(CONF_MAPPING_FILE, default_mapping),
            ): _mapping_selector(default_mapping),
        }
    )


def _is_configurable_entity_source(definition: dict[str, Any]) -> bool:
    """Return whether a mapping definition can be populated from config flow."""
    source = definition.get("source")
    return (
        bool(definition.get("configurable", False))
        and isinstance(source, dict)
        and source.get("type") == "entity_state"
    )


def _entity_source_schema(
    definitions: list[dict[str, Any]],
    current_entity_sources: dict[str, Any] | None = None,
) -> dict[vol.Marker, Any]:
    """Return schema fields for configurable entity sources."""
    schema: dict[vol.Marker, Any] = {}
    current_sources = current_entity_sources or {}

    for definition in definitions:
        if not _is_configurable_entity_source(definition):
            continue

        field_name = f"entity_source_{definition['key']}"
        default_entity_id = current_sources.get(definition["key"])
        if default_entity_id is None:
            default_entity_id = definition.get("source", {}).get("entity_id")

        schema[vol.Optional(field_name, default=default_entity_id)] = EntitySelector(
            EntitySelectorConfig(domain=[SENSOR_DOMAIN])
        )

    return schema


def _extract_entity_sources(
    user_input: dict[str, Any],
    definitions: list[dict[str, Any]],
) -> dict[str, str]:
    """Extract configurable entity-source selections from user input."""
    entity_sources: dict[str, str] = {}
    for definition in definitions:
        if not _is_configurable_entity_source(definition):
            continue

        field_name = f"entity_source_{definition['key']}"
        entity_id = user_input.get(field_name)
        if isinstance(entity_id, str) and entity_id:
            entity_sources[definition["key"]] = entity_id

    return entity_sources


def _options_schema(
    scan_interval: int,
    mapping_file: str,
    current_entity_sources: dict[str, Any] | None = None,
) -> vol.Schema:
    """Return options schema."""
    schema: dict[vol.Marker, Any] = {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=scan_interval,
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
        vol.Required(
            CONF_MAPPING_FILE,
            default=mapping_file,
        ): _mapping_selector(mapping_file),
    }
    definitions = load_sensor_definitions(mapping_file)
    schema.update(_entity_source_schema(definitions, current_entity_sources))
    return vol.Schema(schema)


async def _async_validate_input(
    flow: ConfigFlow, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate that the inverter can be reached."""
    client = SolaXRestAPIClient(
        async_get_clientsession(flow.hass),
        data[CONF_HOST],
        data[CONF_PASSWORD],
    )
    return await client.async_get_realtime_data()


def _device_identifier(data: dict[str, Any], fallback: str) -> str:
    """Return the best available device identifier."""
    information = data.get("information")
    if (
        isinstance(information, list)
        and len(information) > 2
        and isinstance(information[2], str)
    ):
        return information[2]
    if sn := data.get("sn"):
        return str(sn)
    return fallback


class SolaXRestAPIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolaX REST API."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._config_data: dict[str, Any] = {}
        self._entry_title = ""
        self._mapping_definitions: list[dict[str, Any]] = []

    @staticmethod
    def async_get_options_flow(config_entry: Any) -> OptionsFlow:
        """Create the options flow."""
        return SolaXRestAPIOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                payload = await _async_validate_input(self, user_input)
            except SolaXRestAPIError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                available_mappings = get_available_mappings()
                selected_mapping = select_mapping_file(
                    payload,
                    available_mappings,
                    user_input.get(CONF_MAPPING_FILE),
                )
                self._config_data = dict(user_input)
                self._config_data[CONF_MAPPING_FILE] = selected_mapping or DEFAULT_MAPPING_FILE
                self._mapping_definitions = load_sensor_definitions(
                    self._config_data[CONF_MAPPING_FILE]
                )
                identifier = _device_identifier(payload, host)
                await self.async_set_unique_id(identifier)
                self._abort_if_unique_id_configured()

                if any(_is_configurable_entity_source(definition) for definition in self._mapping_definitions):
                    self._entry_title = f"SolaX {identifier}"
                    return await self.async_step_entity_sources()

                return self.async_create_entry(
                    title=f"SolaX {identifier}",
                    data=self._config_data,
                    options={CONF_ENTITY_SOURCES: {}},
                )

        mapping_file = (
            user_input.get(CONF_MAPPING_FILE, DEFAULT_MAPPING_FILE)
            if user_input
            else DEFAULT_MAPPING_FILE
        )
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input, mapping_file),
            errors=errors,
        )


    async def async_step_entity_sources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select entities for configurable optional sensors."""
        if user_input is not None:
            entity_sources = _extract_entity_sources(user_input, self._mapping_definitions)
            return self.async_create_entry(
                title=self._entry_title,
                data=self._config_data,
                options={CONF_ENTITY_SOURCES: entity_sources},
            )

        return self.async_show_form(
            step_id="entity_sources",
            data_schema=vol.Schema(_entity_source_schema(self._mapping_definitions)),
        )


class SolaXRestAPIOptionsFlow(OptionsFlow):
    """Handle SolaX REST API options."""

    def __init__(self, config_entry: Any) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage integration options."""
        if user_input is not None:
            mapping_file = user_input.get(CONF_MAPPING_FILE, DEFAULT_MAPPING_FILE)
            entity_sources = _extract_entity_sources(
                user_input,
                load_sensor_definitions(mapping_file),
            )
            options: dict[str, Any] = {
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_MAPPING_FILE: mapping_file,
                CONF_ENTITY_SOURCES: entity_sources,
            }
            return self.async_create_entry(title="", data=options)

        scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        mapping_file = self._config_entry.options.get(
            CONF_MAPPING_FILE,
            self._config_entry.data.get(CONF_MAPPING_FILE, DEFAULT_MAPPING_FILE),
        )
        current_entity_sources = self._config_entry.options.get(
            CONF_ENTITY_SOURCES,
            self._config_entry.data.get(CONF_ENTITY_SOURCES, {}),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                scan_interval,
                mapping_file,
                current_entity_sources,
            ),
        )
