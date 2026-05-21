# Period Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a month+year period filter to the Proposals list, and replace the analytics period selector with monthly/quarterly/semi-annual/annual modes with a year picker.

**Architecture:** Both features are view+template changes only — no model or service layer changes. The proposals view gains three new GET params (year, month, date_field); the dashboard view gains a `_add_months` helper and four period branches. Templates gain new select controls; the dashboard template JS is updated to show/hide secondary selectors.

**Tech Stack:** Django class-based views, Django QuerySet Q filters, stdlib `calendar`, Tailwind CSS, vanilla JS (no extra dependencies).

---

## File Map

| File | Change |
|---|---|
| `apps/proposals/views.py` | Add period filter to `get_queryset` + context vars to `get_context_data` |
| `apps/dashboard/views.py` | Add `_add_months` helper + four period branches in `MonthlySummaryView` |
| `templates/proposals/proposal_list.html` | Add year/month/date_field selects to filter bar |
| `templates/dashboard/monthly_summary.html` | Replace period options, add secondary selectors, update JS |
| `tests/test_proposals.py` | Add `TestProposalListPeriodFilter` class |
| `tests/test_dashboard.py` | Replace/update `TestMonthlySummaryViewPeriodFilter` tests |

---

## Task 1: Proposals view — period filter logic (TDD)

**Files:**
- Modify: `apps/proposals/views.py`
- Test: `tests/test_proposals.py`

- [ ] **Step 1: Write failing tests**

Append this class to `tests/test_proposals.py`:

```python
@pytest.mark.django_db
class TestProposalListPeriodFilter:
    def _proposal(self, user, client_model, sent_date=None, **kwargs):
        return Proposal.objects.create(
            owner=user,
            title=f"P-{sent_date}",
            client=client_model,
            status=ProposalStatus.DRAFT,
            sent_date=sent_date,
            **kwargs,
        )

    def test_year_month_filter_sent_date(self, authed_client, user, client_model):
        self._proposal(user, client_model, sent_date=date(2026, 5, 10))
        self._proposal(user, client_model, sent_date=date(2026, 3, 10))
        url = reverse("proposal-list") + "?year=2026&month=5&date_field=sent_date"
        response = authed_client.get(url)
        assert response.status_code == 200
        assert len(list(response.context["proposals"])) == 1

    def test_year_month_filter_created_at(self, authed_client, user, client_model):
        self._proposal(user, client_model)  # created now, no sent_date
        today = date.today()
        url = reverse("proposal-list") + f"?year={today.year}&month={today.month}&date_field=created_at"
        response = authed_client.get(url)
        assert len(list(response.context["proposals"])) >= 1

    def test_sent_date_null_fallback(self, authed_client, user, client_model):
        # proposal with no sent_date → should match via created_at
        p = self._proposal(user, client_model)  # sent_date=None
        today = date.today()
        url = reverse("proposal-list") + f"?year={today.year}&month={today.month}&date_field=sent_date"
        response = authed_client.get(url)
        assert p in list(response.context["proposals"])

    def test_no_period_params_returns_all(self, authed_client, user, client_model, proposal):
        response = authed_client.get(reverse("proposal-list"))
        assert response.status_code == 200
        assert proposal in list(response.context["proposals"])

    def test_context_has_year_and_month_choices(self, authed_client):
        response = authed_client.get(reverse("proposal-list"))
        ctx = response.context
        assert "year_choices" in ctx
        assert "month_choices" in ctx
        assert len(ctx["month_choices"]) == 12
        assert len(ctx["year_choices"]) == 5

    def test_period_combines_with_status_filter(self, authed_client, user, client_model):
        self._proposal(user, client_model, sent_date=date(2026, 5, 1), status=ProposalStatus.SENT)
        self._proposal(user, client_model, sent_date=date(2026, 5, 2), status=ProposalStatus.DRAFT)
        url = reverse("proposal-list") + "?year=2026&month=5&date_field=sent_date&status=sent"
        response = authed_client.get(url)
        proposals = list(response.context["proposals"])
        assert len(proposals) == 1
        assert proposals[0].status == ProposalStatus.SENT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_proposals.py::TestProposalListPeriodFilter -v --no-cov
```

