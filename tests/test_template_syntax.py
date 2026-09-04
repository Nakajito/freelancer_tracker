"""Guard against a real Django gotcha: {# ... #} cannot span multiple lines.

Confirmed against the installed Django's own tokenizer, not assumed:

    >>> import django.template.base as b
    >>> b.tag_re.pattern
    '({%.*?%}|{{.*?}}|{#.*?#})'
    >>> bool(b.tag_re.flags & re.DOTALL)
    False

Because `.` does not match a newline here, a `{#` that isn't closed by `#}`
before the next line break is never recognized as a comment tag at all -- it
falls through as literal text and gets rendered straight into every page that
extends the template, verbatim, including the developer-facing wording inside
it. This exact bug shipped to production in templates/base.html: the comment
sat directly above <body>, so it appeared at the top of every single page.

`{% comment %}...{% endcomment %}` is the correct choice for anything that
needs more than one line.
"""

import re
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
HTML_FILES = sorted(TEMPLATES_DIR.rglob("*.html"))


def _multiline_comment_spans(text: str) -> list[int]:
    """Return 1-indexed line numbers of any {# #} that crosses a newline."""
    offenders = []
    for match in re.finditer(r"\{#", text):
        start = match.start()
        close = text.find("#}", start)
        newline = text.find("\n", start)
        if close == -1 or (newline != -1 and newline < close):
            offenders.append(text.count("\n", 0, start) + 1)
    return offenders


@pytest.mark.parametrize("path", HTML_FILES, ids=lambda p: p.name)
def test_no_multiline_django_comments(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    offenders = _multiline_comment_spans(text)
    assert not offenders, (
        f"{path}: {{# #}} comment spans a newline at line(s) {offenders} -- "
        "Django's tokenizer cannot match it, so it renders as literal text "
        "on every page using this template. Put it on one line or use "
        "{% comment %}...{% endcomment %}."
    )


def test_detector_catches_a_known_bad_case() -> None:
    """Control: the detector above must actually fire on the shape of bug
    that shipped, not just always report a clean scan."""
    bad = "before\n{# spans\nmultiple lines #}\nafter\n"
    assert _multiline_comment_spans(bad) == [2]


def test_detector_allows_single_line_comments() -> None:
    good = "before\n{# a single line comment #}\nafter\n"
    assert _multiline_comment_spans(good) == []
