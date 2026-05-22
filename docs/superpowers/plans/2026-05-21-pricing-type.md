# Pricing Type on Proposals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fixed-price vs hourly-rate pricing to proposals, with `amount` auto-calculated from `hourly_rate × estimated_hours` for hourly proposals.

**Architecture:** Three new fields on `Proposal` (`pricing_type`, `hourly_rate`, `estimated_hours`). `save()` override computes `amount` when pricing is hourly. Form validates hourly-specific fields. Templates toggle field visibility via vanilla JS. Analytics and exports are unchanged — they always read `amount`.

**Tech Stack:** Django 5.x, Tailwind CSS, vanilla JS (no new dependencies)

---

## Files

| File | Action |
|---|---|
| `apps/proposals/models.py` | Add `PricingType`, 3 fields, override `save()` |
| `apps/proposals/migrations/0003_proposal_pricing_type.py` | New migration (auto-generated) |
| `apps/proposals/forms.py` | Add 3 fields + `clean()` validation |
| `templates/proposals/proposal_form.html` | Pricing toggle, show/hide sections, live total JS |
| `templates/proposals/proposal_detail.html` | Pricing breakdown in summary strip |
| `tests/test_proposals.py` | New test classes for model + form + view |

---

## Task 1: Model — PricingType + fields + save() override

**Files:**
- Modify: `apps/proposals/models.py`
- Test: `tests/test_proposals.py`

- [ ] **Step 1.1: Write failing tests — add to `tests/test_proposals.py`**

Append this class after the existing `TestProposalModel` class:

```python
@pytest.mark.django_db
class TestProposalPricingType:
    def test_default_pricing_type_is_fixed(self, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(owner=user, title="Test", client=client_model)
        assert p.pricing_type == PricingType.FIXED

    def test_hourly_auto_calculates_amount(self, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Hourly Test",
            client=client_model,
            pricing_type=PricingType.HOURLY,
            hourly_rate=Decimal("50.00"),
            estimated_hours=Decimal("20.00"),
        )
        assert p.amount == Decimal("1000.00")

    def test_fixed_keeps_manual_amount(self, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Fixed Test",
            client=client_model,
            pricing_type=PricingType.FIXED,
            amount=Decimal("500.00"),
        )
        assert p.amount == Decimal("500.00")

    def test_hourly_without_rate_does_not_change_amount(self, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Incomplete Hourly",
            client=client_model,
            pricing_type=PricingType.HOURLY,
            amount=Decimal("999.00"),
            hourly_rate=None,
            estimated_hours=None,
        )
        assert p.amount == Decimal("999.00")

    def test_hourly_recalculates_on_update(self, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Hourly Update",
            client=client_model,
            pricing_type=PricingType.HOURLY,
            hourly_rate=Decimal("50.00"),
            estimated_hours=Decimal("10.00"),
        )
        p.estimated_hours = Decimal("20.00")
        p.save()
        p.refresh_from_db()
        assert p.amount == Decimal("1000.00")
```

- [ ] **Step 1.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_proposals.py::TestProposalPricingType -v --no-cov
```

Expected: `ImportError: cannot import name 'PricingType'`

- [ ] **Step 1.3: Add `PricingType` class to `apps/proposals/models.py`**

After the `ProposalStatus` class (around line 92), add:

```python
class PricingType(models.TextChoices):
    FIXED = "fixed", _("Fixed Price")
    HOURLY = "hourly", _("Hourly Rate")