Expected: all 6 tests FAIL (missing context vars, filter logic not yet added).

- [ ] **Step 3: Implement period filter in `apps/proposals/views.py`**

Replace the full file content:

```python
import calendar
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.mixins import OwnerQuerysetMixin
from apps.proposals.forms import ProposalForm
from apps.proposals.models import Client, Platform, Proposal, ProposalStatus


class ProposalListView(OwnerQuerysetMixin, ListView):
    model = Proposal
    template_name = "proposals/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().with_client().with_tags()
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        platform = self.request.GET.get("platform")
        if platform:
            qs = qs.filter(platform=platform)

        year = self.request.GET.get("year")
        month = self.request.GET.get("month")
        date_field = self.request.GET.get("date_field", "sent_date")

        if year and month:
            y, m = int(year), int(month)
            if date_field == "sent_date":
                qs = qs.filter(
                    Q(sent_date__year=y, sent_date__month=m)
                    | Q(sent_date__isnull=True, created_at__year=y, created_at__month=m)
                )
            else:
                qs = qs.filter(created_at__year=y, created_at__month=m)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = list(ProposalStatus.choices)
        context["platform_choices"] = list(Platform.choices)

        today = date.today()
        context["year_choices"] = list(range(today.year, today.year - 5, -1))
        context["month_choices"] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        context["selected_year"] = self.request.GET.get("year", "")
        context["selected_month"] = self.request.GET.get("month", "")
        context["selected_date_field"] = self.request.GET.get("date_field", "sent_date")
        return context


class ProposalDetailView(OwnerQuerysetMixin, DetailView):
    model = Proposal
    template_name = "proposals/proposal_detail.html"


class ProposalCreateView(LoginRequiredMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("proposal-detail", kwargs={"pk": self.object.pk})


class ProposalUpdateView(OwnerQuerysetMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "proposals/proposal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("proposal-detail", kwargs={"pk": self.object.pk})


class ProposalDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Proposal
    template_name = "proposals/proposal_confirm_delete.html"
    success_url = reverse_lazy("proposal-list")


class ClientListView(OwnerQuerysetMixin, ListView):
    model = Client
    template_name = "proposals/client_list.html"
    context_object_name = "clients"


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = "proposals/client_form.html"
    fields = ["name", "email", "notes"]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("client-list")


class ClientDeleteView(OwnerQuerysetMixin, DeleteView):
    model = Client
    template_name = "proposals/client_confirm_delete.html"
    success_url = reverse_lazy("client-list")


class SearchView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        proposals: list = []
        clients: list = []
        if len(q) >= 2:
            proposals = list(
                Proposal.objects.for_user(request.user).search(q).with_client()[:6]
            )
            clients = list(
                Client.objects.filter(owner=request.user).filter(
                    Q(name__icontains=q) | Q(email__icontains=q)
                )[:4]
            )
        return render(
            request,
            "proposals/search_results.html",
            {"proposals": proposals, "clients": clients, "q": q},
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_proposals.py::TestProposalListPeriodFilter -v --no-cov
```

Expected: all 6 PASS.

- [ ] **Step 5: Run full proposals test suite to catch regressions**

```bash
uv run pytest tests/test_proposals.py -v --no-cov
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add apps/proposals/views.py tests/test_proposals.py
git commit -m "feat(proposals): add month/year period filter to proposal list view"
```

---

## Task 2: Proposals template — period filter controls

**Files:**
- Modify: `templates/proposals/proposal_list.html`

- [ ] **Step 1: Replace the filter form section**

In `templates/proposals/proposal_list.html`, replace the entire `<!-- Filters -->` block (lines 29–57) with:

