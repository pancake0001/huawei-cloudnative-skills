# Workflow

1. Confirm the migration goals: same region, cross-region, multi-cluster, hybrid cloud, version upgrade or architecture adjustment.
2. Inventory the basic information of the source cluster, node pool, plug-ins, network model and key configurations.
3. Inventory the workload, Service, Ingress, PVC/PV, ConfigMap, and Secret.
4. Inventory associated cloud resources: VPC, subnet, security group, ELB, EIP, EVS, SFS.
5. Establish a dependency matrix: ingress traffic, service dependencies, storage dependencies, configuration dependencies, and external systems.
6. Design migration batches, verification points, fallback strategies, and downtime windows.
7. Output the plan without executing changes.