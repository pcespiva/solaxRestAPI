"""Sensor platform for the SolaX REST API integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST

from .const import CONF_ENTITY_SOURCES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolaXRestAPIConfigEntry, SolaXRestAPIDataUpdateCoordinator
from .mapping import resolve_value


@dataclass(frozen=True, kw_only=True)
class SolaXRestAPISensorEntityDescription(SensorEntityDescription):
    """Describe a SolaX REST API sensor."""

    path: tuple[Any, ...] = ()
    scale: float = 1.0
    source: dict[str, Any] | None = None
    read: dict[str, Any] | None = None
    optional: bool = False


def _create_sensor_descriptions(
    sensor_definitions: list[dict[str, Any]],
) -> tuple[SolaXRestAPISensorEntityDescription, ...]:
    """Create entity descriptions from the mapping file."""
    descriptions: list[SolaXRestAPISensorEntityDescription] = []

    for definition in sensor_definitions:
        if not isinstance(definition, dict):
            continue

        entity_category = None
        if definition.get("entity_category") == "diagnostic":
            entity_category = EntityCategory.DIAGNOSTIC

        device_class = None
        if device_class_name := definition.get("device_class"):
            device_class = getattr(
                SensorDeviceClass, str(device_class_name).upper(), None
            )

        state_class = None
        if state_class_name := definition.get("state_class"):
            state_class = getattr(SensorStateClass, str(state_class_name).upper(), None)

        descriptions.append(
            SolaXRestAPISensorEntityDescription(
                key=str(definition["key"]),
                name=definition.get("name", str(definition["key"])),
                entity_category=entity_category,
                path=tuple(definition.get("path", [])),
                scale=float(definition.get("scale", 1.0)),
                native_unit_of_measurement=definition.get("unit"),
                device_class=device_class,
                state_class=state_class,
                source=definition.get("source"),
                read=definition.get("read"),
                optional=bool(definition.get("optional", False)),
            )
        )

    return tuple(descriptions)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolaXRestAPIConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX REST API sensors."""
    descriptions = _create_sensor_descriptions(entry.runtime_data.mapping_definitions)
    async_add_entities(
        [
            SolaXRestAPISensor(entry.runtime_data, description)
            for description in descriptions
        ]
    )


class SolaXRestAPISensor(
    CoordinatorEntity[SolaXRestAPIDataUpdateCoordinator], SensorEntity
):
    """SolaX REST API sensor."""

    entity_description: SolaXRestAPISensorEntityDescription

    def __init__(
        self,
        coordinator: SolaXRestAPIDataUpdateCoordinator,
        description: SolaXRestAPISensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._device_identifier}_{description.key}"
        self._attr_device_info = self._device_info

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None

        entity_sources = {}
        if self.coordinator.config_entry is not None:
            entity_sources = self.coordinator.config_entry.options.get(
                CONF_ENTITY_SOURCES,
                self.coordinator.config_entry.data.get(CONF_ENTITY_SOURCES, {}),
            )
        if not isinstance(entity_sources, dict):
            entity_sources = {}

        value = resolve_value(
            self.coordinator.data,
            {
                "key": self.entity_description.key,
                "path": list(self.entity_description.path),
                "scale": self.entity_description.scale,
                "source": self.entity_description.source,
                "read": self.entity_description.read,
            },
            hass=self.hass,
            entity_sources=entity_sources,
            coordinator=self.coordinator,
        )
        return value

    @property
    def available(self) -> bool:
        """Return whether the entity should be exposed."""
        if self.coordinator.data is None:
            return False

        if self.entity_description.optional:
            return self.native_value is not None
        return True

    @property
    def _device_identifier(self) -> str:
        """Return the best available device identifier."""
        if self.coordinator.data is not None:
            information = self.coordinator.data.get("information")
            if (
                isinstance(information, list)
                and len(information) > 2
                and isinstance(information[2], str)
            ):
                return information[2]
            if sn := self.coordinator.data.get("sn"):
                return str(sn)
        return self.coordinator.config_entry.data[CONF_HOST]

    @property
    def _device_info(self) -> DeviceInfo:
        """Return device info from the latest payload."""
        host = self.coordinator.config_entry.data[CONF_HOST]
        data = self.coordinator.data or {}
        information = (
            data.get("information") if isinstance(data.get("information"), list) else []
        )
        identifier = self._device_identifier
        inverter_type = information[1] if len(information) > 1 else data.get("type")
        nominal_power = information[0] if information else None
        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer="SolaX",
            model=f"Type {inverter_type}" if inverter_type is not None else None,
            name=f"SolaX {identifier}",
            serial_number=identifier,
            sw_version=str(data["ver"]) if data.get("ver") is not None else None,
            configuration_url=f"http://{host}",
            hw_version=f"{nominal_power:g} kW"
            if isinstance(nominal_power, float)
            else None,
        )
