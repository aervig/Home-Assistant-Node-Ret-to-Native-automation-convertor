# Node-RED Native Migrator

Convert selected Node-RED Home Assistant flows to native Home Assistant automations.

## What it does

- Converts supported Node-RED flow patterns from exported JSON
- Supports integration/domain filtering (for example: vacuum, light, climate)
- Generates native automation YAML output
- Can generate an overview dashboard YAML grouped by integration/domain

## Current scope

- server-state-changed -> api-call-service
- server-state-changed -> function(count/timeout) -> switch -> api-call-service + api-call-service

## Install

Install through HACS as a custom repository:

- Repository: https://github.com/aervig/Home-Assistant-Node-Ret-to-Native-automation-convertor
- Category: Integration

## Services

- nodered_native_migrator.convert_flow_file
- nodered_native_migrator.build_overview_dashboard

## Notes

- Restart Home Assistant after installing or updating custom components.
- This project currently uses commit-based updates on main.
