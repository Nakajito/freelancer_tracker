document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('filter-form');
  if (!form) return;
  form.querySelectorAll('select').forEach(s => {
    s.addEventListener('change', () => form.submit());
  });
});
