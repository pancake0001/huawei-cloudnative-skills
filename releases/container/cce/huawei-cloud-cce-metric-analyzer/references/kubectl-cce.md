# kubectl-cce Usage

Use `kubectl` only when the metric analyzer must read Kubernetes resources that AOM and hcloud cannot derive, such as Pod label filtering, Ingress TLS Secrets,
or LoadBalancer Services.

## Install & credentials

Install `kubectl` + `kubectl-cce` v0.2.1 and configure credentials (env-var or runtime `--cli-*` injection) per the canonical doc:
[huawei-cloud-kubectl-cce-installer plugin-usage.md](../../huawei-cloud-kubectl-cce-installer/references/plugin-usage.md).

## Runtime behavior (read-only)

- The LLM emits the bare command (no credential flags).
- Credential visibility is informational, never a gate — do not abort if env vars are not visible (sandbox injects at the runtime entry).
- On auth failure, localize per the table below; in the injection branch, never ask the user for AK/SK values.

## Credential / access failure localization

| Symptom                                  | env-var-mode cause                  | injection-mode cause                             | Action                                                                                                                     |
| ---------------------------------------- | ----------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `401` / `InvalidAK` / auth failed        | env vars not set / wrong            | runtime did not inject / injected expired values | env-var: set vars in the **execution** env; injection: check **runtime credential supply**, do not ask the user for values |
| plugin missing / `kubectl cce` not found | not installed                       | not installed (install env ≠ credential env)     | run the installer; not a credential issue                                                                                  |
| `403` permission denied                  | AK lacks IAM perms                  | injected AK lacks IAM perms                      | grant IAM; mode-independent                                                                                                |
| timeout / connection refused             | network / EIP / region              | runtime network egress                           | separate from auth (auth = `401`/`InvalidAK`; network = `timeout`/`refused`)                                               |
| region / project mismatch                | `HW_REGION` / `HW_PROJECT_ID` wrong | `--region` / `--project-id` or runtime misconfig | check region/project, not credentials                                                                                      |

## Use

```bash
kubectl cce --cluster-id <cluster-id> --region <region> get pods -A
kubectl cce --cluster-id <cluster-id> --region <region> get svc,ingress -A
```
