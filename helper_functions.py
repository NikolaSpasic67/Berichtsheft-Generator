"""Pure-logic helpers for the Berichtsheft generator.

This module is intentionally free of any terminal I/O (no ``print``,
``input``, ANSI escape codes or keyboard listeners). All user interaction
is the responsibility of the GUI layer; these functions only validate
input, parse strings into typed values and look up data.

Errors are signalled by raising ``ValueError`` so the GUI can display
them to the user.
"""

from __future__ import annotations

import re
from datetime import date, datetime

import holidays


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROVINCES: dict[str, str] = {
    "BB": "Brandenburg",
    "BE": "Berlin",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "HB": "Bremen",
    "HE": "Hessen",
    "HH": "Hamburg",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SH": "Schleswig-Holstein",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "TH": "Thüringen",
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Validation / parsing
# ---------------------------------------------------------------------------

def is_valid_date_string(value: str) -> bool:
    """Return ``True`` if *value* matches ``YYYY-MM-DD`` and is a real date."""
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def parse_date(value: str) -> date:
    """Parse a ``YYYY-MM-DD`` string into a :class:`datetime.date`.

    Raises ``ValueError`` with a human-readable German message if the
    string is malformed or not a real calendar date.
    """
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError(
            f"„{value}“ ist kein gültiges Datum (Format: YYYY-MM-DD)."
        )
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"„{value}“ ist kein gültiges Datum: {exc}.") from exc


def is_valid_province(code: str) -> bool:
    """Return ``True`` if *code* is a known German Bundesland code."""
    return isinstance(code, str) and code.upper() in VALID_PROVINCES


def parse_vacation_periods(text: str) -> list[tuple[date, date]]:
    """Parse a vacation-periods string into typed ``(start, end)`` tuples.

    Expected format (multiple periods separated by ``,``)::

        YYYY-MM-DD bis YYYY-MM-DD, YYYY-MM-DD bis YYYY-MM-DD

    Raises ``ValueError`` on any malformed period; on success returns a
    non-empty list of ``(start, end)`` date tuples.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Keine Eingabe. Bitte mindestens einen Zeitraum angeben.")

    ranges: list[tuple[date, date]] = []

    for raw_period in text.split(","):
        period = raw_period.strip()
        if not period:
            continue

        parts = period.split("bis")
        if len(parts) != 2:
            raise ValueError(
                f"Ungültiges Format: „{period}“. "
                "Erwartet: 'YYYY-MM-DD bis YYYY-MM-DD'."
            )

        start = parse_date(parts[0].strip())
        end = parse_date(parts[1].strip())

        if start > end:
            raise ValueError(
                f"Ungültiger Zeitraum: Startdatum {start} liegt nach Enddatum {end}."
            )

        ranges.append((start, end))

    if not ranges:
        raise ValueError("Keine gültigen Zeiträume erkannt.")

    return ranges


# ---------------------------------------------------------------------------
# Domain lookups
# ---------------------------------------------------------------------------

def get_holidays_in_range(
    start_date: date, end_date: date, state: str = "BW"
) -> list[date]:
    """Return all German public holidays for *state* within the date range."""
    if start_date > end_date:
        raise ValueError(
            f"Startdatum {start_date} liegt nach Enddatum {end_date}."
        )
    if not is_valid_province(state):
        raise ValueError(f"Unbekanntes Bundesland-Kürzel: „{state}“.")

    years = list(range(start_date.year, end_date.year + 1))
    de_holidays = holidays.country_holidays("DE", years=years, subdiv=state.upper())
    return sorted(d for d in de_holidays if start_date <= d <= end_date)


def expand_vacation_dates(
    vacation_periods: list[tuple[date, date]],
) -> set[date]:
    """Expand a list of ``(start, end)`` tuples into a set of individual dates."""
    result: set[date] = set()
    for start, end in vacation_periods:
        current = start
        while current <= end:
            result.add(current)
            current = date.fromordinal(current.toordinal() + 1)
    return result

