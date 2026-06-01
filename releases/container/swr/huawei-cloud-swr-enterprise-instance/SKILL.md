---
name: huawei-cloud-swr-enterprise-instance
description: |
  Manages Huawei Cloud SWR enterprise instances, namespaces, registries, repositories, artifacts, credentials, endpoints, domains, and statistics via hcloud CLI.
  Trigger: "SWR enterprise instance", "SWR 企业实例", "企业仓库", "SWR 企业版", "swr.ee", "实例管理", "instance namespace/registry/credential/endpoint/domain"
tags: [swr, enterprise-instance, container-registry, registry, domain]
---

# Huawei Cloud SWR Enterprise Instance Management

## Overview

This skill provides lifecycle management capabilities for Huawei Cloud SWR (Software Repository for Container)
enterprise instances using the `hcloud` CLI. Enterprise instances provide dedicated, isolated container registry
environments with advanced features like security scanning, replication policies, and custom domain support.

**Architecture**: hcloud CLI → SWR Service API → Instance/Namespace/Registry/Repository/Artifact/Credential/Endpoint/Domain resources

**Related Skills**:

- `huawei-cloud-swr-image-management` - Image lifecycle management (basic SWR namespaces, repos, tags, auth, quotas)
- `huawei-cloud-swr-image-governance` - Image governance (permissions, retention, sharing, tags, immutable rules)
- `huawei-cloud-swr-image-automation` - Image automation ops (sync, triggers, domains)

- Create and manage SWR enterprise instances
- Manage instance namespaces with security scanning and vulnerability blocking
- Configure instance registries for cross-instance image sync
- Query and manage instance repositories and artifacts
- Obtain instance access credentials (long-term and temporary)
- Configure instance network access (internal VPC endpoints, public access with whitelist)
- Manage custom domains for instance access
- Monitor instance statistics and job status

**Typical Use Cases**:

- "Create an SWR enterprise instance for my organization"
- "List all enterprise instances in my project"
- "Create a namespace with auto-scan and vulnerability blocking"
- "Configure a registry for syncing images to another instance"
- "List repositories and artifacts in my instance"
- "Get docker login credentials for my instance"
- "Add a VPC internal endpoint for my instance"
- "Enable public access with IP whitelist"
- "Add a custom domain to my instance"
- "Check instance statistics and resource usage"

## Prerequisites

### 0. Enterprise Repository Service Authorization (MANDATORY)

Before using this skill, you **must** first authorize the SWR Enterprise Repository feature on the Huawei Cloud console. Without this authorization, all enterprise instance API operations will fail.