```html
<!-- Filters -->
<form method="get" id="filter-form" class="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 mb-stack-md flex flex-col gap-4 shadow-xs">
    <div class="flex flex-col sm:flex-row flex-wrap gap-4 items-center">
        <div class="relative min-w-[160px]">
            <select name="status" onchange="document.getElementById('filter-form').submit()" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="">{% trans "All Statuses" %}</option>
                {% for value,label in status_choices %}
                <option value="{{ value }}" {% if request.GET.status == value %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
        <div class="relative min-w-[160px]">
            <select name="platform" onchange="document.getElementById('filter-form').submit()" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="">{% trans "All Platforms" %}</option>
                {% for value,label in platform_choices %}
                <option value="{{ value }}" {% if request.GET.platform == value %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
        <div class="relative min-w-[120px]">
            <select name="year" onchange="document.getElementById('filter-form').submit()" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="">{% trans "All Years" %}</option>
                {% for y in year_choices %}
                <option value="{{ y }}" {% if selected_year == y|stringformat:"s" %}selected{% endif %}>{{ y }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
        <div class="relative min-w-[140px]">
            <select name="month" onchange="document.getElementById('filter-form').submit()" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="">{% trans "All Months" %}</option>
                {% for num,name in month_choices %}
                <option value="{{ num }}" {% if selected_month == num|stringformat:"s" %}selected{% endif %}>{{ name }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
        <div class="relative min-w-[150px]">
            <select name="date_field" onchange="document.getElementById('filter-form').submit()" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="sent_date" {% if selected_date_field == "sent_date" %}selected{% endif %}>{% trans "Sent Date" %}</option>
                <option value="created_at" {% if selected_date_field == "created_at" %}selected{% endif %}>{% trans "Created Date" %}</option>
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
        {% if request.GET.status or request.GET.platform or request.GET.year or request.GET.month %}
        <a href="{% url 'proposal-list' %}" class="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg font-label-md text-label-md hover:bg-surface-container transition-colors flex items-center gap-2 whitespace-nowrap">
            <span class="material-symbols-outlined text-[18px]">close</span>
            {% trans "Clear" %}
        </a>
        {% endif %}
    </div>
</form>
```

- [ ] **Step 2: Verify icon `arrow_drop_down` exists in font subset**

```bash
python bin/check-icons.py
```

Expected: no missing icons (arrow_drop_down already used in existing template). If missing, run `python bin/check-icons.py --patch`.

- [ ] **Step 3: Start dev server and manually test the filter**

```bash
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/proposals/ and verify:
- 5 selects visible: Status, Platform, Year, Month, Date field
- Selecting Year=2026 + Month=5 reloads and filters correctly
- "Clear" link appears when year or month is set, disappears after clearing
- Status + Platform filters still work alongside period filter

- [ ] **Step 4: Commit**

```bash
git add templates/proposals/proposal_list.html
git commit -m "feat(proposals): add year/month/date_field selects to filter bar"
```

---

## Task 3: Monthly Summary view — extended period logic (TDD)

**Files:**
- Modify: `apps/dashboard/views.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Update existing tests and add new ones**

In `tests/test_dashboard.py`, find class `TestMonthlySummaryViewPeriodFilter` and replace it entirely with:

