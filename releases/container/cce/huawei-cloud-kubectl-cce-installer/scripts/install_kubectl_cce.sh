#!/usr/bin/env bash
set -euo pipefail

PLUGIN_VERSION="0.1.0"
PLUGIN_REPOSITORY="pancake0001/kubectl-cce-plugin"
KUBERNETES_REPOSITORY="https://github.com/kubernetes/kubernetes.git"
PLUGIN_SOURCE_REPOSITORY="https://github.com/${PLUGIN_REPOSITORY}.git"
BIN_DIR="/usr/local/bin"
MODE="plan"

usage() {
  cat <<'EOF'
Usage: install_kubectl_cce.sh [--check] [--execute] [--bin-dir <directory>]

Without --execute, print the installation plan only. --execute installs missing
executables and must be used only after user confirmation.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --execute) MODE="execute" ;;
    --bin-dir)
      BIN_DIR="${2:?--bin-dir requires a directory}"
      shift
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "amd64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) echo "unsupported" ;;
  esac
}

install_file() {
  local source="$1"
  local destination="$2"
  install -m 0755 "$source" "$destination"
}

build_kubectl_from_source() {
  local version="$1"
  local source_dir="$WORK_DIR/kubernetes"
  require_command git
  require_command go
  echo "Official kubectl download failed; building kubectl ${version} from the Kubernetes source tag."
  git clone --depth 1 --branch "$version" "$KUBERNETES_REPOSITORY" "$source_dir"
  (
    cd "$source_dir"
    go build -o "$WORK_DIR/kubectl" ./cmd/kubectl
  )
  install_file "$WORK_DIR/kubectl" "$BIN_DIR/kubectl"
}

build_plugin_from_source() {
  local source_dir="$WORK_DIR/kubectl-cce-plugin"
  require_command git
  require_command go
  echo "kubectl-cce Release asset is unavailable; building plugin v${PLUGIN_VERSION} from source."
  git clone --depth 1 --branch "v${PLUGIN_VERSION}" "$PLUGIN_SOURCE_REPOSITORY" "$source_dir"
  (
    cd "$source_dir"
    go build -o "$WORK_DIR/kubectl-cce" ./cmd/kubectl-cce
  )
  install_file "$WORK_DIR/kubectl-cce" "$BIN_DIR/kubectl-cce"
}

OS="$(uname -s)"
ARCH="$(detect_arch)"
KUBECTL_PRESENT=false
PLUGIN_PRESENT=false
command -v kubectl >/dev/null 2>&1 && KUBECTL_PRESENT=true
command -v kubectl-cce >/dev/null 2>&1 && PLUGIN_PRESENT=true

echo "platform=${OS} arch=${ARCH}"
echo "kubectl_present=${KUBECTL_PRESENT}"
echo "kubectl_cce_present=${PLUGIN_PRESENT}"
echo "bin_dir=${BIN_DIR}"

if [[ "$MODE" == "check" ]]; then
  if "$KUBECTL_PRESENT"; then kubectl version --client 2>/dev/null || true; fi
  if "$KUBECTL_PRESENT"; then kubectl plugin list 2>/dev/null || true; fi
  exit 0
fi

if [[ "$ARCH" == "unsupported" ]]; then
  echo "Unsupported CPU architecture: $(uname -m)" >&2
  exit 1
fi

if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
  echo "This installer supports Linux and macOS only. See references/plugin-usage.md for Windows." >&2
  exit 1
fi

if [[ "$KUBECTL_PRESENT" == false ]]; then
  echo "PLAN: install kubectl into ${BIN_DIR} from the official stable ${OS} ${ARCH} binary; build the same stable tag from source if the download fails."
fi
if [[ "$PLUGIN_PRESENT" == false ]]; then
  echo "PLAN: download kubectl-cce v${PLUGIN_VERSION} for ${OS} ${ARCH} from GitHub Release when available; otherwise build tag v${PLUGIN_VERSION} from source."
fi
if [[ "$KUBECTL_PRESENT" == true && "$PLUGIN_PRESENT" == true ]]; then
  echo "Nothing to install. Run with --check to verify versions and plugin discovery."
  exit 0
fi
if [[ "$MODE" != "execute" ]]; then
  echo "No changes made. Re-run with --execute after user confirmation."
  exit 0
fi

require_command curl
require_command install
require_command tar
mkdir -p "$BIN_DIR"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

if [[ "$KUBECTL_PRESENT" == false ]]; then
  KUBECTL_VERSION="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
  KUBECTL_OS="$(tr '[:upper:]' '[:lower:]' <<< "$OS")"
  if curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${KUBECTL_OS}/${ARCH}/kubectl" -o "$WORK_DIR/kubectl"; then
    install_file "$WORK_DIR/kubectl" "$BIN_DIR/kubectl"
  else
    build_kubectl_from_source "$KUBECTL_VERSION"
  fi
fi

if [[ "$PLUGIN_PRESENT" == false ]]; then
  if [[ "$OS" == "Linux" ]]; then
    ASSET_NAME="kubectl-cce_${PLUGIN_VERSION}_linux_${ARCH}.tar.gz"
    ASSET_URL="https://github.com/${PLUGIN_REPOSITORY}/releases/download/v${PLUGIN_VERSION}/${ASSET_NAME}"
    if curl -fsSL "$ASSET_URL" -o "$WORK_DIR/$ASSET_NAME" && tar -xzf "$WORK_DIR/$ASSET_NAME" -C "$WORK_DIR" && [[ -f "$WORK_DIR/kubectl-cce" ]]; then
      install_file "$WORK_DIR/kubectl-cce" "$BIN_DIR/kubectl-cce"
    else
      build_plugin_from_source
    fi
  else
    build_plugin_from_source
  fi
fi

echo "Installation complete."
kubectl version --client
kubectl plugin list
kubectl plugin list | grep -q 'kubectl-cce' || {
  echo "kubectl-cce was installed but is not discoverable by kubectl. Verify that ${BIN_DIR} is in PATH." >&2
  exit 1
}
