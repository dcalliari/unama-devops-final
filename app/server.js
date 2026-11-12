const http = require('node:http');
const os = require('node:os');
const fs = require('node:fs');
const path = require('node:path');

function createApp({ logDir, version = 'dev', demo = false } = {}) {
  if (logDir) fs.mkdirSync(logDir, { recursive: true });
  return http.createServer(async (req, res) => {
    const start = process.hrtime.bigint();
    const url = new URL(req.url, 'http://localhost');
    const route = url.pathname;
    let status = 200;
    let body;
    if (req.method !== 'GET') {
      status = 405;
      body = { erro: 'Metodo nao permitido' };
    } else if (route === '/saude' || route === '/') {
      body = { status: 'ok', servico: 'pipeline-final', versao: version, pod: os.hostname() };
    } else if (route === '/api/soma') {
      const a = url.searchParams.get('a');
      const b = url.searchParams.get('b');
      if (a === null || b === null || a.trim() === '' || b.trim() === '' ||
          !Number.isFinite(Number(a)) || !Number.isFinite(Number(b)) ||
          !Number.isFinite(Number(a) + Number(b))) {
        status = 400;
        body = { erro: 'Informe dois numeros finitos: a e b' };
      } else body = { resultado: Number(a) + Number(b), versao: version };
    } else if (demo && route === '/lento') {
      await new Promise(resolve => setTimeout(resolve, 120));
      body = { status: 'ok', cenario: 'latencia controlada' };
    } else if (demo && route === '/erro') {
      status = 500;
      body = { erro: 'Falha controlada para demonstracao' };
    } else {
      status = 404;
      body = { erro: 'Rota nao encontrada' };
    }
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(body));
    const event = {
      '@timestamp': new Date().toISOString(),
      service: { name: 'pipeline-final', version },
      host: { name: os.hostname() },
      http: { request: { method: req.method }, response: { status_code: status } },
      url: { path: route },
      response_time_ms: Number(process.hrtime.bigint() - start) / 1e6,
      message: `${req.method} ${route} ${status}`,
    };
    const line = JSON.stringify(event) + '\n';
    process.stdout.write(line);
    if (logDir) fs.appendFileSync(path.join(logDir, `${os.hostname()}.ndjson`), line);
  });
}

if (require.main === module) {
  const server = createApp({
    logDir: process.env.LOG_DIR,
    version: process.env.APP_VERSION || 'dev',
    demo: process.env.DEMO_MODE === 'true',
  });
  server.listen(Number(process.env.PORT || 3000), process.env.BIND_HOST || '127.0.0.1');
  process.on('SIGTERM', () => server.close(() => process.exit(0)));
}
module.exports = { createApp };