```python
@pytest.mark.django_db
class TestMonthlySummaryViewPeriodFilter:
    def _proposal(self, user, client_model, sent_date, amount="500"):
        return Proposal.objects.create(
            owner=user,
            title=f"P-{sent_date}",
            client=client_model,
            status=ProposalStatus.ACCEPTED,
            amount=Decimal(amount),
            sent_date=sent_date,
        )

    def test_period_monthly_filters_to_correct_month(
        self, authed_client, user, client_model
    ):
        self._proposal(user, client_model, date(2026, 5, 10), "1000")
        self._proposal(user, client_model, date(2026, 4, 10), "2000")
        response = authed_client.get(
            reverse("monthly-summary") + "?period=monthly&year=2026&month=5"
        )
        assert response.status_code == 200
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("1000")
        assert response.context["period"] == "monthly"

    def test_period_quarterly_q1(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2026, 2, 15), "500")  # Q1
        self._proposal(user, client_model, date(2026, 5, 15), "700")  # Q2
        response = authed_client.get(
            reverse("monthly-summary") + "?period=quarterly&year=2026&quarter=1"
        )
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("500")

    def test_period_quarterly_q4_boundary(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2026, 12, 31), "300")  # Q4
        self._proposal(user, client_model, date(2027, 1, 1), "400")   # next year
        response = authed_client.get(
            reverse("monthly-summary") + "?period=quarterly&year=2026&quarter=4"
        )
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("300")

    def test_period_semi_annual_h1(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2026, 3, 1), "400")  # H1
        self._proposal(user, client_model, date(2026, 8, 1), "600")  # H2
        response = authed_client.get(
            reverse("monthly-summary") + "?period=semi-annual&year=2026&half=1"
        )
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("400")

    def test_period_semi_annual_h2(self, authed_client, user, client_model):
        self._proposal(user, client_model, date(2026, 3, 1), "400")  # H1
        self._proposal(user, client_model, date(2026, 8, 1), "600")  # H2
        response = authed_client.get(
            reverse("monthly-summary") + "?period=semi-annual&year=2026&half=2"
        )
        summary = response.context["summary"]
        assert summary["total_amount"] == Decimal("600")

    def test_period_annual_filters_to_correct_year(
        self, authed_client, user, client_model
    ):
        self._proposal(user, client_model, date(2025, 6, 1), "1000")
        self._proposal(user, client_model, date(2026, 1, 15), "2000")
        response = authed_client.get(
            reverse("monthly-summary") + "?period=annual&year=2025"
        )
        assert response.status_code == 200
        summary = response.context["summary"]
        assert summary["proposals_sent"] == 1
        assert summary["total_amount"] == Decimal("1000")

    def test_default_period_is_quarterly(self, authed_client):
        response = authed_client.get(reverse("monthly-summary"))
        assert response.status_code == 200
        assert response.context["period"] == "quarterly"

    def test_context_has_sub_selectors(self, authed_client):
        response = authed_client.get(
            reverse("monthly-summary") + "?period=quarterly&year=2026&quarter=2"
        )
        ctx = response.context
        assert ctx["quarter"] == 2
        assert ctx["month_choices"]
        assert ctx["year_choices"]

    def test_chart_anchor_matches_annual_period_end(
        self, authed_client, user, client_model
    ):
        self._proposal(user, client_model, date(2025, 10, 15), "750")
        response = authed_client.get(
            reverse("monthly-summary") + "?period=annual&year=2025"
        )
        assert response.status_code == 200
        import json
        chart_labels = json.loads(response.context["chart_labels"])
        assert chart_labels[-1] == "Dec 2025"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_dashboard.py::TestMonthlySummaryViewPeriodFilter -v --no-cov
```

Expected: most FAIL (old period values, missing context vars).

- [ ] **Step 3: Implement extended period logic in `apps/dashboard/views.py`**

Replace the full file content:

