from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .const import MODE_MERGE_LIST, MODE_UI_SINGLE


@dataclass
class ConversionResult:
    created: int
    skipped: int
    output_file: str
    integration_index_file: str


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "automation"


def _safe_name(node: dict[str, Any], fallback: str) -> str:
    name = str(node.get("name") or "").strip()
    return name if name else fallback


def _extract_timeout_ms(function_code: str) -> int:
    match = re.search(r"const\s+timeout\s*=\s*(\d+)", function_code or "")
    if not match:
        return 2000
    return int(match.group(1))


def _to_seconds(timeout_ms: int) -> int:
    return max(1, int(round(timeout_ms / 1000)))


def _service_from_call_node(node: dict[str, Any]) -> str | None:
    action = str(node.get("action") or "").strip()
    if action:
        return action
    domain = str(node.get("domain") or "").strip()
    service = str(node.get("service") or "").strip()
    if domain and service:
        return f"{domain}.{service}"
    return None


def _target_from_call_node(node: dict[str, Any]) -> dict[str, Any]:
    target: dict[str, Any] = {}

    for key in ("entityId", "deviceId", "areaId", "floorId", "labelId"):
        raw = node.get(key)
        if isinstance(raw, list) and raw:
            yaml_key = {
                "entityId": "entity_id",
                "deviceId": "device_id",
                "areaId": "area_id",
                "floorId": "floor_id",
                "labelId": "label_id",
            }[key]
            target[yaml_key] = raw[0] if len(raw) == 1 else raw
    return target


def _make_trigger(trigger_node: dict[str, Any]) -> list[dict[str, Any]]:
    entities = trigger_node.get("entities", {}).get("entity", [])
    entity_id = entities[0] if entities else ""
    to_state = str(trigger_node.get("ifState") or "")

    trigger: dict[str, Any] = {
        "trigger": "state",
        "entity_id": entity_id,
    }
    if to_state:
        trigger["to"] = to_state

    return [trigger]


def _build_simple_automation(
    trigger_node: dict[str, Any],
    call_node: dict[str, Any],
    flow_name: str,
) -> tuple[dict[str, Any], str] | None:
    service = _service_from_call_node(call_node)
    if not service:
        return None

    domain = service.split(".", 1)[0]
    trigger_name = _safe_name(trigger_node, "Node-RED trigger")
    alias = f"[{domain}] {flow_name} - {trigger_name}"

    automation = {
        "id": _slugify(alias),
        "alias": alias,
        "mode": "single",
        "triggers": _make_trigger(trigger_node),
        "conditions": [],
        "actions": [
            {
                "action": service,
                "target": _target_from_call_node(call_node),
            }
        ],
    }
    return automation, domain


def _build_double_press_automation(
    trigger_node: dict[str, Any],
    function_node: dict[str, Any],
    switch_node: dict[str, Any],
    first_call: dict[str, Any],
    second_call: dict[str, Any],
    flow_name: str,
) -> tuple[dict[str, Any], str] | None:
    first_service = _service_from_call_node(first_call)
    second_service = _service_from_call_node(second_call)
    if not first_service or not second_service:
        return None

    timeout_seconds = _to_seconds(_extract_timeout_ms(str(function_node.get("func") or "")))

    first_domain = first_service.split(".", 1)[0]
    second_domain = second_service.split(".", 1)[0]
    domain = first_domain if first_domain == second_domain else "mixed"

    trigger_name = _safe_name(trigger_node, "Node-RED trigger")
    alias = f"[{domain}] {flow_name} - {trigger_name} (single/double press)"

    automation = {
        "id": _slugify(alias),
        "alias": alias,
        "mode": "single",
        "triggers": _make_trigger(trigger_node),
        "conditions": [],
        "actions": [
            {
                "wait_for_trigger": _make_trigger(trigger_node),
                "timeout": {"seconds": timeout_seconds},
                "continue_on_timeout": True,
            },
            {
                "if": [
                    {
                        "condition": "template",
                        "value_template": "{{ wait.trigger is not none }}",
                    }
                ],
                "then": [
                    {
                        "action": second_service,
                        "target": _target_from_call_node(second_call),
                    }
                ],
                "else": [
                    {
                        "action": first_service,
                        "target": _target_from_call_node(first_call),
                    }
                ],
            },
        ],
    }
    return automation, domain


