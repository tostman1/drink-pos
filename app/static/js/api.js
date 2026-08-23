async function request(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 8000);
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload.detail;
      throw new Error(typeof detail === 'string' ? detail : payload.message || 'Server error');
    }
    return payload;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  getConfig() {
    return request('/api/config', { method: 'GET' });
  },
  getPeople() {
    return request('/api/people', { method: 'GET' });
  },
  addDrink(personId, itemId, extra = {}) {
    return request('/api/add-drink', {
      method: 'POST',
      body: JSON.stringify({ person_id: personId, item_id: itemId, ...extra }),
    });
  },
  payPerson(personId, pin, extra = {}) {
    return request('/api/pay', {
      method: 'POST',
      body: JSON.stringify({ person_id: personId, pin, ...extra }),
    });
  },
  getSyncStatus() {
    return request('/api/sync-status', { method: 'GET', timeoutMs: 4500 });
  },
};