```

- [ ] **Step 1.4: Add 3 fields to `Proposal` model**

After the `paid = models.BooleanField(default=False)` line (around line 163), add:

```python
    pricing_type = models.CharField(
        max_length=10,
        choices=PricingType.choices,
        default=PricingType.FIXED,
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
```

- [ ] **Step 1.5: Override `save()` on `Proposal`**

Add this method to the `Proposal` class, before `__str__`:

```python
    def save(self, *args, **kwargs):
        if (
            self.pricing_type == PricingType.HOURLY
            and self.hourly_rate is not None
            and self.estimated_hours is not None
        ):
            self.amount = self.hourly_rate * self.estimated_hours
        super().save(*args, **kwargs)
```

- [ ] **Step 1.6: Run tests — verify they pass**

```bash
uv run pytest tests/test_proposals.py::TestProposalPricingType -v --no-cov
```

Expected: 5 passed

---

## Task 2: Migration

**Files:**
- Create: `apps/proposals/migrations/0003_proposal_pricing_type.py` (auto-generated)

- [ ] **Step 2.1: Generate migration**

```bash
uv run python manage.py makemigrations proposals --name pricing_type
```

Expected output:
```
Migrations for 'proposals':
  apps/proposals/migrations/0003_proposal_pricing_type.py
    - Add field estimated_hours to proposal
    - Add field hourly_rate to proposal
    - Add field pricing_type to proposal
```

- [ ] **Step 2.2: Apply migration**

```bash
uv run python manage.py migrate
```

Expected: `Applying proposals.0003_proposal_pricing_type... OK`

- [ ] **Step 2.3: Run full test suite to check no regressions**

```bash
uv run pytest --no-cov -q
```

Expected: all existing tests pass

- [ ] **Step 2.4: Commit**

```bash
git add apps/proposals/models.py apps/proposals/migrations/0003_proposal_pricing_type.py tests/test_proposals.py
git commit -m "feat(proposals): add pricing_type, hourly_rate, estimated_hours fields"
```

---

## Task 3: Form — add fields + validation

**Files:**
- Modify: `apps/proposals/forms.py`
- Test: `tests/test_proposals.py`

- [ ] **Step 3.1: Write failing form tests — append to `tests/test_proposals.py`**

```python
@pytest.mark.django_db
class TestProposalFormPricing:
    BASE_DATA = {
        "title": "Test Proposal",
        "status": "draft",
        "platform": "other",
        "amount": "0",
        "proposal_text": "",
        "job_url": "",
        "proposal_url": "",
        "new_client_name": "",
        "new_client_email": "",
    }

    def _form(self, user, extra):
        from apps.proposals.forms import ProposalForm

        data = {**self.BASE_DATA, **extra}
        return ProposalForm(data=data, user=user)

    def test_hourly_requires_hourly_rate(self, user):
        form = self._form(
            user,
            {"pricing_type": "hourly", "hourly_rate": "", "estimated_hours": "10"},
        )
        assert not form.is_valid()
        assert "hourly_rate" in form.errors

    def test_hourly_requires_estimated_hours(self, user):
        form = self._form(
            user,
            {"pricing_type": "hourly", "hourly_rate": "50", "estimated_hours": ""},
        )
        assert not form.is_valid()
        assert "estimated_hours" in form.errors

    def test_hourly_valid_with_both_fields(self, user):
        form = self._form(
            user,
            {"pricing_type": "hourly", "hourly_rate": "50", "estimated_hours": "20"},
        )
        assert form.is_valid(), form.errors

    def test_fixed_valid_without_hourly_fields(self, user):
        form = self._form(
            user,
            {
                "pricing_type": "fixed",
                "amount": "500",
                "hourly_rate": "",
                "estimated_hours": "",
            },
        )
        assert form.is_valid(), form.errors
```

- [ ] **Step 3.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_proposals.py::TestProposalFormPricing -v --no-cov
```

Expected: failures because `pricing_type` not in form fields yet.

- [ ] **Step 3.3: Update `ProposalForm` in `apps/proposals/forms.py`**

Update the import line to include `PricingType`:

```python
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus, PricingType
```

In `ProposalForm.Meta.fields`, insert the three new fields after `"amount"`:

```python
        fields = [
            "title",
            "platform",
            "client",
            "proposal_text",
            "amount",
            "pricing_type",
            "hourly_rate",
            "estimated_hours",
            "status",
            "sent_date",
            "expected_response_date",
            "job_url",
            "proposal_url",
            "tags",
            "new_client_name",
            "new_client_email",
        ]
```

Add a `clean()` method to `ProposalForm` (after `__init__`, before `save()`):

```python
    def clean(self):
        cleaned_data = super().clean()
        pricing_type = cleaned_data.get("pricing_type")
        if pricing_type == PricingType.HOURLY:
            if not cleaned_data.get("hourly_rate"):
                self.add_error("hourly_rate", _("Required for hourly pricing."))
            if not cleaned_data.get("estimated_hours"):
                self.add_error("estimated_hours", _("Required for hourly pricing."))
        return cleaned_data
```

- [ ] **Step 3.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_proposals.py::TestProposalFormPricing -v --no-cov
```

Expected: 4 passed

- [ ] **Step 3.5: Run full test suite**

```bash
uv run pytest --no-cov -q
```

Expected: all pass

- [ ] **Step 3.6: Commit**

```bash
git add apps/proposals/forms.py tests/test_proposals.py
git commit -m "feat(proposals): add pricing type validation to ProposalForm"
```

---

## Task 4: Template — proposal_form.html

**Files:**
- Modify: `templates/proposals/proposal_form.html`

- [ ] **Step 4.1: Replace the Amount block with the pricing block**

In `templates/proposals/proposal_form.html`, find and replace the entire `<!-- Amount -->` block (lines 37–47):

**OLD:**
```html
            <!-- Amount -->
            <div class="col-span-12 md:col-span-4 flex flex-col gap-2">
                <label class="font-label-md text-label-md text-on-surface-variant flex items-center gap-1" for="id_amount">
                    {% trans "Amount (USD)" %} <span class="text-error">*</span>
                </label>
                <div class="relative currency-field">
                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-label-md z-10">$</span>
                    {{ form.amount }}
                </div>
                {% if form.amount.errors %}<p class="font-body-sm text-body-sm text-error">{{ form.amount.errors.0 }}</p>{% endif %}
            </div>
```

**NEW:**
```html
            <!-- Pricing type -->
            <div class="col-span-12 md:col-span-4 flex flex-col gap-2">
                <label class="font-label-md text-label-md text-on-surface-variant" for="id_pricing_type">{% trans "Pricing Type" %}</label>
                {{ form.pricing_type }}
            </div>

            <!-- Fixed price amount (shown when pricing_type=fixed) -->
            <div id="pricing-fixed-section" class="col-span-12 md:col-span-4 flex flex-col gap-2">
                <label class="font-label-md text-label-md text-on-surface-variant flex items-center gap-1" for="id_amount">
                    {% trans "Amount (USD)" %} <span class="text-error">*</span>
                </label>
                <div class="relative currency-field">
                    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-label-md z-10">$</span>
                    {{ form.amount }}
                </div>
                {% if form.amount.errors %}<p class="font-body-sm text-body-sm text-error">{{ form.amount.errors.0 }}</p>{% endif %}
            </div>

            <!-- Hourly rate + estimated hours (shown when pricing_type=hourly) -->
            <div id="pricing-hourly-section" class="col-span-12 md:col-span-8 hidden">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="flex flex-col gap-2">
                        <label class="font-label-md text-label-md text-on-surface-variant flex items-center gap-1" for="id_hourly_rate">
                            {% trans "Hourly Rate" %} <span class="text-error">*</span>
                        </label>
                        <div class="relative currency-field">
                            <span class="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant font-label-md z-10">$</span>
                            {{ form.hourly_rate }}
                        </div>
                        {% if form.hourly_rate.errors %}<p class="font-body-sm text-body-sm text-error">{{ form.hourly_rate.errors.0 }}</p>{% endif %}
                    </div>
                    <div class="flex flex-col gap-2">
                        <label class="font-label-md text-label-md text-on-surface-variant flex items-center gap-1" for="id_estimated_hours">
                            {% trans "Estimated Hours" %} <span class="text-error">*</span>
                        </label>
                        {{ form.estimated_hours }}
                        {% if form.estimated_hours.errors %}<p class="font-body-sm text-body-sm text-error">{{ form.estimated_hours.errors.0 }}</p>{% endif %}
                    </div>
                    <div class="flex flex-col gap-2 justify-end">
                        <p class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Total" %}</p>
                        <p id="hourly-total-preview" class="font-h3 text-h3 text-on-surface">—</p>
                    </div>
                </div>
            </div>
```

- [ ] **Step 4.2: Add JS to `{% block extra_js %}` in `proposal_form.html`**

The template currently has no `{% block extra_js %}`. Add it just before `{% endblock %}` at the end:

```html
{% block extra_js %}
<script>
(function () {
  const pricingSelect = document.getElementById('id_pricing_type');
  const fixedSection  = document.getElementById('pricing-fixed-section');
  const hourlySection = document.getElementById('pricing-hourly-section');
  const rateInput     = document.getElementById('id_hourly_rate');
  const hoursInput    = document.getElementById('id_estimated_hours');
  const totalPreview  = document.getElementById('hourly-total-preview');

  function updateVisibility() {
    const isHourly = pricingSelect.value === 'hourly';
    fixedSection.classList.toggle('hidden', isHourly);
    hourlySection.classList.toggle('hidden', !isHourly);
  }

  function updateTotal() {
    const rate  = parseFloat(rateInput.value)  || 0;
    const hours = parseFloat(hoursInput.value) || 0;
    if (rate > 0 && hours > 0) {
      const total = (rate * hours).toFixed(2);
      totalPreview.textContent = '$' + parseFloat(total).toLocaleString('en-US', {minimumFractionDigits: 2});
    } else {
      totalPreview.textContent = '—';
    }
  }

  pricingSelect.addEventListener('change', updateVisibility);
  rateInput.addEventListener('input', updateTotal);
  hoursInput.addEventListener('input', updateTotal);

  // Init on load (handles edit mode where value may already be 'hourly')
  updateVisibility();
  updateTotal();
})();
</script>
{% endblock %}
```

- [ ] **Step 4.3: Also apply `currency-input` style to hourly_rate in `__init__`**

In `apps/proposals/forms.py`, inside `ProposalForm.__init__`, after the existing `amount` widget styling lines, add:

```python
        self.fields["hourly_rate"].widget.attrs["class"] = (
            self.fields["hourly_rate"].widget.attrs.get("class", "") + " currency-input"
        ).strip()
        self.fields["hourly_rate"].widget.attrs["style"] = "padding-left: 2.25rem;"
```

- [ ] **Step 4.4: Verify form renders correctly**

```bash
uv run python manage.py runserver
```

Open `http://localhost:8000/proposals/new/` in browser.

Check:
- "Fixed Price" selected by default → Amount field visible, Hourly section hidden
- Switch to "Hourly Rate" → Hourly Rate + Estimated Hours visible, Amount hidden
- Enter rate=50, hours=20 → Total preview shows "$1,000.00"
- Switch back to Fixed → Amount visible again, Hourly hidden

- [ ] **Step 4.5: Commit**

```bash
git add templates/proposals/proposal_form.html apps/proposals/forms.py
git commit -m "feat(proposals): add pricing type toggle to proposal form"
```

---

## Task 5: Template — proposal_detail.html + view test

**Files:**
- Modify: `templates/proposals/proposal_detail.html`
- Test: `tests/test_proposals.py`

- [ ] **Step 5.1: Write failing view test — append to `tests/test_proposals.py`**

```python
@pytest.mark.django_db
class TestProposalDetailPricing:
    def test_detail_shows_fixed_amount(self, authed_client, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Fixed",
            client=client_model,
            pricing_type=PricingType.FIXED,
            amount=Decimal("500.00"),
        )
        url = reverse("proposal-detail", kwargs={"pk": p.pk})
        response = authed_client.get(url)
        assert response.status_code == 200
        assert b"500" in response.content

    def test_detail_shows_hourly_breakdown(self, authed_client, user, client_model):
        from apps.proposals.models import Proposal, PricingType

        p = Proposal.objects.create(
            owner=user,
            title="Hourly",
            client=client_model,
            pricing_type=PricingType.HOURLY,
            hourly_rate=Decimal("50.00"),
            estimated_hours=Decimal("10.00"),
        )
        url = reverse("proposal-detail", kwargs={"pk": p.pk})
        response = authed_client.get(url)
        assert response.status_code == 200
        assert b"50" in response.content   # hourly rate
        assert b"10" in response.content   # estimated hours
        assert b"500" in response.content  # total (50 * 10)
```

- [ ] **Step 5.2: Run tests — verify they fail (detail test)**

```bash
uv run pytest tests/test_proposals.py::TestProposalDetailPricing -v --no-cov
```

Expected: `test_detail_shows_hourly_breakdown` fails (no breakdown rendered yet).

- [ ] **Step 5.3: Update summary strip in `proposal_detail.html`**

Find and replace the "Amount" `<div>` in the Summary Strip (the third card, around line 62–66):

**OLD:**
```html
            <div>
                <p class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">{% trans "Amount" %}</p>
                <p class="font-h3 text-h3 text-on-surface">${{ proposal.amount|default:"—" }}</p>
            </div>
```

**NEW:**
```html
            <div>
                {% if proposal.pricing_type == 'hourly' %}
                <p class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">{% trans "Hourly Rate" %}</p>
                <p class="font-h3 text-h3 text-on-surface">${{ proposal.hourly_rate|default:"—" }}<span class="font-body-sm text-body-sm text-on-surface-variant">/h</span></p>
                {% if proposal.estimated_hours %}
                <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">
                    {{ proposal.estimated_hours }}h &times; ${{ proposal.hourly_rate }} = <strong>${{ proposal.amount }}</strong>
                </p>
                {% endif %}
                {% else %}
                <p class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">{% trans "Amount" %}</p>
                <p class="font-h3 text-h3 text-on-surface">${{ proposal.amount|default:"—" }}</p>
                {% endif %}
            </div>
```

- [ ] **Step 5.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_proposals.py::TestProposalDetailPricing -v --no-cov
```

Expected: 2 passed

- [ ] **Step 5.5: Verify detail page in browser**

With the server running, create a new hourly proposal (50/h × 10h). Open its detail page.

Check:
- Summary strip shows "Hourly Rate" label with "$50.00/h"
- Sub-line shows "10h × $50.00 = $500.00"

Create a fixed proposal ($750). Open its detail page.

Check:
- Summary strip shows "Amount" label with "$750.00"

- [ ] **Step 5.6: Run full test suite + linting**

```bash
uv run pytest --no-cov -q
uv run ruff check .
uv run ruff format --check .
```

Expected: all pass, no lint errors.

- [ ] **Step 5.7: Final commit**

```bash
git add templates/proposals/proposal_detail.html tests/test_proposals.py
git commit -m "feat(proposals): show pricing breakdown in proposal detail view"
```

---

## Task 6: Type checking

**Files:**
- `apps/proposals/models.py`
- `apps/proposals/forms.py`

- [ ] **Step 6.1: Run mypy**

```bash
uv run mypy apps/proposals/models.py apps/proposals/forms.py
```

Expected: no errors. If mypy reports `Optional[Decimal]` issues on `hourly_rate`/`estimated_hours`, the guard `is not None` in `save()` already handles them — mypy may need type: ignore on the multiplication line if it can't infer it. Add `# type: ignore[operator]` only if needed.

- [ ] **Step 6.2: Run coverage check**

```bash
uv run pytest --cov --cov-fail-under=75
```

Expected: passes ≥75% threshold.

- [ ] **Step 6.3: Final verification commit (if any mypy fixes were needed)**

```bash
git add -p
git commit -m "fix(proposals): mypy type annotations for pricing fields"
```
