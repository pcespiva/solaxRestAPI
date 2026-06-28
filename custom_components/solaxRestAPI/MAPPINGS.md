# Mapping dokumentace

Tento dokument popisuje format mapovacich souboru v `mappings/*.json` a aktualni profil `solax_type4`.

## Zakladni struktura souboru

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

## Polozky na urovni profilu

- `version`: verze formatu mappingu.
- `name`: citelny nazev profilu.
- `match`: pravidla pro auto-vyber profilu podle payloadu.
- `sensors`: seznam definic senzoru.

## Pole definice senzoru

- `key` (povinne): interni identifikator senzoru.
- `name`: zobrazene jmeno senzoru.
- `entity_category`: napr. `diagnostic`.
- `path`: cesta do payloadu, napr. `['data', 0]` nebo `['information', 2]`.
- `scale`: nasobek pro prepocet hodnoty.
- `unit`: jednotka (`W`, `kWh`, `V`, `A`, ...).
- `device_class`: Home Assistant `SensorDeviceClass`.
- `state_class`: Home Assistant `SensorStateClass`.
- `optional`: pokud je `true`, entita je dostupna jen kdyz ma hodnotu.
- `configurable`: umozni vybrat zdroj v config flow (pro `entity_state`).
- `source`: alternativni zdroj misto primeho `path`.
- `read`: rozsirene cteni (napr. skladani vice registru).

## Podporovane source typy

- `entity_state`: cteni hodnoty z jine entity v HA.
- `grid_power_derived`: odvozene energie import/export z `grid_power`.
- `rest_api_fetch_status`: stav posledniho REST cteni (`success` / `failed` / `unknown`).

## Podporovane read typy

- `combine`: slozi vysledek z vice casti.
  - `parts`: pole casti (`path` + volitelny `factor`).
  - `scale`: volitelny finalni prepocet.

## Poznamky k payloadu

- API odpoved se normalizuje na lowercase top-level klice.
- Pole `Data` je dostupne jako `data`.
- Pole `Information` je dostupne jako `information`.
- Textove hodnoty (napr. serial) jsou podporene a vraci se jako string.

## Profil `solax_type4`: mapovane entity

### Diagnosticke entity

| Key | Name | Zdroj |
| --- | --- | --- |
| `dongle_serial_number` | Dongle serial number | `path: ['sn']` |
| `dongle_version` | Dongle version | `path: ['ver']` |
| `inverter_nominal_power` | Inverter nominal power | `path: ['information', 0]` |
| `inverter_type` | Inverter type | `path: ['information', 1]` |
| `inverter_serial_number` | Inverter serial number | `path: ['information', 2]` |
| `phase_type` | Phase type | `path: ['information', 9]` |
| `rest_api_fetch_status` | REST API fetch status | `source: rest_api_fetch_status` |

### Merici entity

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

### Kombinovane/odvozene entity

| Key | Name | Zdroj |
| --- | --- | --- |
| `yield_total` | Yield total | `read.combine: data[11] + data[12] * 65536`, pak `scale 0.1` |
| `grid_power` | Grid power | `source: entity_state` (volitelny, konfigurovatelny) |
| `grid_import_energy` | Grid import energy | `source: grid_power_derived` |
| `grid_export_energy` | Grid export energy | `source: grid_power_derived` |

## Jak pridat novou entitu

1. Pridej definici do `sensors` v prislusnem mappingu.
2. Pokud jde o novy typ `source` nebo `read`, dopln logiku v `mapping.py`.
3. Reload integrace a over, ze senzor vraci hodnotu.
