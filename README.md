# Pipeline final: DevOps na prática

Laboratório acadêmico local que integra testes, Docker, registry, Jenkins,
Kubernetes/Helm e Filebeat/Elasticsearch/Kibana. Não usa serviços pagos.
O `Jenkinsfile` implementa CI e CD no laboratório. O workflow
`.github/workflows/main.yml` executa testes, build, publicação no
GHCR e deploy Helm num Kind efêmero do próprio runner GitHub. O runner
hospedado não recebe acesso à máquina local.

## Escopo e rastreabilidade

Os requisitos foram conferidos nas páginas 5 a 9 de **Atividade Final.pdf** e
na atividade final de **Aula 5: Logs e Application Performance Monitoring
(APM) com Elastic Stack.pdf**. A aula 5 é a parte de observabilidade do
projeto, não substitui as outras etapas.

A estrutura do chart, as rotas `/` e `/saude` e as decisões de duas réplicas,
sondas e limites reaproveitam o padrão da atividade Kubernetes anterior.
O código anterior foi somente consultado e permanece intacto. A aplicação
foi adaptada para Node.js padrão, sem dependências externas, e recebe testes,
logs NDJSON e cenários controlados de erro e latência.

O repositório é público: <https://github.com/dcalliari/unama-devops-final>.
O GitHub Actions é acionado por push na branch main ou por workflow_dispatch.
O workflow publica no GHCR sem impor uma visibilidade ao pacote. A imagem usa a tag de
commit completo. O cluster efêmero recebe a imagem recém-construída por
`kind load docker-image`, sem guardar credenciais de registry no Kubernetes.
O push no GHCR é uma etapa anterior e obrigatória, não uma publicação simulada.

O Jenkins complementa a execução remota com o ambiente observável local:
executa a pipeline a partir de um snapshot de commit Git local, publica num
registry HTTP exclusivo e implanta no Kind persistente do laboratório, que
faz pull pelo registry. O acionamento do job local é manual; depois dele
testes, build, push, deploy, verificação e dashboard são automáticos, sem
aprovação intermediária. Resultados só devem ser considerados comprovados
quando acompanhados dos logs e evidências da execução correspondente.

## Arquitetura

```text
commit Git local -> Jenkins -> testes + Helm lint + validação no API Server
                         -> Docker build -> registry localhost:15000
                         -> Helm upgrade --wait -> Kind / namespace pipeline-final
HTTP 127.0.0.1:18080 -> NodePort 30080 -> 2 Pods Node.js
                         -> NDJSON em volume exclusivo (um arquivo por Pod)
                         -> Filebeat filestream -> Elasticsearch -> Kibana
```

O contexto Kubernetes é sempre explícito e o kubeconfig fica fora de
`~/.kube/config`. Todos os ports publicados no host usam `127.0.0.1`.
O processo Node usa `0.0.0.0` **dentro** do container para receber o tráfego
do Service; isso não publica uma porta do host na rede.

## Pré-requisitos

* Linux x86_64, Docker Engine e Compose v2, Git, Bash, curl e Python 3.
* Node.js 22 ou superior, Helm 3 e kubectl compatível com Kubernetes 1.34.
* Kind 0.31.0 e imagem `kindest/node:v1.34.0`.
* Java 21 para o Jenkins 2.528.3, plugins fixados em `jenkins-plugins.txt`.
* Internet para baixar ferramentas e imagens, aproximadamente 5 GB de
  espaço e 6 GB de memória disponível para o laboratório.
* Portas livres: 15000, 15601, 18080, 18081 e 19200. Kind também escolhe
  uma porta livre de API Kubernetes, somente no loopback.

Não execute sobre um diretório de logs de outro projeto. Não há mudança de
sysctl, serviço compartilhado, credencial ou autenticação de registry remoto.

## Reprodução

A partir da raiz do clone, com um `HEAD` commitado:

```bash
export LAB_DIR=/tmp/unama-pipeline-final
mkdir -p "$LAB_DIR/bin"
curl -fL https://kind.sigs.k8s.io/dl/v0.31.0/kind-linux-amd64 -o "$LAB_DIR/bin/kind"
chmod +x "$LAB_DIR/bin/kind"
export PATH="$LAB_DIR/bin:$PATH"
export KUBECONFIG="$LAB_DIR/kubeconfig"
bash scripts/setup.sh

# Sem Jenkins: os mesmos estágios, em sequência, interrompendo em qualquer falha.
TAG=ensaio-1 bash scripts/pipeline.sh all
python3 scripts/dashboard.py

# Com Jenkins: este processo fica em primeiro plano e escuta só loopback.
export JAVA_HOME=/caminho/para/jdk-21
bash scripts/jenkins.sh
```

