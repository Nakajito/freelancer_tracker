import re
from string import Template
from typing import Dict


class PlaceholderRenderer:
    AVAILABLE_PLACEHOLDERS = {
        "client": "Client name",
        "project": "Project title",
        "amount": "Proposal amount",
        "date": "Current date",
    }

    PLACEHOLDER_PATTERN = re.compile(r"\$\{(\w+)\}")

    @classmethod
    def render(cls, template_body: str, context: Dict[str, str]) -> str:
        template = Template(template_body)
        return template.safe_substitute(context)

    @classmethod
    def extract_placeholders(cls, template_body: str) -> list[str]:
        return list(set(cls.PLACEHOLDER_PATTERN.findall(template_body)))

    @classmethod
    def build_context(
        cls,
        client_name: str,
        project_title: str,
        amount: str,
        proposal_date: str = None,
    ):
        from datetime import date

        return {
            "client": client_name,
            "project": project_title,
            "amount": amount,
            "date": proposal_date or str(date.today()),
        }
