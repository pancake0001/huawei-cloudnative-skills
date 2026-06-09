# Risk Rules

- Inspection allows only read-only actions.
- Prohibited mutation actions: auto-scaling, deletion, drain, reboot, hibernate, awake.
- Inspection reports must never contain AK/SK, tokens, certificates, or full kubeconfig.
- After anomalies are found, inspection evidence must be handed to `huawei-cloud-cce-root-cause-analyzer` before remediation is selected.
- Recovery advice, previews, and customer-authorized recovery actions must be handled by `huawei-cloud-cce-auto-remediation-runner`.
