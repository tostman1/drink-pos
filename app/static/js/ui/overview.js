import { escapeHtml, money } from '../utils/format.js';

export function renderPeople(container, people, onSelect = () => {}) {
  if (!container) return;
  container.innerHTML = '';
  for (const person of people || []) {
    const button = document.createElement('button');
    button.className = 'person-card';
    button.type = 'button';
    button.innerHTML = `<span>${escapeHtml(person.name)}</span><strong>${money(person.total || 0)}</strong>`;
    button.addEventListener('click', () => onSelect(person));
    container.appendChild(button);
  }
}