def convert_node_red_file(
    nodered_file: str,
    output_file: str,
    mode: str,
    filter_domain: str | None = None,
) -> ConversionResult:
    source = Path(nodered_file)
    if not source.exists():
        raise FileNotFoundError(f"Node-RED file not found: {nodered_file}")

    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Node-RED export must be a JSON list")

    nodes_by_id = {node.get("id"): node for node in data if isinstance(node, dict) and node.get("id")}

    tab_names: dict[str, str] = {}
    for node in data:
        if node.get("type") == "tab":
            tab_names[node.get("id")] = str(node.get("label") or "Flow")

    converted: list[dict[str, Any]] = []
    integration_index: dict[str, list[str]] = {}
    skipped = 0

    for node in data:
        if node.get("type") != "server-state-changed":
            continue

        flow_name = tab_names.get(str(node.get("z") or ""), "Flow")

        wires = node.get("wires", [])
        if not wires or not wires[0]:
            skipped += 1
            continue

        first_next_id = wires[0][0]
        first_next = nodes_by_id.get(first_next_id)
        if not first_next:
            skipped += 1
            continue

        built: tuple[dict[str, Any], str] | None = None

        if first_next.get("type") == "api-call-service":
            built = _build_simple_automation(node, first_next, flow_name)

        elif first_next.get("type") == "function":
            function_wires = first_next.get("wires", [])
            if not function_wires or not function_wires[0]:
                skipped += 1
                continue
            switch_node = nodes_by_id.get(function_wires[0][0])
            if not switch_node or switch_node.get("type") != "switch":
                skipped += 1
                continue

            switch_wires = switch_node.get("wires", [])
            if len(switch_wires) < 2 or not switch_wires[0] or not switch_wires[1]:
                skipped += 1
                continue

            first_call = nodes_by_id.get(switch_wires[0][0])
            second_call = nodes_by_id.get(switch_wires[1][0])
            if (
                not first_call
                or not second_call
                or first_call.get("type") != "api-call-service"
                or second_call.get("type") != "api-call-service"
            ):
                skipped += 1
                continue

            built = _build_double_press_automation(
                node,
                first_next,
                switch_node,
                first_call,
                second_call,
                flow_name,
            )

        if not built:
            skipped += 1
            continue

        automation, domain = built
        if filter_domain and domain != filter_domain:
            continue

        integration_index.setdefault(domain, []).append(automation["id"])
        converted.append(automation)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == MODE_UI_SINGLE:
        if not converted:
            raise ValueError("No automation could be converted")
        yaml_out = yaml.safe_dump(converted[0], allow_unicode=False, sort_keys=False)
    elif mode == MODE_MERGE_LIST:
        yaml_out = yaml.safe_dump(converted, allow_unicode=False, sort_keys=False)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    output_path.write_text(yaml_out, encoding="utf-8")

    index_path = output_path.with_suffix(".index.json")
    index_path.write_text(json.dumps(integration_index, indent=2), encoding="utf-8")

    return ConversionResult(
        created=len(converted),
        skipped=skipped,
        output_file=str(output_path),
        integration_index_file=str(index_path),
    )


def generate_overview_dashboard(index_file: str, output_file: str) -> str:
    index_path = Path(index_file)
    if not index_path.exists():
        raise FileNotFoundError(f"Integration index not found: {index_file}")

    integration_index: dict[str, list[str]] = json.loads(index_path.read_text(encoding="utf-8"))

    views: list[dict[str, Any]] = [
        {
            "title": "Node-RED Migrated",
            "path": "nodered-migrated",
            "icon": "mdi:shuffle-variant",
            "cards": [],
        }
    ]

    cards = views[0]["cards"]

    cards.append(
        {
            "type": "markdown",
            "content": "# Node-RED -> Native Automations\\nBruk toggles under for aa bytte native automasjoner per integrasjon.",
        }
    )

    for domain in sorted(integration_index.keys()):
        entities = [f"automation.{automation_id}" for automation_id in integration_index[domain]]
        cards.append(
            {
                "type": "entities",
                "title": f"Integration: {domain}",
                "show_header_toggle": True,
                "entities": entities,
            }
        )

    dashboard = {
        "title": "Node-RED Migrated Overview",
        "views": views,
    }

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(dashboard, allow_unicode=False, sort_keys=False), encoding="utf-8")

    return str(out_path)
