# Period Filters Design

**Date:** 2026-05-21  
**Status:** Approved

## Overview

Two independent filter enhancements:
1. Time period filter on the Proposals list
2. Extended period selector on the Monthly Summary / Analytics page

---

## Feature 1: Proposals Period Filter

### Goal

Allow users to narrow the proposals list to a specific month and year, filtering on either `sent_date` or `created_at`.

### URL Params

```
/proposals/?year=2026&month=5&date_field=sent_date&status=...&platform=...
```

New params:
- `year` — integer (e.g., `2026`)
- `month` — integer 1–12 (e.g., `5` for May)
- `date_field` — `sent_date` (default) or `created_at`

Existing params (`status`, `platform`) continue to work and combine with new ones.

### View: `ProposalListView.get_queryset`

File: `apps/proposals/views.py`

Logic added after existing status/platform filters:

```python
year = self.request.GET.get("year")
month = self.request.GET.get("month")
date_field = self.request.GET.get("date_field", "sent_date")

if year and month:
    year, month = int(year), int(month)
    if date_field == "sent_date":
        qs = qs.filter(
            Q(sent_date__year=year, sent_date__month=month)
            | Q(sent_date__isnull=True, created_at__year=year, created_at__month=month)
        )
    else:
        qs = qs.filter(created_at__year=year, created_at__month=month)
```

This is consistent with the analytics null-fallback pattern documented in CLAUDE.md.

### View: `ProposalListView.get_context_data`

Pass to template:
- `year_choices` — last 5 years descending (e.g., 2026..2022)
- `month_choices` — list of `(int, str)` tuples: `[(1, "January"), ..., (12, "December")]`
- `selected_year`, `selected_month`, `selected_date_field` — current GET values

### Template: `templates/proposals/proposal_list.html`

Extend the existing filter bar (`<form id="filter-form">`):

New controls added inline with existing status/platform selects:
- `year` select (populated from `year_choices`)
- `month` select (populated from `month_choices`, first option "All Months")
- `date_field` select: options "Sent Date" / "Created Date"

All selects use `onchange="document.getElementById('filter-form').submit()"` (existing pattern).

Update "Clear" link to `{% url 'proposal-list' %}` (already clears all GET params — no change needed).

Update "Clear" visibility condition: also check `request.GET.year or request.GET.month`.

### No model or migration changes.

---

## Feature 2: Monthly Summary Extended Period Selector

### Goal

Replace the 3-option period selector (Last 30 / Last 90 / This Year) with a flexible selector supporting: Monthly, Quarterly, Semi-annual, Annual — each paired with a year picker.

### URL Params

| Period | Extra param | Example |
|---|---|---|
| `monthly` | `month=1..12` | `?period=monthly&year=2026&month=5` |
| `quarterly` | `quarter=1..4` | `?period=quarterly&year=2026&quarter=1` |
| `semi-annual` | `half=1` or `half=2` | `?period=semi-annual&year=2026&half=1` |
| `annual` | *(none)* | `?period=annual&year=2026` |

Old `period=30` and `period=90` values are **removed**. Old `period=year` becomes `period=annual`.

### Date Range Resolution (view)

File: `apps/dashboard/views.py`, `MonthlySummaryView.get_context_data`

```
monthly:      start = date(year, month, 1)
              end   = start + relativedelta(months=1)
              label = "January 2026"

quarterly:    start = date(year, (quarter-1)*3 + 1, 1)
              end   = start + relativedelta(months=3)
              label = "Q1 2026"

semi-annual:  start = date(year, 1, 1) if half==1 else date(year, 7, 1)
              end   = start + relativedelta(months=6)
              label = "H1 2026"

annual:       start = date(year, 1, 1)
              end   = date(year+1, 1, 1)
              label = "2026"
```

Use stdlib `calendar` + manual arithmetic (no `dateutil` in project). Helper: `date(year + (month)//12, (month-1)%12 + 1, 1)` to advance by N months.

Default period (no params): `quarterly`, current year, current quarter.

### Context additions

Beyond existing `summary`, `year`, `period`, `chart_*`, `platform_*`:
- `month` — int, selected month (for monthly mode)
- `quarter` — int 1–4 (for quarterly mode)
- `half` — int 1–2 (for semi-annual mode)
- `month_choices` — `[(1, "January"), ..., (12, "December")]`
- `year_choices` — last 5 years descending

### Template: `templates/dashboard/monthly_summary.html`

**Period select** — replace existing 3 options with:
```
Monthly | Quarterly | Semi-annual | Annual
```

**Secondary selector** — JS shows/hides below the period select:
- `monthly` → month select (Jan–Dec)
- `quarterly` → Q1 / Q2 / Q3 / Q4 select
- `semi-annual` → H1 / H2 select
- `annual` → nothing (year already shown)

**Year input** — always visible (all modes need year). Existing year input reused.

JS logic: on `period` change, hide all secondary selectors, show the relevant one. Mirror existing `syncYear()` pattern.

### No service layer changes

`MonthlySummaryGenerator.generate(user, start_date, end_date, period_label)` is unchanged — it already accepts arbitrary date ranges.

`DashboardService` methods (`get_earnings_chart`, `get_platform_conversion`, `get_platform_stats`) also unchanged.

---

## Testing

- `tests/test_proposals.py` — add cases for year/month/date_field param combinations, including null `sent_date` fallback behavior
- `tests/test_dashboard.py` — add cases for all four period modes, verify correct `start_date`/`end_date` passed to generator

## Out of Scope

- Custom date range picker
- Saving filter preferences
- URL-shareable filter state (already handled by GET params)
