import os
from unittest import mock

import huawei_cloud.hcloud_runner as hr
from huawei_cloud.hcloud_runner import (
    CredentialCtx, resolve_credentials, set_injected_credentials, kubectl_cce,
)

_ENV_CREDS = ("HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_SECURITY_TOKEN", "HW_PROJECT_ID")


def setup_function():
    set_injected_credentials(None, None, None)
    for k in _ENV_CREDS:
        os.environ.pop(k, None)


def test_injection_resolves_and_marks_injected():
    set_injected_credentials("IAK", "ISK", "ITOK")
    ctx = resolve_credentials(region="cn-north-4", fetch_project_id=False)
    assert ctx.ak == "IAK" and ctx.sk == "ISK" and ctx.security_token == "ITOK"
    assert ctx.injected is True


def test_env_mode_not_injected():
    os.environ["HW_ACCESS_KEY"], os.environ["HW_SECRET_KEY"] = "EAK", "ESK"
    ctx = resolve_credentials(region="cn-north-4", fetch_project_id=False)
    assert ctx.ak == "EAK" and ctx.injected is False


def test_explicit_param_overrides_injection():
    set_injected_credentials("IAK", "ISK", None)
    ctx = resolve_credentials(ak="Pak", sk="Psk", region="cn-north-4", fetch_project_id=False)
    assert ctx.ak == "Pak" and ctx.injected is False


def test_kubectl_cce_forwards_flags_when_injected():
    ctx = CredentialCtx("IAK", "ISK", "ITOK", "PID", injected=True)
    with mock.patch.object(hr.subprocess, "run") as m:
        m.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        kubectl_cce(ctx, "cn-north-4", "c1", ["get", "nodes"])
    cmd = m.call_args.args[0]
    assert "--cli-access-key=IAK" in cmd
    assert "--cli-secret-key=ISK" in cmd
    assert "--cli-security-token=ITOK" in cmd
    assert "HW_ACCESS_KEY" not in m.call_args.kwargs["env"]


def test_kubectl_cce_env_mode_no_flags():
    os.environ["HW_ACCESS_KEY"], os.environ["HW_SECRET_KEY"] = "EAK", "ESK"
    ctx = resolve_credentials(region="cn-north-4", fetch_project_id=False)
    with mock.patch.object(hr.subprocess, "run") as m:
        m.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        kubectl_cce(ctx, "cn-north-4", "c1", ["get", "nodes"])
    cmd = m.call_args.args[0]
    assert not any(c.startswith("--cli-access-key") for c in cmd)
    assert m.call_args.kwargs["env"].get("HW_ACCESS_KEY") == "EAK"


from huawei_cloud.huawei_cloud_entry import parse_args


def test_parse_args_extracts_equals_form():
    params, (ak, sk, tok) = parse_args(
        ["region=cn-north-4", "--cli-access-key=IAK", "--cli-secret-key=ISK"])
    assert params == {"region": "cn-north-4"}
    assert (ak, sk, tok) == ("IAK", "ISK", None)


def test_parse_args_extracts_space_form():
    params, (ak, sk, tok) = parse_args(
        ["--cli-access-key", "IAK", "--cli-secret-key", "ISK", "region=cn-north-4"])
    assert params == {"region": "cn-north-4"}
    assert (ak, sk, tok) == ("IAK", "ISK", None)


def test_parse_args_no_injection():
    params, inj = parse_args(["region=cn-north-4", "cluster_id=c1"])
    assert params == {"region": "cn-north-4", "cluster_id": "c1"}
    assert inj == (None, None, None)
