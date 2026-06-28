"""Helpers for loading and resolving mapped SolaX sensor values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _normalize_key(key: str) -> str:
    """Normalize a dictionary key for lookup."""
    return str(key).lower()


def _coerce_numeric(value: Any) -> float | int | None:
    """Convert a state value to a numeric value when possible."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _is_numeric(value: Any) -> bool:
    """Return True if value is numeric (excluding booleans)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def resolve_value(
    payload: dict[str, Any],
    definition: dict[str, Any],
    hass: Any | None = None,
    entity_sources: dict[str, Any] | None = None,
    coordinator: Any | None = None,
) -> Any:
    """Resolve a value from the payload by following the configured path."""
    source = definition.get("source")
    if isinstance(source, dict):
        if source.get("type") == "grid_power_derived":
            derived_type = definition.get("key")
            if coordinator is None:
                return None
            if derived_type == "grid_import_energy":
                return coordinator.grid_import_total
            if derived_type == "grid_export_energy":
                return coordinator.grid_export_total
            return None

        if source.get("type") == "rest_api_fetch_status":
            if coordinator is None:
                return None

            if coordinator.last_data_fetch_success is None:
                return "unknown"
            if coordinator.last_data_fetch_success:
                return "success"
            return "failed"
        
        if source.get("type") == "entity_state":
            entity_id = source.get("entity_id")
            if not isinstance(entity_id, str) and isinstance(entity_sources, dict):
                entity_id = entity_sources.get(definition.get("key"))
            if isinstance(entity_id, str) and hass is not None:
                state = hass.states.get(entity_id)
                if state is not None:
                    value = _coerce_numeric(getattr(state, "state", None))
                    if value is not None:
                        scale = definition.get("scale", 1)
                        if isinstance(scale, (int, float)) and scale != 1:
                            return value * scale
                        return value
            return None

    if isinstance(definition.get("read"), dict):
        read_definition = definition["read"]
        if read_definition.get("type") == "combine":
            parts = read_definition.get("parts", [])
            if not isinstance(parts, list):
                return None

            values: list[Any] = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                value = resolve_value(payload, part)
                if isinstance(value, (int, float)):
                    values.append(value)
                else:
                    return None

            if not values:
                return None

            current = values[0]
            for index, part in enumerate(parts[1:], start=1):
                if not isinstance(part, dict):
                    continue
                factor = part.get("factor", 1)
                if not isinstance(factor, (int, float)):
                    factor = 1
                current = current + (values[index] * factor)

            scale = read_definition.get("scale", definition.get("scale", 1))
            if isinstance(scale, (int, float)) and scale != 1:
                return current * scale
            return current

    path = definition.get("path", [])
    if not isinstance(path, list):
        return None

    current: Any = payload
    for segment in path:
        if isinstance(current, dict):
            if isinstance(segment, str):
                if segment in current:
                    current = current[segment]
                elif _normalize_key(segment) in current:
                    current = current[_normalize_key(segment)]
                else:
                    return None
            else:
                return None
        elif isinstance(current, list):
            if isinstance(segment, int) and 0 <= segment < len(current):
                current = current[segment]
            else:
                return None
        else:
            return None

    scale = definition.get("scale", 1)
    if _is_numeric(scale) and scale != 1:
        numeric_value = _coerce_numeric(current)
        if numeric_value is None:
            return None
        return numeric_value * scale

    if _is_numeric(current):
        return current

    if isinstance(current, str):
        stripped_value = current.strip()
        return stripped_value or None

    return None


def _resolve_mapping_path(mapping_path: str | Path | None) -> Path:
    """Resolve a mapping file path from a file name or path."""
    if mapping_path is None:
        return Path(__file__).resolve().parent / "mappings" / "solax_type4.json"

    path = Path(mapping_path)
    if path.is_absolute():
        return path

    if path.suffix:
        candidate = Path(__file__).resolve().parent / "mappings" / path
    else:
        candidate = Path(__file__).resolve().parent / "mappings" / f"{path}.json"

    if candidate.exists():
        return candidate

    return path


def load_sensor_definitions(mapping_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load sensor definitions from a JSON mapping file."""
    path = _resolve_mapping_path(mapping_path)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    sensors = data.get("sensors", [])
    if not isinstance(sensors, list):
        raise ValueError("The mapping file must contain a 'sensors' list")
    return sensors


def get_available_mappings(mapping_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """List available mapping profiles from the mappings directory."""
    directory = Path(mapping_dir) if mapping_dir else Path(__file__).resolve().parent / "mappings"
    if not directory.exists():
        return []

    mappings: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        mappings.append(
            {
                "id": path.stem,
                "name": data.get("name", path.stem.replace("_", " ").title()),
                "path": str(path),
                "match": data.get("match", {}),
            }
        )

    return mappings


def select_mapping_file(
    payload: dict[str, Any],
    mapping_files: list[str | Path | dict[str, Any]],
    preferred_id: str | None = None,
) -> str | None:
    """Select the best mapping for a payload."""
    normalized: list[dict[str, Any]] = []
    for item in mapping_files:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        normalized.append({"id": str(item), "path": str(item)})

    if preferred_id:
        for mapping in normalized:
            if mapping.get("id") == preferred_id or mapping.get("path") == preferred_id:
                return str(mapping.get("path"))

    for mapping in normalized:
        match_data = mapping.get("match", {})
        if not isinstance(match_data, dict):
            continue
        if all(
            payload.get(key) == expected
            for key, expected in match_data.items()
        ):
            return str(mapping.get("path"))

    if normalized:
        return str(normalized[0].get("path"))
    return None
