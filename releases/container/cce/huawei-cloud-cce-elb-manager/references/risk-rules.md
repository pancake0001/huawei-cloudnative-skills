# ELB Manager Risk Rules

Risk levels follow the current CCE remediation convention:

| Risk | Meaning | ELB manager usage |
|------|---------|-------------------|
| R3 | Read-only operation | `huawei_list_elb` |
| R2 | Low-risk operation that does not involve cost | Not used |
| R1 | Medium-risk operation | Not used |
| R0 | High-risk operation | `huawei_resize_elb_flavor` |

`huawei_resize_elb_flavor` is R0 because changing ELB L4/L7 flavor may affect public entry capacity, cost, and traffic behavior. The action must return preview output unless `confirm=true` is provided after explicit user authorization.
