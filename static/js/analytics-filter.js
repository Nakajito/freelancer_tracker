document.addEventListener('DOMContentLoaded', () => {
  var form = document.querySelector('#analytics-filter-form');
  var periodSelect = document.getElementById('period');
  if (!form || !periodSelect) return;

  var monthWrapper   = document.getElementById('month-wrapper');
  var quarterWrapper = document.getElementById('quarter-wrapper');
  var halfWrapper    = document.getElementById('half-wrapper');

  function syncSecondary() {
    var v = periodSelect.value;
    if (monthWrapper)   monthWrapper.style.display   = v === 'monthly'     ? '' : 'none';
    if (quarterWrapper) quarterWrapper.style.display = v === 'quarterly'   ? '' : 'none';
    if (halfWrapper)    halfWrapper.style.display    = v === 'semi-annual' ? '' : 'none';
  }

  periodSelect.addEventListener('change', function () {
    syncSecondary();
    form.submit();
  });

  ['year', 'month-select', 'quarter-select', 'half-select'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('change', function () { form.submit(); });
  });

  syncSecondary();
});
