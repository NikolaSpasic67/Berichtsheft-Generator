import os
import re
from datetime import datetime
import keyboard
import holidays

WIDTH = 64
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


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

def _vlen(s: str) -> int:
    """Sichtbare Länge eines Strings (ohne ANSI-Codes)."""
    return len(_ANSI_RE.sub("", s))


def banner(title: str, subtitle: str = "") -> None:
    top    = "╔" + "═" * (WIDTH - 2) + "╗"
    bottom = "╚" + "═" * (WIDTH - 2) + "╝"

    def centered(text: str) -> str:
        pad = WIDTH - 2 - _vlen(text)
        left = pad // 2
        right = pad - left
        return f"{C.CYAN}║{C.RESET}" + " " * left + text + " " * right + f"{C.CYAN}║{C.RESET}"

    empty = f"{C.CYAN}║{C.RESET}" + " " * (WIDTH - 2) + f"{C.CYAN}║{C.RESET}"

    print(f"{C.CYAN}{top}{C.RESET}")
    print(empty)
    print(centered(f"{C.BOLD}{C.CYAN}{title}{C.RESET}"))
    if subtitle:
        print(centered(f"{C.DIM}{subtitle}{C.RESET}"))
    print(empty)
    print(f"{C.CYAN}{bottom}{C.RESET}")


def section(title: str) -> None:
    dash_count = WIDTH - 4 - len(title)
    if dash_count < 2:
        dash_count = 2
    print(f"\n{C.BLUE}┌─ {C.BOLD}{title}{C.RESET} {C.BLUE}{'─' * dash_count}┐{C.RESET}")


def section_end() -> None:
    print(f"{C.BLUE}└{'─' * (WIDTH - 2)}┘{C.RESET}")


def info(label: str, value: str, color: str = C.GREEN) -> None:
    print(f"{C.BLUE}│{C.RESET} {C.DIM}{label:<22}{C.RESET} {color}{value}{C.RESET}")


def success(msg: str) -> None:
    print(f"  {C.GREEN}✔{C.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {C.YELLOW}⚠{C.RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {C.RED}✖{C.RESET} {msg}")


def ask(idx: int, prompt: str) -> str:
    return input(f"  {C.CYAN}[{idx}]{C.RESET} {prompt}{C.DIM} › {C.RESET}").strip()


def ask_int(idx: int, prompt: str) -> int:
    """Fragt nach einer ganzen Zahl und wiederholt bei Fehleingabe."""
    while True:
        raw = ask(idx, prompt)
        try:
            return int(raw)
        except ValueError:
            err(f"„{raw}“ ist keine gültige ganze Zahl. Bitte erneut eingeben.")


def ask_date(idx: int, prompt: str) -> str:
    """Fragt nach einem Datum im Format YYYY-MM-DD und wiederholt bei Fehleingabe."""
    while True:
        raw = ask(idx, prompt)
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            err(f"„{raw}“ ist kein gültiges Datum (Format: YYYY-MM-DD). Bitte erneut eingeben.")

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')
    return

def ask_confirm() -> bool:
    """Wartet auf ENTER (True) oder ESC (False). Ignoriert Key-Release-Events."""
    print("\n Drücke ENTER um zu bestätigen, oder ESC um abzubrechen.")
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

    file_name = ask(1, "Dateiname der Berichtshefte       ")
    full_name = ask(2, "Vollständiger Name     ")
    current_department = ask(3, "Abteilung (z.B. IT, HR, …):     ")
    current_report_index = ask_int(4, "Start Nachweis-Nr. des 1. Berichts")
    start_date = ask_date(5, "Startdatum (YYYY-MM-DD)           ")
    end_date   = ask_date(6, "Enddatum   (YYYY-MM-DD)           ")
    calculate_holidays = ask(7, "Feiertage automatisch berücksichtigen? (j/n) ").lower() == "j"
    if calculate_holidays == "j" or "J":
        province = ask_province()

    section_end()
    success("Eingaben erfolgreich übernommen.")

    return file_name, full_name, current_department, current_report_index, start_date, end_date, province



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
            8,
            "Bundesland für Feiertage (z.B. BW, BY, BE, Alle anzeigen mit 'ALL')",
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
