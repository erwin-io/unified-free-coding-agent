import { createServer as createHttpServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';

const root = dirname(fileURLToPath(import.meta.url));
const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']]
]);
const json = (res, status, data) => {
  const body = JSON.stringify(data);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  res.end(body);
};
async function readJson(req) {
  let text = '';
  for await (const chunk of req) {
    text += chunk;
    if (text.length > 16384) throw Object.assign(new Error('Request too large'), { status: 413 });
  }
  try { return JSON.parse(text || '{}'); }
  catch { throw Object.assign(new Error('Invalid JSON'), { status: 400 }); }
}
export function createApp() {
  const tasks = new Map();
  const startedAt = Date.now();
  return createHttpServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const pathname = url.pathname;
    try {
      if (req.method === 'GET' && pathname === '/api/health') {
        return json(res, 200, { status: 'ok', application: 'test-nodejs-web-app', uptimeSeconds: Math.floor((Date.now() - startedAt) / 1000), database: 'none' });
      }
      if (req.method === 'GET' && pathname === '/api/tasks') {
        return json(res, 200, { items: [...tasks.values()] });
      }
      if (req.method === 'POST' && pathname === '/api/tasks') {
        const body = await readJson(req);
        if (typeof body.title !== 'string' || !body.title.trim() || body.title.trim().length > 120) {
          return json(res, 400, { error: 'Title is required (maximum 120 characters)' });
        }
        const item = { id: randomUUID(), title: body.title.trim(), done: false, createdAt: new Date().toISOString() };
        tasks.set(item.id, item);
        return json(res, 201, { item });
      }
      const match = /^\/api\/tasks\/([a-z0-9-]+)$/.exec(pathname);
      if (match && req.method === 'PATCH') {
        const item = tasks.get(match[1]);
        if (!item) return json(res, 404, { error: 'Task not found' });
        const body = await readJson(req);
        if (typeof body.done !== 'boolean') return json(res, 400, { error: 'done must be boolean' });
        item.done = body.done;
        return json(res, 200, { item });
      }
      if (match && req.method === 'DELETE') {
        return tasks.delete(match[1]) ? json(res, 200, { removed: true }) : json(res, 404, { error: 'Task not found' });
      }
      if (req.method === 'GET' && assets.has(pathname)) {
        const [file, contentType] = assets.get(pathname);
        const bytes = await readFile(join(root, 'public', file));
        res.writeHead(200, { 'Content-Type': contentType, 'X-Content-Type-Options': 'nosniff' });
        return res.end(bytes);
      }
      return json(res, 404, { error: 'Not found' });
    } catch (error) {
      return json(res, error.status || 500, { error: error.status ? error.message : 'Internal server error' });
    }
  });
}
if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const port = Number(process.env.PORT || 3000);
  createApp().listen(port, '127.0.0.1', () => console.log('Demo running: http://127.0.0.1:' + port));
}
