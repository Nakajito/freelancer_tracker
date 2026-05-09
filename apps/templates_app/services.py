"""Proposal-template placeholder rendering."""

import re
from datetime import date
from string import Template
from typing import Dict


class PlaceholderRenderer:
    """Renders ``ProposalTemplate`` bodies by substituting ``${key}`` placeholders."""

    AVAILABLE_PLACEHOLDERS = {
        "client": "Client name",
        "project": "Project title",
        "amount": "Proposal amount",
        "date": "Current date",
    }

    PLACEHOLDER_PATTERN = re.compile(r"\$\{(\w+)\}")

    @classmethod
    def render(cls, template_body: str, context: Dict[str, str]) -> str:
        """Substitute ``${key}`` placeholders using ``string.Template.safe_substitute``.

        Unknown keys are left as-is (not raised as errors).

        Args:
            template_body: Raw template text containing ``${key}`` tokens.
            context: Mapping of placeholder names to substitution values.

        Returns:
            Rendered string with known placeholders replaced.
        """
        template = Template(template_body)
        return template.safe_substitute(context)

    @classmethod
    def extract_placeholders(cls, template_body: str) -> list[str]:
        """Return unique placeholder names found in ``template_body``.

        Args:
            template_body: Raw template text to scan.

        Returns:
            De-duplicated list of placeholder key strings (e.g. ``["client", "amount"]``).
        """
        return list(set(cls.PLACEHOLDER_PATTERN.findall(template_body)))

    @classmethod
    def build_context(
        cls,
        client_name: str,
        project_title: str,
        amount: str,
        proposal_date: str = None,
    ) -> Dict[str, str]:
        """Assemble the standard substitution context dict.

        Args:
            client_name: Value for the ``${client}`` placeholder.
            project_title: Value for the ``${project}`` placeholder.
            amount: Value for the ``${amount}`` placeholder.
            proposal_date: Value for the ``${date}`` placeholder. Defaults to today.

        Returns:
            Dict ready to pass directly to ``render``.
        """
        return {
            "client": client_name,
            "project": project_title,
            "amount": amount,
            "date": proposal_date or str(date.today()),
        }
