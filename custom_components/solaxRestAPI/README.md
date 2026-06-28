# SolaX Rest API (Custom Integration)

Custom Home Assistant integrace pro lokalni cteni dat ze SolaX inverteru pres vestaveny REST endpoint.

## Co integrace umi

- Cte realtime data z lokalni IP adresy inverteru.
- Podporuje mapovaci profily (JSON), aktualne `solax_type4`.
- Vytvari diagnosticke i merici senzory podle mapping souboru.
- Umoznuje navazat externi senzor `grid_power` a odvodit:
  - `grid_import_energy`
  - `grid_export_energy`
- Obsahuje diagnosticky stav posledniho cteni API:
  - `rest_api_fetch_status` = `success` / `failed` / `unknown`

## Pozadavky

- Home Assistant
- SolaX menic dostupny v lokalni siti
- Znamy host (IP/hostname)
- Heslo pro endpoint (default byva `SRCSKCLBHB`)

## Konfigurace v UI

1. Settings -> Devices & Services -> Add Integration.
2. Vyber `SolaX Rest API`.
3. Vypln:
   - Host
   - Password
   - Scan interval (minimalne 5 s)
   - Mapping profile (`solax_type4`)
4. Pokud mapping obsahuje volitelne `entity_state` zdroje, vyber je v dalsim kroku.

## Mapping profile

Integrace nacita entity ze souboru v adresari `mappings/`.

- Aktivni profil se uklada jako `mapping_file`.
- Profil se muze vybrat manualne nebo automaticky podle `match` pravidel.

Detailni popis struktury mappingu a seznam entit je v souboru `MAPPINGS.md`.

## Diagnostika

Integrace publikuje diagnosticka data (`async_get_config_entry_diagnostics`) vcetne:

- `rest_api_fetch_succeeded`
- `last_update_time`
- `last_error`
- `has_last_payload`

Zaroven je dostupny diagnosticky sensor `REST API fetch status`.

## Publikace pres HACS

Doporuceny layout samostatneho Git repozitare:

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

### Minimalni `hacs.json`

```json
{
  "name": "SolaX Rest API",
  "content_in_root": false,
  "country": ["CZ", "SK", "DE", "AT"],
  "homeassistant": ">=2024.1.0",
  "render_readme": true
}
```

### Dulezite pred publikaci

- Zkontroluj, ze `manifest.json` obsahuje korektni `version`.
- Doporucene je drzet `domain` lowercase (HA best practice).
- Vytvor release tagy (`v0.1.0`, `v0.1.1`, ...), HACS je pouziva pro update.
- Pridej repozitar do HACS jako `Custom repository`, category `Integration`.

## Vyvoj

Pri upravach mapovani:

1. Uprav JSON v `mappings/`.
2. Reloadni integraci (nebo restart HA).
3. Over senzory a diagnostiku v Developer Tools.
