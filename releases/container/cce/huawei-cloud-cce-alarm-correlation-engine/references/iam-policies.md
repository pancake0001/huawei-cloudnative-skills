# IAM Policies

This read-only skill needs only query permissions.

| Permission | Purpose |
| ---------- | ------- |
| `aom:event:list` | Query active and historical alarms |
| `aom:alarmRule:list` | Query alarm rules when notification context is needed |
| `aom:actionRule:list` | Query notification action rules |
| `aom:muteRule:list` | Query mute rules |
| `cce:cluster:get` | Resolve CCE cluster context |
| `iam:projects:list` | Resolve project ID for a region when needed |

Do not request create, update, enable, disable, or delete permissions for root-cause alarm correlation.
