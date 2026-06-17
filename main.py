"""Pure-logic report generator for Berichtsheft PDFs.

This module contains no terminal I/O. It exposes a single high-level
entry point :func:`generate_reports` that takes a :class:`ReportConfig`
and produces PDF files plus a :class:`ReportResult` summary. A tkinter
(or any other) GUI can call it directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

import holidays
import pandas as pd
from pypdf import PdfReader, PdfWriter

from helper_functions import expand_vacation_dates


# ---------------------------------------------------------------------------
# Defaults (can be overridden via ReportConfig)
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE_PATH = (
    r"C:\Users\PVV1FE\Documents\Projects\Python\Berichtsheft-Generator"
    r"\bheft_template.pdf"
)
DEFAULT_OUTPUT_DIR = (
    r"C:\Users\PVV1FE\Documents\Projects\Python\Berichtsheft-Generator"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReportConfig:
    """All inputs required to generate a batch of weekly reports."""

    full_name: str
    current_department: str
    start_report_index: int
    start_date: date
    end_date: date

    file_name: str = "Berichtsheft"
    template_path: str = DEFAULT_TEMPLATE_PATH
    output_dir: str = DEFAULT_OUTPUT_DIR

    calculate_holidays: bool = False
    province: str = "BW"

    calculate_vacation: bool = False
    vacation_periods: list[tuple[date, date]] = field(default_factory=list)


@dataclass
class GeneratedReport:
    """Information about a single successfully generated report file."""

    index: int
    week: int
    year: int
    week_start: date
    week_end: date
    file_path: str


@dataclass
class SkippedWeek:
    """A week that was skipped during generation, with a reason."""

    week: int
    year: int
    reason: str


@dataclass
class ReportResult:
    """Aggregated outcome of a :func:`generate_reports` run."""

    generated_reports: list[GeneratedReport] = field(default_factory=list)
    skipped_weeks: list[SkippedWeek] = field(default_factory=list)
    next_report_index: int = 0

    @property
    def generated_count(self) -> int:
        return len(self.generated_reports)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_weeks)


# Optional callback signature: called once per processed week.
# Args: (current_week_number_1based, total_weeks, message)
ProgressCallback = Callable[[int, int, str], None]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def generate_reports(
    config: ReportConfig,
    progress_callback: Optional[ProgressCallback] = None,
) -> ReportResult:
    """Generate one PDF per complete work week in the configured range.

    Parameters
    ----------
    config:
        Fully populated :class:`ReportConfig`.
    progress_callback:
        Optional callable invoked after each week is processed (whether
        generated or skipped). Useful for driving a GUI progress bar.

    Returns
    -------
    ReportResult
        Summary of generated files, skipped weeks and the next free
        report index after the run.
    """
    _validate_config(config)

    workdays = pd.bdate_range(start=config.start_date, end=config.end_date)
    df = pd.DataFrame({"date": workdays})
    df["week"] = df["date"].dt.isocalendar().week
    df["year"] = df["date"].dt.isocalendar().year

    vacation_dates: set[date] = (
        expand_vacation_dates(config.vacation_periods)
        if config.calculate_vacation
        else set()
    )

    grouped = list(df.groupby(["year", "week"]))
    total_weeks = len(grouped)

    result = ReportResult(next_report_index=config.start_report_index)
    current_index = config.start_report_index

    for step, ((year, week), group) in enumerate(grouped, start=1):
        week_start = group["date"].min().date()
        week_end = group["date"].max().date()
        days_in_week = (week_end - week_start).days + 1

        if days_in_week < 5:
            skipped = SkippedWeek(
                week=int(week),
                year=int(year),
                reason="keine vollständige Woche",
            )
            result.skipped_weeks.append(skipped)
            if progress_callback is not None:
                progress_callback(
                    step,
                    total_weeks,
                    f"KW {int(week):02d}/{int(year)} übersprungen "
                    f"({skipped.reason})",
                )
            continue

        week_holidays: set[date] = set()
        if config.calculate_holidays:
            week_holidays = set(
                holidays.country_holidays(
                    "DE", years=[int(year)], subdiv=config.province
                )
            )

        all_week_dates = pd.date_range(start=week_start, end=week_end)
        manipulated_days_texts = ["" for _ in range(5)]
        for i, single_date in enumerate(all_week_dates[:5]):
            single_date_only = single_date.date()
            if config.calculate_holidays and single_date_only in week_holidays:
                manipulated_days_texts[i] = "(Feiertag)"
            elif config.calculate_vacation and single_date_only in vacation_dates:
                manipulated_days_texts[i] = "(Urlaub)"

        output_path = os.path.join(
            config.output_dir, f"{config.file_name}_{current_index}.pdf"
        )
        _write_pdf(
            template_path=config.template_path,
            output_path=output_path,
            full_name=config.full_name,
            department=config.current_department,
            report_index=current_index,
            week_start=week_start,
            week_end=week_end,
            manipulated_days_texts=manipulated_days_texts,
        )

        report = GeneratedReport(
            index=current_index,
            week=int(week),
            year=int(year),
            week_start=week_start,
            week_end=week_end,
            file_path=output_path,
        )
        result.generated_reports.append(report)

        if progress_callback is not None:
            progress_callback(
                step,
                total_weeks,
                f"KW {int(week):02d}/{int(year)} → {os.path.basename(output_path)}",
            )

        current_index += 1

    result.next_report_index = current_index
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_config(config: ReportConfig) -> None:
    """Raise ``ValueError`` / ``FileNotFoundError`` for invalid inputs."""
    if not os.path.isfile(config.template_path):
        raise FileNotFoundError(
            f"Template-Datei nicht gefunden: {config.template_path}"
        )
    if not os.path.isdir(config.output_dir):
        raise FileNotFoundError(
            f"Ausgabeverzeichnis existiert nicht: {config.output_dir}"
        )
    if config.start_date > config.end_date:
        raise ValueError(
            f"Startdatum {config.start_date} liegt nach Enddatum {config.end_date}."
        )
    if not config.full_name.strip():
        raise ValueError("Vollständiger Name darf nicht leer sein.")
    if not config.file_name.strip():
        raise ValueError("Dateiname darf nicht leer sein.")
    if not config.current_department.strip():
        raise ValueError("Abteilung darf nicht leer sein.")
    if config.start_report_index < 0:
        raise ValueError("Start-Nachweis-Nr. darf nicht negativ sein.")


def _write_pdf(
    *,
    template_path: str,
    output_path: str,
    full_name: str,
    department: str,
    report_index: int,
    week_start: date,
    week_end: date,
    manipulated_days_texts: list[str],
) -> None:
    """Fill in the PDF form template for one week and write the result."""
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    writer.set_need_appearances_writer(True)

    writer.update_page_form_field_values(
        writer.pages[0],
        {
            "Date1_af_date": week_start.strftime("%d.%m.%Y"),
            "Date2_af_date": week_end.strftime("%d.%m.%Y"),
            "Date5_af_date": week_end.strftime("%d.%m.%Y"),
            "Text3": str(full_name),
            "Text4": str(report_index),
            "Text12": str(department),
            "Text6": (
                f"Montag: {manipulated_days_texts[0]}\n\n"
                f"Dienstag: {manipulated_days_texts[1]}\n\n"
                f"Mittwoch: {manipulated_days_texts[2]}\n\n"
                f"Donnerstag: {manipulated_days_texts[3]}\n\n"
                f"Freitag: {manipulated_days_texts[4]}"
            ),
        },
    )

    with open(output_path, "wb") as file:
        writer.write(file)

