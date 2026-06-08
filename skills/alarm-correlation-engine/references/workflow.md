# Workflow

1. Read the alarm name, resource, time window and severity level given by the user.
2. The last 1 hour is used by default; if the user describes a past fault, the window is expanded according to the user's time.
3. Call `huawei_list_aom_alarms`, don’t just check active_alert.
4. Call `huawei_analyze_aom_alarms` to form deduplication, burst, attention, and normal groups.
5. If the alarm is related to notification or silence, read the rules, action rules, and silence rules.
6. Merge by resource, namespace, node, workload, alarm type.
7. Output the Pod, Node, Network, or Workload objects that require continued diagnosis.