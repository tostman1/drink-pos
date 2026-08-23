import { api } from './api.js';
import { state, notifySubscribers } from './state.js';

let timer = null;

export async function checkSyncStatus() {
  try {
    const payload = await api.getSyncStatus();
    state.sync.state = 'online';
    state.sync.failureCount = 0;
    state.sync.lastSyncAt = new Date().toISOString();
    notifySubscribers('sync', { ...state.sync, payload });
    return payload;
  } catch (error) {
    state.sync.state = 'offline';
    state.sync.failureCount += 1;
    notifySubscribers('sync', { ...state.sync, error });
    throw error;
  }
}

export async function resyncNow() {
  const [config, people] = await Promise.all([api.getConfig(), api.getPeople()]);
  state.config = config;
  state.setPeople(people);
  await checkSyncStatus().catch(() => null);
  return { config, people };
}

export function initSync(intervalMs = 5000) {
  clearInterval(timer);
  timer = setInterval(() => checkSyncStatus().catch(() => null), intervalMs);
  return resyncNow();
}

export function stopSync() {
  clearInterval(timer);
  timer = null;
}
