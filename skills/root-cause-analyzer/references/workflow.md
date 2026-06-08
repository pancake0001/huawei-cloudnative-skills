# Workflow

1. Establish a fault timeline: user perception time, alarm triggering time, Kubernetes event time, release/configuration change time.
2. It is preferred to call `huawei_root_cause_analyze`; if drill-down is required, call rollout, dependency, change, network, node/pod diagnoser respectively.
3. Workload release funnel has the highest priority: generation/observedGeneration, ReplicaSet, Pod Ready, events, logs, command/args, probes, and mirrors.
4. Dependency influence surface uses Service selector, Ingress backend, Pod Ready and Node distribution to determine the propagation path.
5. Use audit logs, K8s historical events, AOM alarms and current topology to verify the cause and effect chain of "failure after change" on the impact of the change.
6. Record supporting evidence, counter-evidence, data gaps and recovery handovers for each root cause candidate.
7. Sort by scope of impact, time consistency, evidence strength, and recoverability.
8. Output the Top 3 root causes, verification steps, impact areas and recovery suggestions.
9. Clearly label low-confidence conclusions that require supplementary data.