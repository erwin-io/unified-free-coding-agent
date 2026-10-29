const status = document.querySelector('#api-status');
const detail = document.querySelector('#api-detail');
const total = document.querySelector('#total-count');
const done = document.querySelector('#done-count');
const list = document.querySelector('#task-list');
const empty = document.querySelector('#empty');
const feedback = document.querySelector('#feedback');
const form = document.querySelector('#task-form');

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'HTTP ' + response.status);
  return data;
}
function tell(message, isError = false) {
  feedback.textContent = message;
  feedback.className = isError ? 'error' : 'success';
}
async function updateHealth() {
  try {
    const info = await api('/api/health');
    status.textContent = info.status === 'ok' ? '● Online' : 'Unavailable';
    status.className = info.status === 'ok' ? 'online' : 'offline';
    detail.textContent = 'No database · Uptime ' + info.uptimeSeconds + 's';
  } catch (error) {
    status.textContent = '● Offline';
    status.className = 'offline';
    detail.textContent = error.message;
  }
}
async function renderTasks() {
  try {
    const { items } = await api('/api/tasks');
    list.replaceChildren();
    total.textContent = items.length;
    done.textContent = items.filter(item => item.done).length;
    empty.hidden = items.length !== 0;
    for (const item of items) {
      const li = document.createElement('li');
      li.className = item.done ? 'task completed' : 'task';
      const label = document.createElement('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = item.done;
      checkbox.setAttribute('aria-label', 'Complete ' + item.title);
      checkbox.addEventListener('change', async () => {
        try {
          await api('/api/tasks/' + item.id, { method: 'PATCH', body: JSON.stringify({ done: checkbox.checked }) });
          await renderTasks();
        } catch (error) { tell(error.message, true); }
      });
      const text = document.createElement('span');
      text.textContent = item.title;
      label.append(checkbox, text);
      const remove = document.createElement('button');
      remove.className = 'delete';
      remove.textContent = 'Remove';
      remove.setAttribute('aria-label', 'Remove ' + item.title);
      remove.addEventListener('click', async () => {
        try {
          await api('/api/tasks/' + item.id, { method: 'DELETE' });
          await renderTasks();
        } catch (error) { tell(error.message, true); }
      });
      li.append(label, remove);
      list.append(li);
    }
  } catch (error) { tell(error.message, true); }
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const title = form.elements.title.value.trim();
  if (!title) return;
  try {
    await api('/api/tasks', { method: 'POST', body: JSON.stringify({ title }) });
    form.reset();
    tell('Task created through the Node.js API.');
    await renderTasks();
  } catch (error) { tell(error.message, true); }
});
await updateHealth();
await renderTasks();
setInterval(updateHealth, 15000);
