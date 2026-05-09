"""Shared utility functions used across apps."""

from datetime import date


def month_range(year: int, month: int) -> tuple[date, date]:
    """Return the half-open ``[start, end)`` interval for a calendar month.

    The end date is the first day of the following month, suitable for
    ORM lookups like ``date__gte=start, date__lt=end``.

    Args:
        year: Four-digit year.
        month: Month number, 1-12.

    Returns:
        Tuple ``(start, end)`` where ``start`` is the first day of the
        given month and ``end`` is the first day of the next month.
    """
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end
