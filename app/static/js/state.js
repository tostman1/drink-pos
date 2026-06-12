const subscribers = new Map();

export const state = {
  config: {},
  people: [],
  items: [],
  ui: {
    adminMode: false,
    currentPerson: null,
    dialogOpen: false,
  },
  sync: {
    lastSyncAt: '',
    state: 'unknown',
    failureCount: 0,
  },
  getPersonById(id) {
    return this.people.find(person => Number(person.id) === Number(id)) || null;
  },
  getOpenTotal(personId = this.ui.currentPerson?.id) {
    const person = this.getPersonById(personId);
    return Number(person?.total || 0);
  },
  setPeople(newPeople) {
    this.people = Array.isArray(newPeople) ? newPeople : [];
    notifySubscribers('people', this.people);
  },
  updatePerson(id, updates) {
    const person = this.getPersonById(id);
    if (!person) return null;
    Object.assign(person, updates);
    notifySubscribers('people', this.people);
    notifySubscribers('person', person);
    return person;
  },
  subscribe(event, callback) {
    return subscribe(event, callback);
  },
};

export function subscribe(event, callback) {
  const list = subscribers.get(event) || new Set();
  list.add(callback);
  subscribers.set(event, list);
  return () => list.delete(callback);
}

export function notifySubscribers(event, payload) {
  for (const callback of subscribers.get(event) || []) callback(payload);
}
