import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly status = signal('Connecting to API...');
  readonly message = signal('Loading...');

  constructor() {
    void fetch('/api/health').then(r => {
      if (!r.ok) throw new Error('API not available');
      return r.json();
    }).then(body => this.status.set(body.status === 'ok' ? 'Online' : 'Unexpected'))
      .catch(() => this.status.set('Offline'));

    void fetch('/api/message').then(r => r.json())
      .then(body => this.message.set(body.message))
      .catch(() => this.message.set('Could not load API message'));
  }
}
