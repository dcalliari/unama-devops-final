#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common.sh"
TAG=${TAG:-$(git -C "$ROOT" rev-parse --short=12 HEAD)}
[[ "$TAG" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$ ]] || { echo 'Tag invalida' >&2; exit 1; }
IMAGE=localhost:15000/pipeline-final:$TAG
case "${1:-all}" in
  test)
    node --test "$ROOT/app/server.test.js"
    helm lint "$ROOT/helm/pipeline-final"
    helm template unama-final "$ROOT/helm/pipeline-final" > "$LAB_DIR/evidencias/helm-rendered.yaml"
    kubectl --context "$CONTEXT" --namespace "$NAMESPACE" apply --dry-run=server -f "$LAB_DIR/evidencias/helm-rendered.yaml"
    ;;
  build)
    docker build --pull -t "$IMAGE" "$ROOT/app"
    ;;
  push)
    docker push "$IMAGE"
    curl -fsS http://127.0.0.1:15000/v2/pipeline-final/tags/list
    ;;
  deploy)
    helm upgrade --install unama-final "$ROOT/helm/pipeline-final" --kube-context "$CONTEXT" --namespace "$NAMESPACE" \
      --set image.repository=localhost:15000/pipeline-final --set-string image.tag="$TAG" --wait --timeout 180s
    kube rollout status deployment/unama-final --timeout=180s
    kube get pods,svc -o wide
    ;;
  verify)
    TAG="$TAG" python3 "$ROOT/scripts/verify.py"
    ;;
  all)
    for stage in test build push deploy verify; do
      printf '\n===== %s %s =====\n' "$(date -u +%FT%TZ)" "$stage"
      TAG="$TAG" bash "$0" "$stage"
    done
    echo 'PIPELINE LOCAL: SUCCESS'
    ;;
  *) echo 'Use: pipeline.sh [test|build|push|deploy|verify|all]' >&2; exit 2 ;;
esac
