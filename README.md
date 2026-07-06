# Home Assistant Node-RED to Native Automation Converter

Custom Home Assistant integration that helps migrate Node-RED flows to native Home Assistant automations.

Status: Main branch (commit-based updates)

It includes:

- Config Flow GUI (Settings -> Devices & Services)
- Conversion service for Node-RED JSON exports
- Integration/domain filtering (migrate one integration at a time)
- Overview dashboard YAML grouped by integration for easy enable/disable of migrated automations

## One-click install (HACS)

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=aervig&repository=Home-Assistant-Node-Ret-to-Native-automation-convertor&category=integration)

## Update model

This repository uses commit-based updates from the main branch only.
No beta channel and no release/tag based install flow is used.

## Install with HACS

1. Open HACS.
2. Go to Integrations.
3. Click the three dots menu -> Custom repositories.
4. Add this repository URL:
   - https://github.com/aervig/Home-Assistant-Node-Ret-to-Native-automation-convertor
   - Category: Integration
5. Search for Node-RED Native Migrator in HACS and install.
6. Restart Home Assistant.
7. Go to Settings -> Devices & Services -> Add Integration.
8. Add Node-RED Native Migrator.

## Manual install

1. Copy custom_components/nodered_native_migrator to your Home Assistant config/custom_components folder.
2. Restart Home Assistant.
3. Add integration from Settings -> Devices & Services.

## First run setup (what to fill in)

You do not need to fill anything during first install anymore.

The integration now creates itself with sane defaults automatically:

- Domain filter: empty (convert all)
- Output file: /config/automations_migrated.yaml
- Output mode: merge_list

If you want to change defaults later, open integration options. There you can adjust these fields:

- Default integration/domain filter
  - Optional.
  - Leave empty to convert all supported flows.
  - Example values: vacuum, light, climate.

- Default output file
  - Path to generated automation YAML.
  - Recommended: /config/automations_migrated.yaml

- Default output mode
  - merge_list: use when writing list-style automations for include files.
  - ui_single: use when you want one single automation object for Edit in YAML.
  - Recommended for most file-based setups: merge_list.

## Services

### 1) Convert Node-RED flow export

Domain: nodered_native_migrator  
Service: convert_flow_file

Example service data:

```yaml
nodered_file: /config/node_red_exports/my_flow.json
output_file: /config/automations_migrated.yaml
mode: merge_list
filter_domain: vacuum
```

Fields:

- nodered_file: Absolute path to exported Node-RED JSON file
- output_file: Output YAML path
- mode:
  - ui_single (single automation object for UI editor)
  - merge_list (list for include_dir_merge_list style)
- filter_domain: Optional domain filter (vacuum, light, climate, and so on)

### 2) Build overview dashboard

Domain: nodered_native_migrator  
Service: build_overview_dashboard

Example service data:

```yaml
output_file: /config/dashboards/nodered_migrated_overview.yaml
```

This creates a dashboard YAML with automation entities grouped per integration/domain.

## Current MVP scope

Supported conversion patterns right now:

- server-state-changed -> api-call-service
- server-state-changed -> function(count/timeout) -> switch -> api-call-service + api-call-service (single/double press style)

More Node-RED patterns can be added incrementally.

## Development roadmap

- Add support for more trigger types (time, event, mqtt, template)
- Add preview before write
- Add conflict handling for duplicate automation IDs
- Add a visual mapping panel for flow-to-automation links

## Repository structure

- custom_components/nodered_native_migrator/manifest.json
- custom_components/nodered_native_migrator/__init__.py
- custom_components/nodered_native_migrator/config_flow.py
- custom_components/nodered_native_migrator/converter.py
- custom_components/nodered_native_migrator/services.yaml
- custom_components/nodered_native_migrator/translations/en.json

## License

MIT
