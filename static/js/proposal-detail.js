document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('days-since-sent');
  if (!el) return;
  const dateStr = el.dataset.sentDate;
  if (!dateStr) return;

  const [y, m, d] = dateStr.split('-').map(Number);
  // Construct local midnight so diff reflects user's timezone
  const sent = new Date(y, m - 1, d);
  const now = new Date();
  const diffMs = now - sent;
  if (diffMs < 0) return;

  const MINUTE = 60 * 1000;
  const HOUR   = 60 * MINUTE;
  const DAY    = 24 * HOUR;

  const days    = Math.floor(diffMs / DAY);
  const hours   = Math.floor((diffMs % DAY) / HOUR);
  const minutes = Math.floor((diffMs % HOUR) / MINUTE);

  const parts = [];
  if (days > 0)    parts.push(days    + (days    === 1 ? ' day'    : ' days'));
  if (hours > 0)   parts.push(hours   + (hours   === 1 ? ' hour'   : ' hours'));
  if (minutes > 0 && days === 0) parts.push(minutes + (minutes === 1 ? ' minute' : ' minutes'));

  el.textContent = parts.length ? parts.join(', ') : 'Just now';
});
