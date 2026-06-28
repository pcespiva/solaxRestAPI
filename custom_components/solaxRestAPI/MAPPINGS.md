# Mapping Documentation

This document describes the mapping file format in `mappings/*.json` and the current `solax_type4` profile.

## Basic File Structure

```json
{
  "version": 1,
  "name": "SolaX Type 4",
  "match": {
    "type": 4
  },
  "sensors": [
    {
      "key": "ac_voltage",
      "name": "AC voltage",
      "path": ["data", 0],
      "scale": 0.1,
      "unit": "V",
      "device_class": "voltage",
      "state_class": "measurement"
    }
  ]
}
```

## Profile-Level Fields

- `version`: mapping format version.
- `name`: human-readable profile name.
- `match`: rules for automatic profile selection based on payload.
- `sensors`: list of sensor definitions.

## Sensor Definition Fields

- `key` (required): internal sensor identifier.
- `name`: display name.
- `entity_category`: for example `diagnostic`.
- `path`: path inside payload, for example `['data', 0]` or `['information', 2]`.
- `scale`: multiplier applied to the value.
- `unit`: measurement unit (`W`, `kWh`, `V`, `A`, ...).
- `device_class`: Home Assistant `SensorDeviceClass`.
- `state_class`: Home Assistant `SensorStateClass`.
- `optional`: if `true`, the entity is available only when a value exists.
- `configurable`: allows source selection in config flow (for `entity_state`).
- `source`: alternative source instead of direct `path`.
- `read`: advanced read behavior (for example combining multiple registers).

## Supported `source` Types

- `entity_state`: read value from another Home Assistant entity.
- `grid_power_derived`: derived import/export energy from `grid_power`.
- `rest_api_fetch_status`: status of the last REST API read (`success` / `failed` / `unknown`).

## Supported `read` Types

- `combine`: builds a value from multiple parts.
- `parts`: list of parts (`path` + optional `factor`).
- `scale`: optional final scaling.

## Payload Notes

- API response top-level keys are normalized to lowercase.
- `Data` is available as `data`.
- `Information` is available as `information`.
- Text values (for example serial numbers) are supported and returned as strings.

## `solax_type4` Profile: Mapped Entities

### Diagnostic Entities

| Key | Name | Zdroj |
| --- | --- | --- |
| `dongle_serial_number` | Dongle serial number | `path: ['sn']` |
| `dongle_version` | Dongle version | `path: ['ver']` |
| `inverter_nominal_power` | Inverter nominal power | `path: ['information', 0]` |
| `inverter_type` | Inverter type | `path: ['information', 1]` |
| `inverter_serial_number` | Inverter serial number | `path: ['information', 2]` |
| `phase_type` | Phase type | `path: ['information', 9]` |
| `rest_api_fetch_status` | REST API fetch status | `source: rest_api_fetch_status` |

### Measurement Entities

| Key | Name | Zdroj | Scale | Unit |
| --- | --- | --- | --- | --- |
| `yield_daily` | Yield daily | `data[13]` | `0.1` | `kWh` |
| `ac_current` | AC current | `data[1]` | `0.1` | `A` |
| `ac_frequency` | AC frequency | `data[9]` | `0.01` | `Hz` |
| `ac_voltage` | AC voltage | `data[0]` | `0.1` | `V` |
| `ac_power` | AC power | `data[2]` | `1` | `W` |
| `pv1_current` | PV1 current | `data[5]` | `0.1` | `A` |
| `pv1_power` | PV1 power | `data[7]` | `1` | `W` |
| `pv1_voltage` | PV1 voltage | `data[3]` | `0.1` | `V` |
| `temperature_internal` | Temperature internal | `data[39]` | `1` | `degC` |

### Combined/Derived Entities

| Key | Name | Zdroj |
| --- | --- | --- |
| `yield_total` | Yield total | `read.combine: data[11] + data[12] * 65536`, then `scale 0.1` |
| `grid_power` | Grid power | `source: entity_state` (optional, configurable) |
| `grid_import_energy` | Grid import energy | `source: grid_power_derived` |
| `grid_export_energy` | Grid export energy | `source: grid_power_derived` |

## How To Add A New Entity

1. Add a definition to `sensors` in the relevant mapping file.
2. If you introduce a new `source` or `read` type, add logic in `mapping.py`.
3. Reload the integration and verify the sensor returns the expected value.
