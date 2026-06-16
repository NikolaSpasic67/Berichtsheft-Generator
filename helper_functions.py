import os
import re
from datetime import datetime
import keyboard
import holidays

# --- Layout constants --------------------------------------------------------
WIDTH       = 78          # total visible width of the bordered UI
LABEL_WIDTH = 26          # width reserved for the label column in info rows
_ANSI_RE    = re.compile(r"\033\[[0-9;]*m")


class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    RED     = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE    = "\033[34m"
    GREY    = "\033[90m"


# --- Low-level string helpers (ANSI-aware) ----------------------------------
def _vlen(s: str) -> int:
    """Sichtbare Länge eines Strings (ohne ANSI-Codes)."""
    return len(_ANSI_RE.sub("", s))


def _pad_visible(s: str, width: int, align: str = "left") -> str:
    """Polstert s auf exakt `width` sichtbare Zeichen (ANSI ignorierend)."""
    pad = width - _vlen(s)
    if pad <= 0:
        return s
    if align == "right":
        return " " * pad + s
    if align == "center":
        left = pad // 2
        return " " * left + s + " " * (pad - left)
    return s + " " * pad


def _wrap_plain(text: str, width: int) -> list[str]:
    """Bricht reinen Text in Zeilen ≤ width, bevorzugt an Kommas/Leerzeichen."""
    if width <= 0:
        return [text]
    lines: list[str] = []
    remaining = text
    while len(remaining) > width:
        break_at = -1
        # Suche bevorzugten Umbruchpunkt (Komma > Leerzeichen) im hinteren Drittel
        for i in range(width, max(width - 25, 0), -1):
            if i < len(remaining) and remaining[i] in (",", " "):
                break_at = i + 1
                break
        if break_at <= 0:
            break_at = width
        lines.append(remaining[:break_at].rstrip())
        remaining = remaining[break_at:].lstrip()
    if remaining:
        lines.append(remaining)
    return lines


# --- Box primitives ----------------------------------------------------------
def _border_line(left: str, fill: str, right: str, color: str = C.BLUE) -> str:
    return f"{color}{left}{fill * (WIDTH - 2)}{right}{C.RESET}"


def _row(content: str, color: str = C.BLUE) -> str:
    """Rahmt einen Inhalt zwischen │ … │, polstert auf WIDTH."""
    inner_width = WIDTH - 4  # 2x "│ " / " │"
    padded = _pad_visible(content, inner_width)
    return f"{color}│{C.RESET} {padded} {color}│{C.RESET}"


# --- Public widgets ----------------------------------------------------------
def banner(title: str, subtitle: str = "") -> None:
    print(_border_line("╔", "═", "╗", C.CYAN))
    print(_row("", C.CYAN))
    print(_row(_pad_visible(f"{C.BOLD}{C.CYAN}{title}{C.RESET}", WIDTH - 4, "center"), C.CYAN))
    if subtitle:
        print(_row(_pad_visible(f"{C.DIM}{subtitle}{C.RESET}", WIDTH - 4, "center"), C.CYAN))
    print(_row("", C.CYAN))
    print(_border_line("╚", "═", "╝", C.CYAN))


def section(title: str) -> None:
    """Öffnet einen Abschnitt mit ┌─ Titel ─…─┐ (Gesamtbreite = WIDTH)."""
    title_vlen = _vlen(title)
    # Aufbau: ┌─␣title␣── … ──┐  →  1 + 1 + 1 + title + 1 + dashes + 1 = WIDTH
    dash_count = WIDTH - 5 - title_vlen
    if dash_count < 2:
        dash_count = 2
    print(f"\n{C.BLUE}┌─ {C.BOLD}{title}{C.RESET}{C.BLUE} {'─' * dash_count}┐{C.RESET}")


def section_end() -> None:
    print(_border_line("└", "─", "┘", C.BLUE))


def divider() -> None:
    """Dünner Trenner innerhalb eines Abschnitts (├─ … ─┤)."""
    print(_border_line("├", "─", "┤", C.BLUE))


