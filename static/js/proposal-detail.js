document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('days-since-sent');
  if (!el) return;
  const dateStr = el.dataset.sentDate;
  if (!dateStr) return;

  const [y, m, d] = dateStr.split('-').map(Number);

  // Compare calendar dates only — sent_date has no time component, so comparing
  // timestamps from local midnight introduces a spurious time-of-day offset.
  const now = new Date();
  const sentMs  = Date.UTC(y, m - 1, d);
  const todayMs = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.floor((todayMs - sentMs) / (24 * 60 * 60 * 1000));

  if (diffDays < 0) return;

  let text;
  if (diffDays === 0)      text = 'Hoy';
  else if (diffDays === 1) text = '1 día';
  else                     text = diffDays + ' días';

  el.textContent = text;
});
