document.addEventListener('DOMContentLoaded', () => {
  const pricingSelect = document.getElementById('id_pricing_type');
  const fixedSection  = document.getElementById('pricing-fixed-section');
  const hourlySection = document.getElementById('pricing-hourly-section');
  const rateInput     = document.getElementById('id_hourly_rate');
  const hoursInput    = document.getElementById('id_estimated_hours');
  const totalPreview  = document.getElementById('hourly-total-preview');

  if (!pricingSelect) return;

  function updateVisibility() {
    const isHourly = pricingSelect.value === 'hourly';
    fixedSection.classList.toggle('hidden', isHourly);
    hourlySection.classList.toggle('hidden', !isHourly);
  }

  function updateTotal() {
    const rate  = parseFloat(rateInput.value)  || 0;
    const hours = parseFloat(hoursInput.value) || 0;
    if (rate > 0 && hours > 0) {
      totalPreview.textContent = '$' + (rate * hours).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    } else {
      totalPreview.textContent = '—';
    }
  }

  pricingSelect.addEventListener('change', updateVisibility);
  rateInput.addEventListener('input', updateTotal);
  hoursInput.addEventListener('input', updateTotal);

  updateVisibility();
  updateTotal();
});
