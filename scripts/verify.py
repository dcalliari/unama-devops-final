"""Verificacao HTTP e ingestao real de um lote identificavel no Elasticsearch."""
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


tag = os.environ['TAG']
start = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
base = 'http://127.0.0.1:18080'
status, health = get(base + '/saude')
assert status == 200 and health['versao'] == tag, health
routes = [('/api/soma?a=2&b=3', 200)] * 20 + [('/lento', 200)] * 5 + [('/erro', 500)] * 3 + [('/nao-existe', 404)] * 2
counts = Counter()
for route, expected in routes:
    status, body = get(base + route)
    assert status == expected, (route, status, body)
    if '/api/soma' in route:
        assert body['resultado'] == 5
    counts[status] += 1
query = {
    'size': 0,
    'query': {'bool': {'filter': [
        {'term': {'service.version': tag}},
        {'range': {'@timestamp': {'gte': start}}},
        {'terms': {'url.path': ['/api/soma', '/lento', '/erro', '/nao-existe']}},
    ]}},
    'aggs': {
        'status': {'terms': {'field': 'http.response.status_code'}},
        'latencia_media_ms': {'avg': {'field': 'response_time_ms'}},
        'latencia_p95_ms': {'percentiles': {'field': 'response_time_ms', 'percents': [95]}},
        'rotas': {'terms': {'field': 'url.path'}, 'aggs': {'media_ms': {'avg': {'field': 'response_time_ms'}}}},
    },
}
request = urllib.request.Request(
    'http://127.0.0.1:19200/pipeline-final-*/_search', data=json.dumps(query).encode(),
    headers={'Content-Type': 'application/json'},
)
for attempt in range(60):
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
        if result['hits']['total']['value'] >= 30:
            break
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    time.sleep(2)
else:
    raise SystemExit('Falha: Filebeat nao entregou as 30 requisicoes ao Elasticsearch')
buckets = {str(b['key']): b['doc_count'] for b in result['aggregations']['status']['buckets']}
assert buckets == {str(k): v for k, v in counts.items()}, buckets
assert result['hits']['total']['value'] == 30, result
slow = next(b for b in result['aggregations']['rotas']['buckets'] if b['key'] == '/lento')
assert slow['media_ms']['value'] >= 100, slow
proof = {'inicio_utc': start, 'tag': tag, 'saude': health, 'http_status': dict(counts), 'elasticsearch': result}
output = Path(os.environ['LAB_DIR']) / 'evidencias' / f'verificacao-{tag}.json'
output.write_text(json.dumps(proof, indent=2, ensure_ascii=False))
print(json.dumps(proof, indent=2, ensure_ascii=False))
print('E2E: 30 requisicoes verificadas via NodePort e confirmadas apos Filebeat no Elasticsearch')
