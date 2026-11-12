"""Provisiona objetos reais do Kibana pela API Saved Objects, sem dados sinteticos."""
import json
import urllib.request

base = 'http://127.0.0.1:15601'
index_id = 'pipeline-final-logs'
ref_name = 'kibanaSavedObjectMeta.searchSourceJSON.index'
refs = [{'name': ref_name, 'type': 'index-pattern', 'id': index_id}]
source = json.dumps({'query': {'language': 'kuery', 'query': 'service.name : "pipeline-final"'}, 'filter': [], 'indexRefName': ref_name})
objects = [{'type': 'index-pattern', 'id': index_id, 'attributes': {'title': 'pipeline-final-*', 'timeFieldName': '@timestamp'}}]


def visualization(id_, title, type_, aggs, params=None):
    objects.append({'type': 'visualization', 'id': id_, 'attributes': {
        'title': title,
        'visState': json.dumps({'title': title, 'type': type_, 'params': params or {}, 'aggs': aggs}),
        'uiStateJSON': '{}', 'description': 'Dados reais coletados pelo Filebeat',
        'kibanaSavedObjectMeta': {'searchSourceJSON': source},
    }, 'references': refs})


visualization('pf-count', 'Total de requisicoes', 'metric', [{'id': '1', 'enabled': True, 'type': 'count', 'schema': 'metric', 'params': {}}], {'fontSize': 42})
visualization('pf-latency', 'Tempo medio de resposta (ms)', 'metric', [{'id': '1', 'enabled': True, 'type': 'avg', 'schema': 'metric', 'params': {'field': 'response_time_ms', 'customLabel': 'Media (ms)'}}], {'fontSize': 42})
visualization('pf-status', 'Requisicoes por status HTTP', 'pie', [
    {'id': '1', 'enabled': True, 'type': 'count', 'schema': 'metric', 'params': {}},
    {'id': '2', 'enabled': True, 'type': 'terms', 'schema': 'segment', 'params': {'field': 'http.response.status_code', 'size': 10, 'order': 'desc', 'orderBy': '1'}},
], {'addLegend': True, 'addTooltip': True, 'isDonut': True, 'legendPosition': 'right'})
visualization('pf-routes', 'Tempo medio por rota (ms)', 'table', [
    {'id': '1', 'enabled': True, 'type': 'avg', 'schema': 'metric', 'params': {'field': 'response_time_ms', 'customLabel': 'Media (ms)'}},
    {'id': '2', 'enabled': True, 'type': 'terms', 'schema': 'bucket', 'params': {'field': 'url.path', 'size': 10, 'order': 'desc', 'orderBy': '1'}},
], {'perPage': 10, 'showTotal': False, 'showMetricsAtAllLevels': False})
objects.append({'type': 'search', 'id': 'pf-live-logs', 'attributes': {
    'title': 'Logs da aplicacao em tempo real', 'description': 'Atualizacao automatica a cada 5 segundos',
    'columns': ['url.path', 'http.response.status_code', 'response_time_ms', 'service.version'],
    'sort': [['@timestamp', 'desc']], 'grid': {}, 'hideChart': True,
    'kibanaSavedObjectMeta': {'searchSourceJSON': source},
}, 'references': refs})
panels = []
placements = [
    ('pf-count', 'visualization', 0, 0, 12, 7),
    ('pf-latency', 'visualization', 12, 0, 12, 7),
    ('pf-status', 'visualization', 24, 0, 24, 14),
    ('pf-routes', 'visualization', 0, 7, 24, 7),
    ('pf-live-logs', 'search', 0, 14, 48, 17),
]
dashboard_refs = []
for i, (id_, type_, x, y, w, h) in enumerate(placements):
    name = f'panel_{i}'
    panels.append({'panelIndex': str(i), 'panelRefName': name, 'type': type_, 'embeddableConfig': {}, 'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': str(i)}, 'version': '8.17.0'})
    dashboard_refs.append({'name': name, 'type': type_, 'id': id_})
objects.append({'type': 'dashboard', 'id': 'pipeline-final', 'attributes': {
    'title': 'Pipeline final | Logs e performance',
    'description': 'NodePort Kubernetes -> NDJSON -> Filebeat -> Elasticsearch -> Kibana',
    'panelsJSON': json.dumps(panels), 'optionsJSON': json.dumps({'useMargins': True, 'hidePanelTitles': False}),
    'version': 1, 'timeRestore': True, 'timeFrom': 'now-24h', 'timeTo': 'now',
    'refreshInterval': {'pause': False, 'value': 5000},
    'kibanaSavedObjectMeta': {'searchSourceJSON': '{"query":{"language":"kuery","query":""},"filter":[]}'},
}, 'references': dashboard_refs})
ndjson = '\n'.join(json.dumps(obj) for obj in objects) + '\n'
boundary = 'pipelinefinalboundary'
body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="dashboard.ndjson"\r\nContent-Type: application/ndjson\r\n\r\n{ndjson}\r\n--{boundary}--\r\n').encode()
request = urllib.request.Request(base + '/api/saved_objects/_import?overwrite=true', data=body, headers={'kbn-xsrf': 'true', 'Content-Type': f'multipart/form-data; boundary={boundary}'})
with urllib.request.urlopen(request, timeout=60) as response:
    result = json.load(response)
assert result.get('success'), result
print(json.dumps(result, indent=2))
print(base + '/app/dashboards#/view/pipeline-final')
