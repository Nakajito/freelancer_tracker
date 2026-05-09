Architecture
============

PropoTrack follows the Django patterns laid out in
``AGENTS.md``: bounded-context apps under ``apps/``, a service layer for
multi-model logic, custom QuerySets for chainable filtering, and shared
abstractions in ``apps.core``.

Apps
----

* ``apps.core`` — abstract base models, mixins, form helpers, utilities.
* ``apps.accounts`` — custom ``User`` and allauth adapters.
* ``apps.proposals`` — proposals, clients, tags, status engine.
* ``apps.followups`` — follow-up tracking and auto-suggest service.
* ``apps.timetracking`` — time entries and recurring retainers.
* ``apps.templates_app`` — proposal templates with placeholder rendering.
* ``apps.dashboard`` — read-only metric services and views.
* ``apps.exports`` — CSV/JSON exports and monthly summaries.

Shared abstractions
-------------------

* ``apps.core.mixins`` — ``OwnerQuerysetMixin`` and
  ``ProposalOwnerQuerysetMixin`` for per-user CBV scoping.
* ``apps.core.forms`` — ``date_input_widget()`` factory.
* ``apps.core.utils`` — ``month_range`` helper.
