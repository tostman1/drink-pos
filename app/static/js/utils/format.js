export function numberComma(value, minimumFractionDigits = 2, maximumFractionDigits = minimumFractionDigits) {
  const number = Number(value || 0);
  return number.toLocaleString('de-AT', { minimumFractionDigits, maximumFractionDigits });
}

export function money(value) {
  return `EUR ${numberComma(value, 2, 2)}`;
}

export function decimalText(value, digits = 2) {
  return numberComma(value, digits, digits);
}

export function centsFromEur(value) {
  return Math.max(0, Math.round(Number(value || 0) * 100));
}

export function eurFromCents(cents) {
  return Number(cents || 0) / 100;
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
