import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../server.js';

const server = createApp();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
after(() => server.close());
const base = 'http://127.0.0.1:' + server.address().port;

test('GET / serves frontend HTML', async () => {
  const response = await fetch(base);
  assert.equal(response.status, 200);
  assert.match(await response.text(), /Full-stack test dashboard/);
});
test('GET /app.js serves frontend script', async () => {
  const response = await fetch(base + '/app.js');
  assert.equal(response.status, 200);
  assert.match(await response.text(), /renderTasks/);
});
test('GET /api/health returns ready backend', async () => {
  const response = await fetch(base + '/api/health');
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.application, 'test-nodejs-web-app');
  assert.equal(body.database, 'none');
});
test('Task API CRUD works without a database', async () => {
  const invalid = await fetch(base + '/api/tasks', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '' })
  });
  assert.equal(invalid.status, 400);
  const created = await fetch(base + '/api/tasks', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'Verify UI' })
  });
  assert.equal(created.status, 201);
  const { item } = await created.json();
  assert.equal(item.done, false);
  const items = await (await fetch(base + '/api/tasks')).json();
  assert.equal(items.items.length, 1);
  const updated = await fetch(base + '/api/tasks/' + item.id, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ done: true })
  });
  assert.equal(updated.status, 200);
  assert.equal((await updated.json()).item.done, true);
  const removed = await fetch(base + '/api/tasks/' + item.id, { method: 'DELETE' });
  assert.equal(removed.status, 200);
  assert.equal((await (await fetch(base + '/api/tasks')).json()).items.length, 0);
});
