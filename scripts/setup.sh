#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common.sh"
for tool in docker node kind kubectl helm python3; do command -v "$tool" >/dev/null; done
# O hostPath pertence somente a este laboratorio; nunca e um diretorio de sistema.
chmod 0777 "$LAB_DIR/logs"
compose up -d
cat > "$LAB_DIR/kind.yaml" <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  apiServerAddress: 127.0.0.1
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 18080
        listenAddress: 127.0.0.1
    extraMounts:
      - hostPath: $LAB_DIR/logs
        containerPath: /var/log/pipeline-final
EOF
if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --image kindest/node:v1.34.0 --config "$LAB_DIR/kind.yaml" --kubeconfig "$KUBECONFIG" --wait 180s
fi
kind export kubeconfig --name "$CLUSTER" --kubeconfig "$KUBECONFIG"
if ! docker inspect -f '{{json .NetworkSettings.Networks}}' unama-pipeline-final-registry | grep -q '"kind"'; then
  docker network connect kind unama-pipeline-final-registry
fi
for node in $(kind get nodes --name "$CLUSTER"); do
  docker exec "$node" mkdir -p /etc/containerd/certs.d/localhost:15000
  printf '[host."http://unama-pipeline-final-registry:5000"]\n  capabilities = ["pull", "resolve"]\n' |
    docker exec -i "$node" sh -c 'cat > /etc/containerd/certs.d/localhost:15000/hosts.toml'
done
kubectl --context "$CONTEXT" create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f -
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:15601/api/status >/dev/null; then
    echo 'Laboratorio pronto: API NodePort 127.0.0.1:18080; Kibana 127.0.0.1:15601'
    exit 0
  fi
  sleep 3
done
echo 'Kibana nao ficou pronto dentro do limite' >&2
exit 1