def blank_row() -> None:
    """Leere bordered Zeile."""
    print(_row(""))


def info(label: str, value: str, color: str = C.GREEN) -> None:
    """Bordered Schlüssel/Wert-Zeile; lange Werte werden umgebrochen."""
    inner_width = WIDTH - 4
    value_width = inner_width - LABEL_WIDTH - 1  # 1 = Trenner-Leerzeichen

    plain = str(value)
    chunks = _wrap_plain(plain, value_width) if plain else [""]

    # erste Zeile: Label + erstes Stück des Werts
    label_cell = f"{C.DIM}{_pad_visible(label, LABEL_WIDTH)}{C.RESET}"
    value_cell = _pad_visible(f"{color}{chunks[0]}{C.RESET}", value_width)
    print(_row(f"{label_cell} {value_cell}"))

    # Folgezeilen: Label-Spalte leer
    for chunk in chunks[1:]:
        label_cell = " " * LABEL_WIDTH
        value_cell = _pad_visible(f"{color}{chunk}{C.RESET}", value_width)
        print(_row(f"{label_cell} {value_cell}"))


def subheader(text: str) -> None:
    """Kompakter Abschnittstitel ohne Box, mit Pfeil-Akzent."""
    print(f"\n{C.BOLD}{C.CYAN}▶ {text}{C.RESET}")
    print(f"{C.DIM}{'─' * WIDTH}{C.RESET}")


def report_row(index: int, week: int, year: int, week_start, week_end, file_basename: str) -> None:
    """Einheitliche Statuszeile pro generiertem Bericht."""
    print(
        f"  {C.GREEN}✔{C.RESET} "
        f"{C.BOLD}Nr. {index:>4}{C.RESET}  "
        f"{C.DIM}│{C.RESET} KW {C.CYAN}{int(week):02d}/{int(year)}{C.RESET}  "
        f"{C.DIM}│{C.RESET} {week_start.strftime('%d.%m.%Y')} {C.DIM}–{C.RESET} {week_end.strftime('%d.%m.%Y')}  "
        f"{C.DIM}→{C.RESET} {file_basename}"
    )


def success(msg: str) -> None:
    print(f"  {C.GREEN}✔{C.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {C.YELLOW}⚠{C.RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {C.RED}✖{C.RESET} {msg}")


def ask(idx: int, prompt: str) -> str:
    # Einheitlich gepolstertes Prompt-Label, damit alle Eingaben in einer Spalte stehen.
    label = f"[{idx:>2}]"
    return input(
        f"  {C.CYAN}{label}{C.RESET}  {prompt:<46}{C.DIM}›{C.RESET} "
    ).strip()


def ask_int(idx: int, prompt: str) -> int:
    """Fragt nach einer ganzen Zahl und wiederholt bei Fehleingabe."""
    while True:
        raw = ask(idx, prompt)
        try:
            return int(raw)
        except ValueError:
            err(f"„{raw}“ ist keine gültige ganze Zahl. Bitte erneut eingeben.")


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def ask_date(idx: int, prompt: str) -> str:
    """Fragt nach einem Datum im Format YYYY-MM-DD und wiederholt bei Fehleingabe."""
    while True:
        raw = ask(idx, prompt)
        if not _DATE_RE.match(raw):
            err(f"„{raw}“ ist kein gültiges Datum (Format: YYYY-MM-DD, genau 4-2-2 Ziffern). Bitte erneut eingeben.")
            continue
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError as exc:
            err(f"„{raw}“ ist kein gültiges Datum: {exc}. Bitte erneut eingeben.")

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')
    return

def ask_confirm() -> bool:
    """Wartet auf ENTER (True) oder ESC (False). Ignoriert Key-Release-Events."""
    print()
    print(
        f"  {C.DIM}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{C.RESET}"
    )
    print(
        f"  {C.BOLD}{C.GREEN}ENTER{C.RESET} {C.DIM}bestätigen{C.RESET}"
        f"   {C.DIM}·{C.RESET}   "
        f"{C.BOLD}{C.RED}ESC{C.RESET} {C.DIM}abbrechen{C.RESET}"
    )
    print(
        f"  {C.DIM}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{C.RESET}"
    )
    while True:
        event = keyboard.read_event()
        if event.event_type != keyboard.KEY_DOWN:
            continue
        if event.name == 'enter':
            return True
        if event.name == 'esc':
            return False
        

