# kubectl-cce

`kubectl-cce` is a Go kubectl plugin that starts a short-lived local reverse
proxy, adds Huawei Cloud CCE authentication, runs the real `kubectl`, and then
shuts the proxy down.

The plugin does not hard-code pods. It lets the real `kubectl` perform normal
Kubernetes discovery and resource mapping, so normal REST-style resources such
as namespaces, nodes, pods, deployments, services, configmaps, secrets,
ingresses, PVs, PVCs, jobs, cronjobs, roles, and CRDs use the same command shape
as upstream kubectl.

## Install

```bash
go build -o kubectl-cce ./cmd/kubectl-cce
export PATH="$PWD:$PATH"
kubectl plugin list
```

kubectl discovers the plugin because the executable is named `kubectl-cce`.

## Configure

AK/SK is preferred when both AK and SK are present:

```bash
export CCE_CLUSTER_ID="your-cluster-id"
export CCE_REGION="cn-north-4"
export CCE_PROJECT_ID="your-project-id" # optional, but recommended for AK/SK
export HUAWEICLOUD_SDK_AK="your-ak"
export HUAWEICLOUD_SDK_SK="your-sk"
```

For a temporary AK/SK, also set:

```bash
export HUAWEICLOUD_SECURITY_TOKEN="your-security-token"
```

If Huawei Cloud returns an AK/SK authentication or signature error, enable
debug output to inspect the canonical request and string-to-sign:

```bash
export CCE_PROXY_DEBUG=1
kubectl cce get ns
```

If AK/SK is not set, the plugin can fall back to an IAM token:

```bash
export HUAWEI_IAM_TOKEN="your-iam-token"
```

You can override the target host directly:

```bash
export CCE_ENDPOINT="your-cluster-id.cce.cn-north-4.myhuaweicloud.com"
```

## Usage

```bash
kubectl cce get pods -n default
kubectl cce get pods -A
kubectl cce get ns
kubectl cce get nodes
kubectl cce get svc,deploy,cm -n default
kubectl cce get ingress -A
kubectl cce get pv,pvc -A
kubectl cce get jobs,cronjobs -A
kubectl cce get crd
kubectl cce get deployments -n default -o yaml
kubectl cce describe pod nginx -n default
kubectl cce logs nginx -n default
```

The plugin internally runs something like:

```bash
kubectl \
  --server=http://127.0.0.1:<random-port> \
  --insecure-skip-tls-verify=true \
  --kubeconfig=/dev/null \
  get pods -n default
```

## Current Limitations

This MVP targets normal REST-style kubectl calls. Streaming commands such as
`exec`, `attach`, and `port-forward` are intentionally blocked because CCE API
Gateway does not reliably pass the websocket/SPDY upgrade required by these
commands.

`logs -f` and `watch` may work depending on the CCE API gateway behavior, but
they have not been hardened yet.
