import {test, after} from 'node:test';
import assert from 'node:assert/strict';
import {makeApi} from '../server.mjs';
const server = makeApi();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
after(() => server.close());
const base = 'http://127.0.0.1:' + server.address().port;
test('health endpoint is online', async () => {
  const response = await fetch(base + '/api/health');
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, 'ok');
  assert.equal(body.database, 'none');
});
test('API message available', async () => {
  const response = await fetch(base + '/api/message');
  assert.equal((await response.json()).message, 'Angular and Node.js are connected.');
});
test('unknown route is 404', async () => {
  const response = await fetch(base + '/api/missing');
  assert.equal(response.status, 404);
});