def get_user_input() -> tuple[str, str, str, int, str, str, str]:
    """
    Fragt alle benötigten Informationen vom Nutzer ab, mit Validierung und Wiederholung bei Fehlern.
    Gibt die gesammelten Informationen als Tuple zurück.
    """
    
    banner("BERICHTSHEFT-GENERATOR", "Berichtsheft Dateien automatisch erstellen")
    section("Eingaben")

    global province
    global vacation_periods_list
    province = "BW"  # Standardwert, falls Feiertage nicht berücksichtigt werden
    vacation_periods_list = []

    file_name            = ask(1, "Dateiname der Berichtshefte")
    full_name            = ask(2, "Vollständiger Name")
    current_department   = ask(3, "Abteilung (z.B. IT, HR, …)")
    current_report_index = ask_int(4, "Start Nachweis-Nr. des 1. Berichts")
    start_date           = ask_date(5, "Startdatum (YYYY-MM-DD)")
    end_date             = ask_date(6, "Enddatum   (YYYY-MM-DD)")
    calculate_holidays   = ask_calculate_holidays()
    if calculate_holidays:
        province = ask_province()
    calculate_vacation = ask_calculate_vacation()
    if calculate_vacation:
        vacation_periods_list = calculate_vacation
        
    section_end()
    success("Eingaben erfolgreich übernommen.")

    return file_name, full_name, current_department, current_report_index, start_date, end_date, calculate_holidays, province, vacation_periods_list, calculate_vacation



def get_holidays_in_range(start_date: str, end_date: str, state = "BW") -> list[str]:
    """Gibt eine Liste von Feiertagen im Format YYYY-MM-DD zurück, die im angegebenen Zeitraum liegen."""
    de_holidays = holidays.country_holidays("DE", state=state)

