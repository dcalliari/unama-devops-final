#!/usr/bin/env bash
set -euo pipefail
ROOT=$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")
export LAB_DIR=${LAB_DIR:-/tmp/unama-pipeline-final}
export KUBECONFIG="$LAB_DIR/kubeconfig"
export PATH="$LAB_DIR/bin:$PATH"
CLUSTER=unama-pipeline-final
CONTEXT=kind-unama-pipeline-final
NAMESPACE=pipeline-final
mkdir -p "$LAB_DIR/evidencias" "$LAB_DIR/logs"
compose() { docker compose -f "$ROOT/observability/compose.yaml" "$@"; }
kube() { kubectl --context "$CONTEXT" --namespace "$NAMESPACE" "$@"; }
