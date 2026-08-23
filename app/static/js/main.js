import { api } from './api.js';
import { initSync } from './sync.js';
import { state } from './state.js';
import { renderPeople } from './ui/overview.js';

async function boot() {
  const config = await api.getConfig();
  state.config = config;
  await initSync();
  renderPeople(document.getElementById('leftColumn'), state.people);
  state.subscribe('people', people => renderPeople(document.getElementById('leftColumn'), people));
}

document.addEventListener('DOMContentLoaded', () => {
  boot().catch(error => console.error('Drink POS boot failed', error));
});