```python
import calendar
import json
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from apps.dashboard.services import DashboardService
from apps.exports.services import MonthlySummaryGenerator


def _add_months(year: int, month: int, n: int) -> date:
    """Return the first day of the month that is n months after (year, month)."""
    m = month + n
    return date(year + (m - 1) // 12, (m - 1) % 12 + 1, 1)


class LandingView(TemplateView):
    template_name = "dashboard/landing.html"


class DemoAutoLoginView(View):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        User = get_user_model()
        try:
            user = User.objects.get(email=settings.DEMO_USER_EMAIL)
        except User.DoesNotExist:
            messages.error(request, _("Demo not available. Please sign up."))
            return redirect("landing")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard")


class DemoSignupRedirectView(View):
    """Log out demo user and redirect to signup so the form is reachable."""

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return redirect("account_signup")


class DemoExitView(View):
    """Log out demo user and return to the landing page."""

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return redirect("landing")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["funnel"] = DashboardService.get_funnel_metrics(user)
        context["conversion"] = DashboardService.get_conversion_metrics(user)
        context["forecast"] = DashboardService.get_forecast_metrics(user)
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(user)
        context["urgent_followups"] = DashboardService.get_urgent_followups(user)
        context["today"] = timezone.now().date()

        return context


class MonthlySummaryView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/monthly_summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        today = date.today()
        period = self.request.GET.get("period", "quarterly")
        year = int(self.request.GET.get("year", today.year))

        default_quarter = (today.month - 1) // 3 + 1
        default_half = 1 if today.month <= 6 else 2

        month = int(self.request.GET.get("month", today.month))
        quarter = int(self.request.GET.get("quarter", default_quarter))
        half = int(self.request.GET.get("half", default_half))

        if period == "monthly":
            start_date = date(year, month, 1)
            end_date = _add_months(year, month, 1)
            period_label = f"{calendar.month_name[month]} {year}"
        elif period == "quarterly":
            start_month = (quarter - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            end_date = _add_months(year, start_month, 3)
            period_label = f"Q{quarter} {year}"
        elif period == "semi-annual":
            start_month = 1 if half == 1 else 7
            start_date = date(year, start_month, 1)
            end_date = _add_months(year, start_month, 6)
            period_label = f"H{half} {year}"
        else:  # "annual"
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 1, 1)
            period_label = str(year)

        summary = MonthlySummaryGenerator.generate(
            user, start_date, end_date, period_label
        )
        chart = DashboardService.get_earnings_chart(
            user, months=6, anchor_date=end_date - timedelta(days=1)
        )

        context["summary"] = summary
        context["year"] = year
        context["period"] = period
        context["month"] = month
        context["quarter"] = quarter
        context["half"] = half
        context["month_choices"] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        context["year_choices"] = list(range(today.year, today.year - 5, -1))
        context["chart_labels"] = json.dumps(chart["labels"])
        context["chart_data"] = json.dumps(chart["data"])
        context["platform_conversion"] = DashboardService.get_platform_conversion(
            user, start_date, end_date
        )
        context["platform_stats"] = DashboardService.get_platform_stats(
            user, start_date, end_date
        )
        context["hourly_rate"] = DashboardService.get_hourly_rate_metrics(
            user
        ).hourly_rate

        return context
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_dashboard.py::TestMonthlySummaryViewPeriodFilter -v --no-cov
```

Expected: all PASS.

- [ ] **Step 5: Run full dashboard test suite to catch regressions**

```bash
uv run pytest tests/test_dashboard.py -v --no-cov
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add apps/dashboard/views.py tests/test_dashboard.py
git commit -m "feat(analytics): replace 30/90/year periods with monthly/quarterly/semi-annual/annual"
```

---

## Task 4: Monthly Summary template — updated period selector

**Files:**
- Modify: `templates/dashboard/monthly_summary.html`

- [ ] **Step 1: Replace the Filter Bar block**

In `templates/dashboard/monthly_summary.html`, replace the entire `<!-- Filter Bar -->` block (lines 24–41) with:

