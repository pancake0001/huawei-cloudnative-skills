#!/usr/bin/env python3
"""
Transform skill from development structure to release structure.

Usage:
    python scripts/dev/transform_for_release.py \
        --skill huawei-cloud-cce-cluster-management \
        --target D:\\code\\huaweicloud-skills\\skills

Transformations:
    1. Infer domain/subdomain from skill name
    2. Translate SKILL.md (Chinese -> English)
    3. Copy scripts based on action-to-module mapping
    4. Prune dispatcher.py to skill-specific actions
    5. Delete manifest.json
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

DOMAIN_MAPPING = {
    "cce": ("containers", "cce"),
    "obs": ("storage", "obs"),
    "evs": ("storage", "evs"),
    "sfs": ("storage", "sfs"),
    "eip": ("network", "eip"),
    "elb": ("network", "elb"),
    "nat": ("network", "nat"),
    "vpc": ("network", "vpc"),
    "ecs": ("compute", "ecs"),
    "iam": ("security", "iam"),
    "hss": ("security", "hss"),
    "aom": ("monitor", "aom"),
    "lts": ("monitor", "lts"),
    "ces": ("monitor", "ces"),
}

ACTION_TO_MODULE = {
    "cluster": "cce_cluster.py",
    "nodepool": "cce_nodepool.py",
    "node": "cce_node.py",
    "addon": "cce_addon.py",
    "pod": "cce_k8s.py",
    "namespace": "cce_k8s.py",
    "deployment": "cce_k8s.py",
    "service": "cce_k8s.py",
    "ingress": "cce_k8s.py",
    "pvc": "cce_k8s.py",
    "pv": "cce_k8s.py",
    "configmap": "cce_k8s.py",
    "secret": "cce_k8s.py",
    "daemonset": "cce_k8s.py",
    "statefulset": "cce_k8s.py",
    "cronjob": "cce_k8s.py",
    "event": "cce_k8s.py",
    "workload": "cce_k8s.py",
    "kubeconfig": "cce_cluster.py",
    "hibernate": "cce_cluster.py",
    "awake": "cce_cluster.py",
    "eip": "cce_cluster.py",
    "vpc": "network.py",
    "subnet": "network.py",
}


def infer_domain_subdomain(skill_name: str) -> Tuple[str, str]:
    match = re.match(r"huawei-cloud-(\w+)-(\w+)-.*", skill_name)
    if not match:
        raise ValueError(f"Cannot infer domain from skill name: {skill_name}")
    service = match.group(1)
    if service in DOMAIN_MAPPING:
        return DOMAIN_MAPPING[service]
    raise ValueError(f"Unknown service '{service}' in skill name: {skill_name}")


def get_required_modules(actions: List[str]) -> Set[str]:
    """Infer required modules from action names."""
    modules = set()
    modules.add("common.py")
    modules.add("dispatcher.py")
    modules.add("__init__.py")
    
    for action in actions:
        action_lower = action.lower()
        for keyword, module in ACTION_TO_MODULE.items():
            if keyword in action_lower:
                modules.add(module)
                break
    
    return modules


def load_skill_manifest(skill_dir: Path) -> Dict:
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {skill_dir}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_tool_actions(manifest: Dict) -> List[str]:
    actions = []
    for tool in manifest.get("tools", []):
        name = tool.get("name", "")
        actions.append(name)
    return actions


def translate_skill_md(content: str) -> str:
    translations = {
        "技能名称": "Skill Name",
        "技能描述": "Skill Description",
        "工具列表": "Tool List",
        "参数": "Parameters",
        "返回值": "Return Value",
        "示例": "Example",
        "注意事项": "Notes",
        "前置条件": "Prerequisites",
        "依赖": "Dependencies",
        "功能": "Function",
        "区域": "Region",
        "集群": "Cluster",
        "节点池": "Node Pool",
        "节点": "Node",
        "插件": "Addon",
        "工作负载": "Workload",
        "命名空间": "Namespace",
        "容器": "Container",
        "镜像": "Image",
        "标签": "Label",
        "注解": "Annotation",
        "配置": "Configuration",
        "状态": "Status",
        "创建": "Create",
        "查询": "Query/List",
        "删除": "Delete",
        "更新": "Update",
        "扩缩容": "Scale",
        "休眠": "Hibernate",
        "唤醒": "Awake",
        "绑定": "Bind",
        "解绑": "Unbind",
        "获取": "Get",
        "列表": "List",
        "详情": "Details",
        "指标": "Metrics",
        "日志": "Logs",
        "事件": "Events",
        "告警": "Alerts",
        "异常": "Exception/Error",
        "成功": "Success",
        "失败": "Failure",
        "必填": "Required",
        "可选": "Optional",
        "默认": "Default",
        "类型": "Type",
        "说明": "Description",
        "华为云": "Huawei Cloud",
        "容器引擎": "Cloud Container Engine",
        "集群管理": "Cluster Management",
        "节点管理": "Node Management",
        "插件管理": "Addon Management",
        "版本": "Version",
        "规格": "Flavor/Specification",
        "网络": "Network",
        "存储": "Storage",
        "安全": "Security",
        "权限": "Permission",
        "策略": "Policy",
        "项目": "Project",
        "企业项目": "Enterprise Project",
        "可用区": "Availability Zone",
        "子网": "Subnet",
        "虚拟私有云": "Virtual Private Cloud",
        "弹性公网IP": "Elastic IP",
        "云服务器": "Elastic Cloud Server",
        "云硬盘": "Elastic Volume Service",
        "对象存储": "Object Storage Service",
        "文件存储": "Scalable File Service",
        "身份与访问管理": "Identity and Access Management",
        "主机安全": "Host Security Service",
        "应用运维管理": "Application Operation Management",
        "监控": "Cloud Eye Service",
        "日志服务": "Log Tank Service",
        "是": "Yes",
        "否": "No",
        "无": "None",
        "名称": "Name",
        "ID": "ID",
        "数量": "Count",
        "大小": "Size",
        "时间": "Time",
        "操作": "Operation",
    }
    
    result = content
    for cn, en in translations.items():
        result = result.replace(cn, en)
    return result


def prune_dispatcher(dispatcher_content: str, actions: List[str]) -> str:
    """Prune dispatcher.py to only include skill-specific actions."""
    action_set = set(actions)
    lines = dispatcher_content.split("\n")
    result_lines = []
    
    for line in lines[:30]:
        if "from . import" in line:
            continue
        result_lines.append(line)
    
    required_modules = get_required_modules(actions)
    cce_modules = [m.replace(".py", "") for m in required_modules if m not in ["dispatcher.py", "__init__.py", "network.py", "common.py"]]
    
    imports = f"from . import common, {', '.join(cce_modules)}"
    if "network.py" in required_modules:
        imports += ", network"
    result_lines.append(imports)
    result_lines.append("")
    
    if cce_modules:
        result_lines.append("# Compatibility shim: aggregate split modules into 'cce'")
        result_lines.append("import types")
        result_lines.append("cce = types.SimpleNamespace(")
        
        shim_map = {
            "list_cce_clusters": "cce_cluster.list_cce_clusters",
            "delete_cce_cluster": "cce_cluster.delete_cce_cluster",
            "get_cce_nodes": "cce_cluster.get_cce_nodes",
            "get_cce_kubeconfig": "cce_cluster.get_cce_kubeconfig",
            "hibernate_cce_cluster": "cce_cluster.hibernate_cce_cluster",
            "awake_cce_cluster": "cce_cluster.awake_cce_cluster",
            "bind_cce_cluster_eip": "cce_cluster.bind_cce_cluster_eip",
            "unbind_cce_cluster_eip": "cce_cluster.unbind_cce_cluster_eip",
            "create_cce_cluster": "cce_cluster.create_cce_cluster",
            "list_cce_node_pools": "cce_nodepool.list_cce_node_pools",
            "resize_node_pool": "cce_nodepool.resize_node_pool",
            "create_node_pool": "cce_nodepool.create_node_pool",
            "delete_node_pool": "cce_nodepool.delete_node_pool",
            "list_cce_cluster_nodes": "cce_node.list_cce_nodes",
            "delete_cce_node": "cce_node.delete_cce_node",
            "create_cce_node": "cce_node.create_cce_node",
            "cce_node_cordon": "cce_node.cce_node_cordon",
            "cce_node_uncordon": "cce_node.cce_node_uncordon",
            "cce_node_drain": "cce_node.cce_node_drain",
            "cce_node_status": "cce_node.cce_node_status",
            "list_cce_addons": "cce_addon.list_cce_addons",
            "get_cce_addon_detail": "cce_addon.get_cce_addon_detail",
            "install_cce_addon": "cce_addon.install_cce_addon",
            "uninstall_cce_addon": "cce_addon.uninstall_cce_addon",
            "update_cce_addon": "cce_addon.update_cce_addon",
        }
        
        for action_lower, func_ref in shim_map.items():
            result_lines.append(f"    {action_lower}={func_ref},")
        
        result_lines.append(")")
        result_lines.append("")
    
    for i, line in enumerate(lines):
        if i < 30:
            continue
        if line.strip().startswith("from . import"):
            continue
        if '"huawei_' in line and ": ((" in line:
            action_match = re.search(r'"(huawei_\w+)"', line)
            if action_match and action_match.group(1) in action_set:
                result_lines.append(line)
            continue
        if line.strip() == "}":
            result_lines.append(line)
            continue
        result_lines.append(line)
    
    return "\n".join(result_lines)


def prune_huawei_cloud_py(content: str, required_modules: Set[str]) -> str:
    """Prune huawei-cloud.py imports."""
    available = {m.replace(".py", "") for m in required_modules}
    
    all_modules = ["aom", "cce", "ecs", "elb", "identity", "cce_metrics", "storage",
                   "cce_inspection", "cce_diagnosis", "cce_app_logs", "hss", "lts",
                   "report_generator", "chart_generator", "cce_auto_inspection",
                   "cce_cluster", "cce_nodepool", "cce_node", "cce_addon", "cce_k8s",
                   "network", "common"]
    
    unavailable = [m for m in all_modules if m not in available]
    
    lines = content.split("\n")
    result_lines = []
    
    for line in lines:
        skip = False
        for m in unavailable:
            if f"from huawei_cloud import {m}" in line:
                result_lines.append(f"    # {line.strip()}  # Pruned")
                skip = True
                break
            if f"_{m}_mod" in line or f"_{m.replace('cce_', '')}_mod" in line:
                result_lines.append(f"    # {line.strip()}  # Pruned")
                skip = True
                break
        if not skip:
            result_lines.append(line)
    
    return "\n".join(result_lines)


def transform_skill(skill_name: str, target_dir: Path) -> Path:
    source_dir = Path("skills") / skill_name
    if not source_dir.exists():
        raise FileNotFoundError(f"Skill directory not found: {source_dir}")
    
    domain, subdomain = infer_domain_subdomain(skill_name)
    output_dir = target_dir / domain / subdomain / skill_name
    
    print(f"Transforming: {source_dir}")
    print(f"  -> {output_dir}")
    print(f"  Domain/Subdomain: {domain}/{subdomain}")
    
    if output_dir.exists():
        print(f"  WARNING: Output directory exists, removing...")
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = load_skill_manifest(source_dir)
    actions = get_tool_actions(manifest)
    required_modules = get_required_modules(actions)
    
    print(f"  Actions: {len(actions)}")
    print(f"  Required modules: {sorted(required_modules)}")
    
    for item in source_dir.iterdir():
        item_name = item.name
        
        if item_name == "manifest.json":
            continue
        
        if item_name == "SKILL.md":
            with open(item, "r", encoding="utf-8") as f:
                cn_content = f.read()
            with open(output_dir / "SKILL-CN.md", "w", encoding="utf-8") as f:
                f.write(cn_content)
            skill_en_path = source_dir / "SKILL-EN.md"
            if skill_en_path.exists():
                with open(skill_en_path, "r", encoding="utf-8") as f:
                    en_content = f.read()
                with open(output_dir / "SKILL.md", "w", encoding="utf-8") as f:
                    f.write(en_content)
                print(f"  Created SKILL-CN.md (Chinese) and SKILL.md (English from SKILL-EN.md)")
            else:
                with open(output_dir / "SKILL.md", "w", encoding="utf-8") as f:
                    f.write("# Huawei Cloud CCE Cluster Management\n\n[Chinese Version: SKILL-CN.md]\n\n**TODO: Translate from SKILL-CN.md using LLM or manual translation.**\n\nFor now, please refer to SKILL-CN.md for the complete documentation.\n")
                print(f"  Created SKILL-CN.md (Chinese) and placeholder SKILL.md (English)")
            continue
        
        if item_name == "scripts":
            scripts_output = output_dir / "scripts"
            scripts_output.mkdir(parents=True, exist_ok=True)
            huawei_cloud_output = scripts_output / "huawei_cloud"
            huawei_cloud_output.mkdir(parents=True, exist_ok=True)
            
            if os.path.islink(item):
                scripts_source = Path(os.path.realpath(item))
            else:
                scripts_source = item
            
            with open(scripts_source / "huawei-cloud.py", "r", encoding="utf-8") as f:
                content = f.read()
            pruned = prune_huawei_cloud_py(content, required_modules)
            with open(scripts_output / "huawei-cloud.py", "w", encoding="utf-8") as f:
                f.write(pruned)
            print(f"  Pruned huawei-cloud.py")
            
            huawei_cloud_source = scripts_source / "huawei_cloud"
            for module_file in required_modules:
                src_file = huawei_cloud_source / module_file
                if src_file.exists():
                    if module_file == "dispatcher.py":
                        with open(src_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        pruned = prune_dispatcher(content, actions)
                        with open(huawei_cloud_output / "dispatcher.py", "w", encoding="utf-8") as f:
                            f.write(pruned)
                        print(f"  Pruned dispatcher.py")
                    else:
                        shutil.copy2(src_file, huawei_cloud_output / module_file)
                        print(f"  Copied {module_file}")
            
            continue
        
        if item_name == "references":
            shutil.copytree(item, output_dir / "references")
            print(f"  Copied references")
            continue
        
        if item_name.startswith("."):
            shutil.copy2(item, output_dir / item_name)
            continue
    
    print(f"  Transformation complete!")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Transform skill for release")
    parser.add_argument("--skill", required=True, help="Skill name")
    parser.add_argument("--target", required=True, help="Target directory")
    
    args = parser.parse_args()
    target_dir = Path(args.target)
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        output_dir = transform_skill(args.skill, target_dir)
        print(f"\nSuccess! Skill transformed to: {output_dir}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()