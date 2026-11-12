const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createApp } = require('./server');

let server, base, dir;
before(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pipeline-final-test-'));
  server = createApp({ logDir: dir, version: 'test', demo: true });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(async () => {
  await new Promise(resolve => server.close(resolve));
  fs.rmSync(dir, { recursive: true });
});
test('saude informa status e versao', async () => {
  const res = await fetch(base + '/saude');
  assert.equal(res.status, 200);
  assert.equal((await res.json()).versao, 'test');
});
test('soma dois numeros', async () => {
  const res = await fetch(base + '/api/soma?a=2&b=3');
  assert.equal(res.status, 200);
  assert.equal((await res.json()).resultado, 5);
});
test('rejeita parametros ausentes, vazios, invalidos e overflow', async () => {
  for (const query of ['a=2', 'a=&b=3', 'a=abc&b=3', 'a=Infinity&b=2', 'a=1e308&b=1e308']) {
    assert.equal((await fetch(base + '/api/soma?' + query)).status, 400);
  }
});
test('rota desconhecida retorna 404', async () => {
  assert.equal((await fetch(base + '/nao-existe')).status, 404);
});
test('metodo invalido retorna 405', async () => {
  assert.equal((await fetch(base + '/', { method: 'POST' })).status, 405);
});
test('falha controlada retorna 500', async () => {
  assert.equal((await fetch(base + '/erro')).status, 500);
});
test('latencia controlada aguarda pelo menos 100 ms', async () => {
  const start = performance.now();
  assert.equal((await fetch(base + '/lento')).status, 200);
  assert.ok(performance.now() - start >= 100);
});
test('log estruturado contem status, tempo e nao grava query', async () => {
  await fetch(base + '/saude?segredo=nao-gravar');
  const text = fs.readFileSync(path.join(dir, `${os.hostname()}.ndjson`), 'utf8');
  assert.ok(!text.includes('nao-gravar'));
  const event = JSON.parse(text.trim().split('\n').at(-1));
  assert.equal(event.http.response.status_code, 200);
  assert.ok(event.response_time_ms >= 0);
  assert.equal(event.url.path, '/saude');
  assert.ok(Date.parse(event['@timestamp']));
});
test('rotas de demonstracao desabilitadas por padrao', async () => {
  const app = createApp();
  await new Promise(resolve => app.listen(0, '127.0.0.1', resolve));
  try {
    assert.equal((await fetch(`http://127.0.0.1:${app.address().port}/erro`)).status, 404);
  } finally { await new Promise(resolve => app.close(resolve)); }
});
