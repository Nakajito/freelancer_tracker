# Pricing Type on Proposals

**Date:** 2026-05-21
**Status:** Approved

## Summary

Add a `pricing_type` field to `Proposal` with two options: Fixed Price and Hourly Rate. For hourly proposals, the user enters `hourly_rate` and `estimated_hours`; `amount` is auto-calculated as their product. Analytics and exports remain unchanged since they always read `amount`.

## Model Changes

Three new fields on `apps/proposals/models.py`:

```python
class PricingType(models.TextChoices):
    FIXED = "fixed", _("Fixed Price")
    HOURLY = "hourly", _("Hourly Rate")

# On Proposal:
pricing_type = models.CharField(
    max_length=10, choices=PricingType.choices, default=PricingType.FIXED
)
hourly_rate = models.DecimalField(
    max_digits=10, decimal_places=2, null=True, blank=True,
    validators=[MinValueValidator(Decimal("0.01"))],
)
estimated_hours = models.DecimalField(
    max_digits=6, decimal_places=2, null=True, blank=True,
    validators=[MinValueValidator(Decimal("0.01"))],
)
```

`save()` override:

```python
def save(self, *args, **kwargs):
    if self.pricing_type == PricingType.HOURLY and self.hourly_rate and self.estimated_hours:
        self.amount = self.hourly_rate * self.estimated_hours
    super().save(*args, **kwargs)
```

Existing proposals default to `pricing_type=fixed`, `hourly_rate=null`, `estimated_hours=null`.

## Migration

Single migration: add 3 fields with their defaults. No data migration needed.

## Form Changes (`apps/proposals/forms.py`)

- Add `pricing_type`, `hourly_rate`, `estimated_hours` to `ProposalForm.Meta.fields`
- Validation in `clean()`: if `pricing_type == HOURLY`, both `hourly_rate` and `estimated_hours` must be present and > 0
- For hourly, `amount` is not required from the user (it will be computed in `save()`)

## Template: proposal_form.html

Replace the current Amount section with a pricing block:

1. **Radio toggle** — "Fixed Price" / "Hourly Rate" (default: Fixed)
2. **Fixed section** (shown when Fixed selected): existing `amount` field with `$` prefix
3. **Hourly section** (shown when Hourly selected):
   - `hourly_rate` field with `$` prefix and `/h` suffix
   - `estimated_hours` field
   - Live total preview: `$X/h × Yh = $Z` (computed via JS)
4. JS: on toggle, show/hide sections and update `required` attrs accordingly

## Template: proposal_detail.html

In the Summary Strip, replace the "Amount" card with a "Pricing" card:

- **Fixed**: label "Amount" → `$1,234.00` (unchanged)
- **Hourly**: label "Rate" → `$50.00/h` + sub-line `20h estimated → $1,000.00`

## Analytics / Exports Impact

None. `amount` is always populated (auto-calculated for hourly on save). All dashboard queries, CSV/JSON exports, and `DashboardService` methods read `amount` directly — no changes needed.

## Tests

| Test | Location |
|---|---|
| `Proposal.save()` auto-calculates `amount` for hourly | `tests/test_proposals.py` |
| `Proposal.save()` does not override `amount` for fixed | `tests/test_proposals.py` |
| Form validation fails when hourly fields missing | `tests/test_proposals.py` |
| Form validation passes with valid hourly data | `tests/test_proposals.py` |
| Detail view shows rate breakdown for hourly proposal | `tests/test_proposals.py` |

## Out of Scope

- Changing time entry / retainer logic (they work with `amount` as-is)
- Currency selector
- Filtering proposals by pricing type in list view
