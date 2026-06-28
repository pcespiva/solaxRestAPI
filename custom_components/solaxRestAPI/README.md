# SolaX Rest API (Custom Integration)

Custom Home Assistant integration for reading local SolaX inverter data through the built-in REST endpoint.

## Features

- Reads realtime data from the inverter's local IP address.
- Supports JSON mapping profiles (currently `solax_type4`).
- Creates diagnostic and measurement sensors from the mapping file.
- Can use an external `grid_power` sensor and derive:
  - `grid_import_energy`
  - `grid_export_energy`
- Includes a diagnostic status sensor for API fetch state:
  - `rest_api_fetch_status` = `success` / `failed` / `unknown`

## Requirements

- Home Assistant
- SolaX inverter reachable on the local network
- Known host (IP/hostname)
- Endpoint password (default is often `SRCSKCLBHB`)

## Configuration In UI

1. Go to Settings -> Devices & Services -> Add Integration.
2. Select `SolaX Rest API`.
3. Fill in:
   - Host
   - Password
   - Scan interval (minimum 5 seconds)
   - Mapping profile (`solax_type4`)
4. If the mapping contains configurable `entity_state` sources, select them in the next step.

## Mapping Profiles

The integration loads entities from files in `mappings/`.

- The active profile is stored as `mapping_file`.
- A profile can be selected manually or auto-selected using `match` rules.

For full mapping format and entity list, see `MAPPINGS.md`.

## Diagnostics

The integration exposes diagnostics (`async_get_config_entry_diagnostics`) including:

- `rest_api_fetch_succeeded`
- `last_update_time`
- `last_error`
- `has_last_payload`

It also exposes the diagnostic sensor `REST API fetch status`.

## Publishing Through HACS

Recommended standalone repository layout:

```text
<repo-root>/
  custom_components/
    solaxRestAPI/
      __init__.py
      manifest.json
      ...
  hacs.json
  README.md
```

### Minimal `hacs.json`

```json
{
  "name": "SolaX Rest API",
  "content_in_root": false,
  "country": ["CZ", "SK", "DE", "AT"],
  "homeassistant": ">=2024.1.0",
  "render_readme": true
}
```

### Important Before Release

- Ensure `manifest.json` contains a valid `version`.
- Lowercase domain naming is recommended (Home Assistant best practice).
- Create release tags (`v0.1.0`, `v0.1.1`, ...) because HACS uses them for updates.
- Add this repository to HACS as `Custom repository`, category `Integration`.

## Development

When changing mappings:

1. Edit the JSON file in `mappings/`.
2. Reload the integration (or restart Home Assistant).
3. Verify sensors and diagnostics in Developer Tools.
