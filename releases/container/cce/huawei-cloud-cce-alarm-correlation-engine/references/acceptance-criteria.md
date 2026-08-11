# Acceptance Criteria

## Functional

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| AC-01 | Skill activation | Activates for AOM alarm, CCE alarm, alarm storm, and alarm correlation requests |
| AC-02 | Active and historical alarms | Queries or records a clear data gap for both active and historical alarm evidence |
| AC-03 | Alarm grouping | Groups alarms by severity, resource, type, and time proximity |
| AC-04 | Handoff | Maps alarm groups to Pod, workload, node, network, storage, metric, event, or root-cause follow-up |
| AC-05 | Notification context | Queries rules/action/mute data only when needed to explain notifications |

## Safety

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| SAF-01 | Read-only | No alarm rule or notification mutation commands are used |
| SAF-02 | Credential safety | No AK/SK, tokens, Authorization headers, or signed payloads are printed |
| SAF-03 | Evidence caution | Absence of active alarms is not treated as proof of health |
| SAF-04 | Confidence | High-confidence claims require corroborating evidence |

## Documentation

| ID | Acceptance Item | Pass Criteria |
| -- | --------------- | ------------- |
| DOC-01 | CLI mode | Documentation uses `hcloud` commands directly |
| DOC-02 | No dispatcher | Documentation does not instruct legacy dispatcher actions |
| DOC-03 | Report format | Summary, root-cause signal, and next actions appear before raw evidence |
