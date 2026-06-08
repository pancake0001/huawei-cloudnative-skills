# RiskRules

- Allow automatic execution of read-only diagnostic actions.
- It is prohibited to call expansion and contraction, workload deletion, node deletion, drain, and reboot in this skill.
- If `huawei_scale_cce_workload` or `huawei_resize_cce_workload` is suggested, it must be forwarded to `auto-remediation-runner`.
- The log can only output the desensitized tail fragment; do not copy the original text of the suspected password, token, AK/SK, and Authorization in the application log to the output.
- ImagePullBackOff gives priority to Events and does not repeatedly request container logs that do not exist.
- The suggestions for expansion, isolation, deletion and reconstruction given for OOMKilled, PendingScheduling and Evicted can only be recovery plans and are not executed in this skill.