def ask_province():
    valid_provinces = {
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

    while True:
        province_input = ask(
            8, "Bundesland (z.B. BW, BY, BE – 'ALL' für Liste)"
        ).upper()

        if province_input == "ALL":
            _print_province_table(valid_provinces)
            continue
        elif province_input in valid_provinces:
            success(
                f"Bundesland gewählt: {C.BOLD}{valid_provinces[province_input]}"
                f"{C.RESET} ({province_input})"
            )
            return province_input
        else:
            err(
                f"„{province_input}“ ist kein gültiges Bundesland. "
                f"Tippe {C.BOLD}ALL{C.RESET} für eine Übersicht."
            )


def _print_province_table(provinces: dict[str, str]) -> None:
    """Druckt eine hübsch formatierte Tabelle aller Bundesländer und deren Codes."""
    clear_console()
    title = "Bundesländer & Codes"
    name_width = max(len(name) for name in provinces.values())
    code_width = max(len(code) for code in provinces)
    # Innenbreite: "  CODE  │  NAME  "
    inner = 2 + code_width + 2 + 1 + 2 + name_width + 2
    inner = max(inner, len(title) + 4)

    top    = f"{C.CYAN}┌{'─' * inner}┐{C.RESET}"
    sep    = f"{C.CYAN}├{'─' * inner}┤{C.RESET}"
    bottom = f"{C.CYAN}└{'─' * inner}┘{C.RESET}"

    def row(left: str, right: str, *, header: bool = False) -> str:
        left_styled  = f"{C.BOLD}{left}{C.RESET}" if header else f"{C.YELLOW}{left}{C.RESET}"
        right_styled = f"{C.BOLD}{right}{C.RESET}" if header else f"{C.GREEN}{right}{C.RESET}"
        content = f"  {left:<{code_width}}  {C.CYAN}│{C.RESET}  {right:<{name_width}}  "
        # Mit Styling neu aufbauen (Padding über sichtbare Länge)
        styled = (
            f"  {left_styled}{' ' * (code_width - len(left))}  "
            f"{C.CYAN}│{C.RESET}  "
            f"{right_styled}{' ' * (name_width - len(right))}  "
        )
        # Auffüllen, falls inner > content
        pad = inner - _vlen(styled)
        if pad > 0:
            styled += " " * pad
        return f"{C.CYAN}│{C.RESET}{styled}{C.CYAN}│{C.RESET}"

    title_pad = inner - len(title)
    left_pad = title_pad // 2
    right_pad = title_pad - left_pad
    title_line = (
        f"{C.CYAN}│{C.RESET}"
        + " " * left_pad
        + f"{C.BOLD}{C.MAGENTA}{title}{C.RESET}"
        + " " * right_pad
        + f"{C.CYAN}│{C.RESET}"
    )

    print()
    print(top)
    print(title_line)
    print(sep)
    print(row("Code", "Bundesland", header=True))
    print(sep)
    for code, name in sorted(provinces.items()):
        print(row(code, name))
    print(bottom)
    print()

def ask_calculate_holidays() -> bool:
    while True:
        answer = ask(7, "Feiertage automatisch berücksichtigen? (j/n)").lower()
        if answer == "j":
            return True
        if answer == "n":
            return False
        err("Ungültige Eingabe. Bitte 'j' für Ja oder 'n' für Nein eingeben.")


def ask_calculate_vacation():
    while True:
        answer = ask(9, "Urlaubstage automatisch berücksichtigen? (j/n)").lower()
        if answer == "n":
            return False
        if answer != "j":
            err("Ungültige Eingabe. Bitte 'j' für Ja oder 'n' für Nein eingeben.")
            continue

        # Zeiträume abfragen und vollständig validieren. Bei *irgendeinem* Fehler
        # wird die komplette Eingabe verworfen und erneut abgefragt, damit nichts
        # stillschweigend weggelassen wird.
        while True:
            vacation_period = ask(
                10, "Urlaubszeiträume (YYYY-MM-DD bis YYYY-MM-DD, mehrere mit ,)"
            )
            if not vacation_period.strip():
                err("Keine Eingabe. Bitte mindestens einen Zeitraum angeben.")
                continue

            vacation_ranges = []
            had_error = False

            for raw_period in vacation_period.split(","):
                period = raw_period.strip()
                if not period:
                    continue

                # Trenner "bis" muss genau einmal vorkommen
                parts = period.split("bis")
                if len(parts) != 2:
                    err(f"Ungültiges Format: „{period}“. Erwartet: 'YYYY-MM-DD bis YYYY-MM-DD'.")
                    had_error = True
                    break

                start_str, end_str = parts[0].strip(), parts[1].strip()

                if not _DATE_RE.match(start_str):
                    err(f"Ungültiges Startdatum: „{start_str}“. Erwartet: YYYY-MM-DD (genau 4-2-2 Ziffern).")
                    had_error = True
                    break
                if not _DATE_RE.match(end_str):
                    err(f"Ungültiges Enddatum: „{end_str}“. Erwartet: YYYY-MM-DD (genau 4-2-2 Ziffern).")
                    had_error = True
                    break

                try:
                    start = datetime.strptime(start_str, "%Y-%m-%d").date()
                    end = datetime.strptime(end_str, "%Y-%m-%d").date()
                except ValueError as exc:
                    err(f"Ungültiges Datum in „{period}“: {exc}.")
                    had_error = True
                    break

                if start > end:
                    err(f"Ungültiger Zeitraum: Startdatum {start} liegt nach Enddatum {end}.")
                    had_error = True
                    break

                vacation_ranges.append([(start, end)])

            if had_error:
                err("Bitte alle Zeiträume erneut eingeben.")
                continue
            if not vacation_ranges:
                err("Keine gültigen Zeiträume erkannt. Bitte erneut eingeben.")
                continue

            return vacation_ranges
