import { createServer } from 'node:http';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const json = (res, code, payload) => {
  res.writeHead(code, {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'});
  res.end(JSON.stringify(payload));
};
export function makeApi() {
  return createServer(async (req, res) => {
    const route = new URL(req.url, 'http://localhost').pathname;
    if (req.method === 'GET' && route === '/api/health') {
      return json(res, 200, {status: 'ok', service: 'angular-node-api', database: 'none'});
    }
    if (req.method === 'GET' && route === '/api/message') {
      return json(res, 200, {message: 'Angular and Node.js are connected.'});
    }
    return json(res, 404, {error: 'Not found'});
  });
}
if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const port = Number(process.env.API_PORT || 3001);
  makeApi().listen(port, '127.0.0.1', () => {
    console.log('Backend: http://127.0.0.1:' + port + '/api/health');
  });
}