**Authorization Link**: [https://console.huaweicloud.com/swr-instance](https://console.huaweicloud.com/swr-instance)

**Steps**:

1. Log in to the Huawei Cloud console
2. Visit the SWR enterprise repository console at the link above
3. Complete the service authorization process (grant SWR the necessary service permissions)
4. Confirm the authorization is successful before proceeding with any CLI operations

**Authorization Failure Handling**:

- If any API call returns an authorization-related error, direct the user to visit the authorization link above
- Pause execution and wait for the user to confirm authorization is complete

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

- Valid Huawei Cloud credentials (AK/SK mode)
- **Security Rules**:
  - 🚫 Never expose AK/SK values in code, conversation, or commands
  - 🚫 Never use `echo $HUAWEI_CLOUD_AK` or `echo $HUAWEI_CLOUD_SK` to check credentials
  - ✅ Use environment variables: `HUAWEI_CLOUD_AK`, `HUAWEI_CLOUD_SK`, `HUAWEI_CLOUD_REGION`
  - ✅ Prefer IAM users over root account for cloud operations
  - ✅ Enable MFA for sensitive operations

**Configuration Method** (Environment Variables Only):

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**⚠️ Important Security Notes**:

- Never commit credentials to version control
- Use IAM users with minimal required permissions
- Enable MFA for sensitive operations
- Rotate AK/SK regularly

### 3. IAM Permission Requirements

| Resource | Permissions |
| -------- | ----------- |
| Instance | `swr:instance:create/list/get/update/delete` |
| Namespace | `swr:instanceNamespace:create/list/get/update/delete` |
| Registry | `swr:instanceRegistry:create/list/get/update/delete` |
| Repository | `swr:instanceRepository:list/get/update/delete` |
| Artifact | `swr:instanceArtifact:list/get/delete/scan` |
| Credential | `swr:instanceCredential:create/list/update/delete` |
| Endpoint | `swr:instanceEndpoint:create/list/get/delete/update` |
| Domain | `swr:instanceDomain:add/list/get/delete/update` |
| Job/Statistic | `swr:instanceJob:list/get/delete`, `swr:instanceStatistic:get` |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Instance Lifecycle

See [Task: Instance Lifecycle](references/task-instance-lifecycle.md) for detailed workflows.

**⚠️ hcloud CLI CreateInstance Bug**: The `hcloud SWR CreateInstance` command has a known bug where the
`--project_id` parameter appears twice (path and body) with the same name. hcloud CLI rejects duplicate
parameter names (`重复的参数:project_id`), making it impossible to use hcloud CLI for instance creation.
Use the Python SDK script as an alternative:

```bash
# ✅ CORRECT - Use Python SDK script for CreateInstance (bypasses hcloud bug)
python scripts/swr_instance_helper.py create --name=my-instance --spec=swr.ee.basic \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> \
    --enterprise_project_id=0 --description="My enterprise registry"

# ❌ BROKEN - hcloud CLI CreateInstance fails due to duplicate --project_id bug
# hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.professional ...

# Other instance lifecycle commands work fine with hcloud CLI

# List all instances
hcloud SWR ListInstance --cli-region=cn-north-4

# List instances with status filter
hcloud SWR ListInstance --status=Running --cli-region=cn-north-4

# Show instance details
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4

# View instance configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4

# Update instance configuration (anonymous access)
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4

# Delete instance (CAUTION: removes all data permanently)
hcloud SWR DeleteInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

**Instance Naming Rules**:

- Start with lowercase letter
- Followed by lowercase letters, digits, or hyphens (`-`)
- No consecutive hyphens
- Cannot end with hyphen
- Length: 3-48 characters

**Instance Spec Options**: `swr.ee.basic` (basic edition), `swr.ee.professional` (professional edition)

**Instance Status Values**: `Initial`, `Creating`, `Running`, `Unavailable`

### 2. Instance Namespaces

See [Task: Instance Namespaces](references/task-instance-namespaces.md) for detailed workflows.

```bash
# Create namespace with auto-scan and vulnerability blocking
hcloud SWR CreateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4
# List / Show / Update / Delete — see task reference for full commands
```

**Namespace Naming**: lowercase/digit start, 1-64 chars. **Severity**: `none`/`low`/`medium`/`high`/`critical`

### 3. Instance Registries (Sync Targets)

See [Task: Instance Registries](references/task-instance-registries.md) for detailed workflows.

```bash
# Create a sync target registry
hcloud SWR CreateInstanceRegistry --instance_id=<id> --name=target --type=swr-pro-internal --url=<url> --credential.type=basic --credential.access_key=<ak> --credential.access_secret=<sk> --cli-region=cn-north-4
# List / Show / Update / Delete — see task reference for full commands
```

**Registry Types**: `swr-pro` (Harbor), `swr-pro-internal` (SWR enterprise), `huawei-SWR` (basic SWR)

### 4. Instance Repositories

See [Task: Instance Registries](references/task-instance-registries.md) for repository section.

```bash
hcloud SWR ListInstanceRepositories --instance_id=<id> --cli-region=cn-north-4  # List repos
hcloud SWR ShowInstanceRepository --instance_id=<id> --namespace_name=<ns> --repository_name=<repo> --cli-region=cn-north-4  # Show details
# Update / Delete — see task reference
```

### 5. Instance Artifacts (Image Versions)

See [Task: Instance Artifacts](references/task-instance-artifacts.md) for detailed workflows.

```bash
hcloud SWR ListInstanceArtifacts --instance_id=<id> --namespace_name=<ns> --repository_name=<repo> --cli-region=cn-north-4
hcloud SWR ShowInstanceArtifact --instance_id=<id> --namespace_name=<ns> --repository_name=<repo> --reference=<digest> --with_scan_overview=true --cli-region=cn-north-4
hcloud SWR StartManualScanning --instance_id=<id> --namespace_name=<ns> --repository_name=<repo> --reference=<digest> --cli-region=cn-north-4
# Delete / Vulnerabilities / Build history — see task reference
```

**Artifact Types**: `IMAGE` (container image), `CHART` (Helm chart)

### 6. Instance Credentials

See [Task: Instance Credentials](references/task-instance-credentials.md) for detailed workflows.

```bash
hcloud SWR CreateInstanceLtCredential --instance_id=<id> --name=my-credential --cli-region=cn-north-4  # Long-term
hcloud SWR CreateInstanceTempCredential --instance_id=<id> --cli-region=cn-north-4  # Temporary
# List / Enable/disable / Delete — see task reference
```

**Naming**: lowercase/digit start, 1-64 chars

### 7. Instance Endpoints (Network Access)

See [Task: Instance Endpoints](references/task-instance-endpoints.md) for detailed workflows.

```bash
# Internal VPC endpoint
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<id> --vpc_id=<vpc> --subnet_id=<subnet> --cli-region=cn-north-4
# Public access enable/disable + whitelist — see task reference
```

### 8. Instance Domains

See [Task: Instance Domains](references/task-instance-domains.md) for detailed workflows.

```bash
hcloud SWR AddDomainName --instance_id=<id> --domain_name=registry.example.com --certificate_id=<cert-id> --cli-region=cn-north-4
hcloud SWR ListDomainNames --instance_id=<id> --cli-region=cn-north-4
# Show overview / Delete / Update certificate — see task reference
```

### 9. Instance Statistics and Jobs

```bash
hcloud SWR ListInstanceStatistics --instance_id=<id> --cli-region=cn-north-4  # Statistics
hcloud SWR ListInstanceJobs --cli-region=cn-north-4  # Async jobs
hcloud SWR ShowInstanceJob --job_id=<job-id> --cli-region=cn-north-4  # Job details
```

## Parameter Reference

| Parameter       | Required | Description                   | Default                              |
| --------------- | -------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Yes      | Huawei Cloud region ID        | `HUAWEI_CLOUD_REGION`                |
| `--instance_id` | Context  | Enterprise instance ID        | N/A                                  |
| `--project_id`  | Auto     | Project ID                    | Auto from credentials                |

See task reference docs for detailed per-resource parameters (Instance Creation, Namespace, Registry, Endpoint Whitelist).

## Output Format

See [Output Format](references/output-format.md) for detailed response format examples (Instance List, Instance Details, Namespace List, Internal Endpoint List, Domain Name List, Long-term Credential).

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. Enable `auto_scan=true` + `prevent_vul=true` for production namespaces; set `severity=high`/`critical`
2. Store registry credentials securely; rotate access keys periodically
3. Configure IP whitelist when enabling public access
4. Use `CreateInstanceLtCredential` for CI/CD; `CreateInstanceTempCredential` for temporary access
5. Use `swr.ee.basic` for small teams; `swr.ee.professional` for enterprise requirements

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR Instance API Guide](references/swr-instance-api-guide.md) | hcloud SWR instance API reference |
| [SDK Helper Script](scripts/swr_instance_helper.py) | Python SDK wrapper for CreateInstance (bypasses hcloud CLI bug) |
| [Output Format](references/output-format.md)          | Response format examples (Instance, Namespace, Endpoint, Domain, Credential) |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Instance Lifecycle](references/task-instance-lifecycle.md) | Instance create, list, show, update config |
| [Task: Instance Namespaces](references/task-instance-namespaces.md) | Namespace CRUD workflows |
| [Task: Instance Registries](references/task-instance-registries.md) | Registry CRUD and repositories |
| [Task: Instance Artifacts](references/task-instance-artifacts.md) | Artifact management and scanning |
| [Task: Instance Credentials](references/task-instance-credentials.md) | Credential management workflows |
| [Task: Instance Endpoints](references/task-instance-endpoints.md) | Internal and public access configuration |
| [Task: Instance Domains](references/task-instance-domains.md) | Custom domain management |

## Notes

- **Instance/namespace/artifact deletion is irreversible** — removes ALL data permanently
- **Default domain cannot be deleted** — only custom domains can be removed
- **AK/SK must never be hardcoded** — use environment variables only
- **hcloud CLI CreateInstance bug** — use Python SDK script (`scripts/swr_instance_helper.py`) instead
- **Pagination**: `offset` must be 0 or a multiple of `limit`
- **Registry credential.access_secret is sensitive** — never expose or log

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                         | Quick Fix                                    |
| ------------------------------- | -------------------------------------------- |
| Invalid instance name           | 3-48 chars, lowercase start, no consecutive hyphens |
| Instance still creating         | Wait for Running, check with ListInstance    |
| Offset not multiple of limit    | offset must be 0 or multiple of limit        |
| hcloud CreateInstance bug      | Use Python SDK `swr_instance_helper.py create` |
| Public access whitelist format  | Use indexed: `--ip_list.1.ip=value`          |
| SWR service quota exceeded     | Contact SWR team to expand quota             |