let statusTimer = null;

export function showStatus(text, { timeoutMs = 2400 } = {}) {
  const element = document.getElementById('status');
  if (!element) return;
  element.textContent = text;
  element.style.display = 'block';
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    element.style.display = 'none';
  }, timeoutMs);
}