```html
<!-- Filter Bar -->
<form method="get" class="mb-stack-md flex flex-col sm:flex-row gap-4 items-end bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-xs">
    <div class="flex flex-col gap-1 flex-1">
        <label for="period" class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Period" %}</label>
        <div class="relative">
            <select name="period" id="period" class="w-full appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="monthly" {% if period == "monthly" %}selected{% endif %}>{% trans "Monthly" %}</option>
                <option value="quarterly" {% if period == "quarterly" or not period %}selected{% endif %}>{% trans "Quarterly" %}</option>
                <option value="semi-annual" {% if period == "semi-annual" %}selected{% endif %}>{% trans "Semi-annual" %}</option>
                <option value="annual" {% if period == "annual" %}selected{% endif %}>{% trans "Annual" %}</option>
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
    </div>

    <div class="flex flex-col gap-1">
        <label for="year" class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Year" %}</label>
        <div class="relative">
            <select name="year" id="year" class="appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                {% for y in year_choices %}
                <option value="{{ y }}" {% if year == y %}selected{% endif %}>{{ y }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
    </div>

    <div class="flex flex-col gap-1" id="month-wrapper" style="display:none">
        <label for="month-select" class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Month" %}</label>
        <div class="relative">
            <select name="month" id="month-select" class="appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                {% for num,name in month_choices %}
                <option value="{{ num }}" {% if month == num %}selected{% endif %}>{{ name }}</option>
                {% endfor %}
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
    </div>

    <div class="flex flex-col gap-1" id="quarter-wrapper" style="display:none">
        <label for="quarter-select" class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Quarter" %}</label>
        <div class="relative">
            <select name="quarter" id="quarter-select" class="appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="1" {% if quarter == 1 %}selected{% endif %}>Q1 ({% trans "Jan–Mar" %})</option>
                <option value="2" {% if quarter == 2 %}selected{% endif %}>Q2 ({% trans "Apr–Jun" %})</option>
                <option value="3" {% if quarter == 3 %}selected{% endif %}>Q3 ({% trans "Jul–Sep" %})</option>
                <option value="4" {% if quarter == 4 %}selected{% endif %}>Q4 ({% trans "Oct–Dec" %})</option>
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
    </div>

    <div class="flex flex-col gap-1" id="half-wrapper" style="display:none">
        <label for="half-select" class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">{% trans "Half" %}</label>
        <div class="relative">
            <select name="half" id="half-select" class="appearance-none bg-surface border border-outline-variant rounded-lg py-2 pl-4 pr-10 font-body-sm text-body-sm text-on-surface focus:outline-hidden focus:ring-2 focus:ring-primary cursor-pointer">
                <option value="1" {% if half == 1 %}selected{% endif %}>H1 ({% trans "Jan–Jun" %})</option>
                <option value="2" {% if half == 2 %}selected{% endif %}>H2 ({% trans "Jul–Dec" %})</option>
            </select>
            <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">arrow_drop_down</span>
        </div>
    </div>

    <button type="submit" class="bg-primary text-on-primary px-5 py-2 rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors shadow-xs">{% trans "View" %}</button>
</form>
```

- [ ] **Step 2: Replace the JS block**

In `templates/dashboard/monthly_summary.html`, replace the `<script>` block inside `{% block extra_js %}` (the inline script after `charts.js`) with:

```html
<script>
(function () {
    var periodSelect = document.getElementById("period");
    var monthWrapper = document.getElementById("month-wrapper");
    var quarterWrapper = document.getElementById("quarter-wrapper");
    var halfWrapper = document.getElementById("half-wrapper");

    function syncSecondary() {
        var v = periodSelect.value;
        monthWrapper.style.display = v === "monthly" ? "" : "none";
        quarterWrapper.style.display = v === "quarterly" ? "" : "none";
        halfWrapper.style.display = v === "semi-annual" ? "" : "none";
    }

    periodSelect.addEventListener("change", syncSecondary);
    syncSecondary();
})();
</script>
```

- [ ] **Step 3: Start dev server and test the UI**

```bash
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/analytics/ and verify:
- Period select shows Monthly / Quarterly / Semi-annual / Annual
- Selecting "Monthly" shows the Month selector, hides Quarter and Half
- Selecting "Quarterly" shows Q1–Q4, hides Month and Half
- Selecting "Semi-annual" shows H1/H2, hides Month and Quarter
- Selecting "Annual" hides all secondary selectors
- Year select always visible with last 5 years
- Submitting each combination loads data and shows correct `period_label` in KPI card

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest --no-cov
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard/monthly_summary.html
git commit -m "feat(analytics): update period selector UI with monthly/quarterly/semi-annual/annual"
```

---

## Final Check

- [ ] **Run linter and type checker**

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy apps config
```

Fix any issues before proceeding.

- [ ] **Run full test suite with coverage**

```bash
uv run pytest --cov --cov-fail-under=75
```

Expected: all pass, coverage ≥ 75%.

- [ ] **Run icon check**

```bash
python bin/check-icons.py
```

Expected: no missing icons.
