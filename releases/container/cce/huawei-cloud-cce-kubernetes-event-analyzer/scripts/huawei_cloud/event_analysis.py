"""Local aggregation for Kubernetes Event query results."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional


def _as_int(value: Any, default: int = 1) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _event_times(event: Dict[str, Any]) -> List[Optional[str]]:
    first = event.get("first_timestamp") or event.get("eventTime")
    last = event.get("last_timestamp") or event.get("eventTime")
    return [first, last] if first != last else [first]


def _parse_events(value: Optional[str]) -> List[Dict[str, Any]]:
    if not value:
        raise ValueError("events is required and must be a JSON array or an object containing an events array")
    parsed = json.loads(value)
    if isinstance(parsed, dict):
        parsed = parsed.get("events")
    if not isinstance(parsed, list):
        raise ValueError("events must be a JSON array or an object containing an events array")
    return [event for event in parsed if isinstance(event, dict)]


def _range(values: Iterable[Optional[str]]) -> Dict[str, Optional[str]]:
    timestamps = sorted(value for value in values if value)
    return {"first": timestamps[0] if timestamps else None, "last": timestamps[-1] if timestamps else None}


def analyze_cce_events_action(params: Dict[str, str]) -> Dict[str, Any]:
    """Aggregate current or historical Event records without a cloud request."""
    try:
        events = _parse_events(params.get("events"))
    except (ValueError, json.JSONDecodeError) as exc:
        return {"success": False, "error": str(exc)}

    try:
        max_groups = max(1, min(int(params.get("max_groups", "10")), 100))
    except ValueError:
        return {"success": False, "error": "max_groups must be an integer between 1 and 100"}

    reason_counts: Counter[str] = Counter()
    reason_warnings: Counter[str] = Counter()
    reason_times: Dict[str, List[Optional[str]]] = defaultdict(list)
    namespace_counts: Counter[str] = Counter()
    object_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    repeated_patterns: List[Dict[str, Any]] = []

    for event in events:
        event_type = str(event.get("type") or "Unknown")
        reason = str(event.get("reason") or "Unknown")
        namespace = str(event.get("namespace") or (event.get("involved_object") or {}).get("namespace") or "unknown")
        occurrences = _as_int(event.get("count"))
        involved_object = event.get("involved_object") or event.get("involvedObject") or {}
        if not isinstance(involved_object, dict):
            involved_object = {}
        object_key = "/".join(
            filter(
                None,
                (
                    namespace,
                    str(involved_object.get("kind") or "Unknown"),
                    str(involved_object.get("name") or "Unknown"),
                ),
            )
        )

        reason_counts[reason] += occurrences
        namespace_counts[namespace] += occurrences
        object_counts[object_key] += occurrences
        type_counts[event_type] += occurrences
        reason_times[reason].extend(_event_times(event))
        if event_type.lower() == "warning":
            reason_warnings[reason] += occurrences
        if occurrences > 1:
            repeated_patterns.append(
                {
                    "reason": reason,
                    "type": event_type,
                    "namespace": namespace,
                    "involved_object": involved_object or None,
                    "count": occurrences,
                    "first_timestamp": event.get("first_timestamp"),
                    "last_timestamp": event.get("last_timestamp"),
                }
            )

    top_reasons = [
        {
            "reason": reason,
            "count": count,
            "warning_count": reason_warnings[reason],
            "time_range": _range(reason_times[reason]),
        }
        for reason, count in reason_counts.most_common(max_groups)
    ]
    repeated_patterns.sort(key=lambda item: item["count"], reverse=True)

    return {
        "success": True,
        "source": params.get("source") or "provided_events",
        "event_records": len(events),
        "total_occurrences": sum(type_counts.values()),
        "event_type_breakdown": dict(type_counts.most_common()),
        "warning_count": type_counts.get("Warning", 0),
        "normal_count": type_counts.get("Normal", 0),
        "time_range": _range(timestamp for event in events for timestamp in _event_times(event)),
        "top_reasons": top_reasons,
        "namespace_breakdown": [
            {"namespace": namespace, "count": count}
            for namespace, count in namespace_counts.most_common(max_groups)
        ],
        "affected_objects": [
            {"object": object_key, "count": count}
            for object_key, count in object_counts.most_common(max_groups)
        ],
        "repeated_patterns": repeated_patterns[:max_groups],
    }
