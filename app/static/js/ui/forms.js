export function renderDrinkButtons(container, items, onAdd = () => {}) {
  if (!container) return;
  container.innerHTML = '';
  for (const item of items || []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = item.short_label || item.name;
    button.addEventListener('click', () => onAdd(item));
    container.appendChild(button);
  }
}
