# CCE Pressure-Test Manifest Templates

These templates are starting points. Replace every placeholder before use. Show the final file to the user and apply it only after approval.

## Local k6 Script

```javascript
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: __VUS__,
  duration: "__DURATION__",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"]
  }
};

export default function () {
  const params = {
    headers: {
      "User-Agent": "cce-pressure-test-k6"
      // Add "Host": "__HOST_HEADER__" only when the Ingress requires it.
    }
  };
  const res = http.get("__TARGET_URL__", params);
  check(res, {
    "status is 2xx or expected": (r) => r.status >= 200 && r.status < 300
  });
  sleep(1);
}
```

Run only after approval:

```bash
k6 run --vus <vus> --duration <duration> <script.js>
```

## In-Cluster k6 Job

Use this when the target is only reachable from inside the cluster. Prefer a regional SWR image for k6 if Docker Hub pulls are unreliable.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: __K6_CONFIGMAP_NAME__
  namespace: __CLIENT_NAMESPACE__
data:
  script.js: |
    import http from "k6/http";
    import { check, sleep } from "k6";

    export const options = {
      vus: __VUS__,
      duration: "__DURATION__",
      thresholds: {
        http_req_failed: ["rate<0.01"],
        http_req_duration: ["p(95)<1000"]
      }
    };

    export default function () {
      const params = {
        headers: {
          "User-Agent": "cce-pressure-test-k6"
        }
      };
      const res = http.get("__TARGET_URL__", params);
      check(res, {
        "status is 2xx or expected": (r) => r.status >= 200 && r.status < 300
      });
      sleep(1);
    }
---
apiVersion: batch/v1
kind: Job
metadata:
  name: __K6_JOB_NAME__
  namespace: __CLIENT_NAMESPACE__
  labels:
    app.kubernetes.io/name: cce-pressure-test-k6
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: cce-pressure-test-k6
    spec:
      restartPolicy: Never
      containers:
        - name: k6
          image: __K6_IMAGE__
          imagePullPolicy: IfNotPresent
          command: ["k6", "run", "/scripts/script.js"]
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "1"
              memory: "512Mi"
          volumeMounts:
            - name: k6-script
              mountPath: /scripts
      volumes:
        - name: k6-script
          configMap:
            name: __K6_CONFIGMAP_NAME__
```

Approved execution:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> apply -f <approved-k6-manifest.yaml>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> wait --for=condition=complete job/<job-name> -n <client-namespace> --timeout=<timeout>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> logs job/<job-name> -n <client-namespace> --all-containers
```

If the target needs a Host header, add it to the k6 script headers before approval.

## Service Template

Use only when an existing Service is unavailable or unsuitable, and only after approval.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: __SERVICE_NAME__
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/managed-by: cce-pressure-test
spec:
  type: ClusterIP
  selector:
    __LABEL_KEY__: __LABEL_VALUE__
  ports:
    - name: http
      port: __SERVICE_PORT__
      targetPort: __TARGET_PORT__
      protocol: TCP
```

## Ingress Template

Use only when the ingress controller and route policy are understood and approved.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: __INGRESS_NAME__
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/managed-by: cce-pressure-test
  annotations:
    kubernetes.io/ingress.class: __INGRESS_CLASS__
spec:
  rules:
    - host: __HOST__
      http:
        paths:
          - path: __PATH__
            pathType: Prefix
            backend:
              service:
                name: __SERVICE_NAME__
                port:
                  number: __SERVICE_PORT__
```

## Cleanup Template

Cleanup requires approval. Only delete resources created for this test:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> delete job/<job-name> -n <client-namespace>
kubectl cce --cluster-id <cluster-id> --region <region> --project-id <project-id> delete configmap/<configmap-name> -n <client-namespace>
```

Do not delete existing workloads, Services, Ingresses, namespaces, ELBs, EIPs, or security/network resources automatically.
