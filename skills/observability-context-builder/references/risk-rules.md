# RiskRules

- Allows automatic invocation of R1 read-only queries: alarms, indicators, logs, events, lists, and read-only report generation.
- Disable calling any change action that requires `confirm=true`.
- Do not save AK/SK, token, certificate, kubeconfig.
- The log output must be desensitized. When a suspected key is encountered, only the hit location will be described, and the original text will not be copied.
- Charts and reports can only be generated based on authorized query results.