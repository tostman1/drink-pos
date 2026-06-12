export function openDialog(dialog, person) {
  if (!dialog) return;
  dialog.dataset.personId = person?.id || '';
  if (typeof dialog.showModal === 'function') dialog.showModal();
}

export function closeDialog(dialog) {
  if (dialog?.open) dialog.close();
}