Em outro terminal, abra <http://127.0.0.1:18081/job/pipeline-final/> e use
**Build Now**. O job arquiva o `HEAD` local, sem copiar modificações não
commitadas. A tag associa hash de commit e número da execução. Veja o console
para identificar a versão efetivamente implantada. Para acionar por API,
use o crumb CSRF e preserve o cookie da mesma sessão.

* API: <http://127.0.0.1:18080/saude>
* Soma: <http://127.0.0.1:18080/api/soma?a=2&b=3>
* Dashboard: <http://127.0.0.1:15601/app/dashboards#/view/pipeline-final>
* Registry: <http://127.0.0.1:15000/v2/pipeline-final/tags/list>

`verify.py` gera 30 requisições: 20 somas, 5 respostas lentas, 3 erros 500
controlados e 2 rotas inexistentes. Confere os códigos HTTP, o resultado da
soma, a versão e o lote inteiro no Elasticsearch após a passagem pelo
Filebeat. A consulta filtra versão e instante de início. Não misture dois
lotes com a mesma tag no mesmo segundo. Use uma tag nova por ensaio.

```bash
kubectl --context kind-unama-pipeline-final -n pipeline-final get pods,svc -o wide
helm --kube-context kind-unama-pipeline-final -n pipeline-final history unama-final
curl -fsS http://127.0.0.1:19200/pipeline-final-*/_count
```

## Observabilidade e testes

`app/server.test.js` contém nove testes automatizados de HTTP real em
loopback. Os testes exercitam saúde, soma, parâmetros inválidos/overflow,
404, 405, erro controlado, latência, estrutura/privacidade dos logs e
rotas de demonstração desabilitadas por padrão.

O Filebeat lê somente `LAB_DIR/logs/*.ndjson`, decodifica JSON, mantém o
estado de leitura em volume próprio e envia diretamente ao Elasticsearch.
Não usa o socket Docker nem varre logs de aplicações alheias. A data view
`pipeline-final-*` usa `@timestamp`. O dashboard mostra total, tempo médio,
códigos HTTP, média por rota e logs recentes, com atualização a cada 5s.
Sondas também geram requisições `/saude`, portanto o total do dashboard é
maior que o lote E2E. Isso é esperado, não equivale a tráfego de usuários.

O tempo de resposta é medido no servidor com relógio monotônico em
milissegundos. Não é latência ponta a ponta do cliente, nem tracing
APM distribuído. O agente Elastic APM da aula é opcional e não foi adicionado.

## Segurança e limites do laboratório

O Jenkins sem login e a segurança Elastic desativada são escolhas apenas de
laboratório, restritas a loopback. Não use esta configuração em produção nem
em host multiusuário não confiável. Código executado pelo Jenkins tem os
mesmos privilégios do usuário local, inclusive acesso ao Docker.

O registry local usa HTTP. O Kind contém a configuração de confiança apenas
para `localhost:15000`; o Docker do host não é reconfigurado. `hostPath` e
permissão de escrita no diretório temporário simplificam a coleta num único
nó. Em produção, usar TLS, autenticação, RBAC, secrets, armazenamento
persistente gerenciado e coleta por agente no nó. Os Pods da API são
não-root, com filesystem raiz somente leitura e sem capabilities.

## Artefatos e preservação

Resultados, logs e kubeconfig ficam em `$LAB_DIR`, fora do Git. O relatório
PDF e capturas são artefatos de entrega, não fonte. Nenhum identificador de
aluno ou segredo precisa estar no repositório. Não usar `docker system prune`.
Para encerrar **apenas este laboratório**, depois de preservar as evidências:

```bash
# Encerrar o processo Jenkins com Ctrl+C no terminal em que foi iniciado.
kind delete cluster --name unama-pipeline-final
docker compose -f observability/compose.yaml down
# Os volumes são preservados; não usar -v se quiser manter logs indexados.
```

## Roteiro de apresentação (até 10 minutos)

1. 0:00 a 1:30: problema, DevOps e diferença entre CI/Delivery/Deployment.
2. 1:30 a 3:00: código, testes e falha controlada da aplicação.
3. 3:00 a 5:00: Jenkins, build, push no registry e tag rastreável.
4. 5:00 a 6:30: Helm, duas réplicas, sondas e acesso via NodePort.
5. 6:30 a 8:30: requisições, Filebeat e dashboard com status e latência.
6. 8:30 a 10:00: evidência E2E, limites locais, rastreabilidade da publicação e
   melhorias necessárias para produção.
