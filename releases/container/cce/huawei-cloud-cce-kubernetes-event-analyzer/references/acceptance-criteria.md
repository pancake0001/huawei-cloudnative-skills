# Acceptance Criteria

## Current Events

- The skill uses `kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> get events ...`.
- The result includes event counts, Warning counts, top reasons, affected namespaces/resources, repeated patterns, and representative sanitized samples when Events exist.
- Namespace, reason, type, keyword, and time-window filters are reflected in the report.

## Historical Events

- Historical LTS queries are attempted only after discovering a `default-event` LogConfig or receiving explicit LTS IDs.
- The query is bounded by start and end time.
- Missing LogConfig, missing LTS IDs, or unavailable LTS permissions are reported as data gaps.

## Analysis Quality

- Event patterns are mapped to likely diagnosis handoff skills.
- Current Event retention limits are stated when the incident is older than available Events.
- No mutation command, generated kubeconfig, SDK dispatcher, or raw SDK access is used.
