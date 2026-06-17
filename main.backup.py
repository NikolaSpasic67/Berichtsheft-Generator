import json
import os
import pandas as pd
from pypdf import PdfReader
from pypdf import PdfWriter
from datetime import datetime
from datetime import date
from helper_functions import *
import holidays

# --- Terminal Styling (ANSI) -------------------------------------------------
# Aktiviert ANSI-Escape-Sequenzen unter Windows (10+), damit Farben & Stile
# auch in der klassischen Konsole funktionieren.
# NTUser for name

if os.name == "nt":
    os.system("")
clear_console()


# Global Vars
template_path = r"C:\Users\PVV1FE\Documents\Projects\Python\Berichtsheft-Generator\bheft_template.pdf"
output_dir    = r"C:\Users\PVV1FE\Documents\Projects\Python\Berichtsheft-Generator"
reader = PdfReader(template_path)
page = reader.pages[0]
text = page.extract_text()
current_report_index = 0
calculate_holidays = False
calculate_vacation = False
province = "BW"
file_name = "Berichtsheft"
full_name = "Max Mustermann"
current_department = "PEA6-Fe-FI"

# Main loop to collect user input, ask for confirmation and clear console for next steps. Repeats until user confirms.
while True:

    # Get all user information. Returns the collected information as a tuple.
    file_name, full_name, current_department, current_report_index, start_date, end_date, calculate_holidays, province, vacation_periods_list, calculate_vacation = get_user_input()

    # Calculate all workdays between start and end date, excluding weekends. If calculate_holidays is True, 
    # also include holidays based on the selected province.
    workdays = pd.bdate_range(start=start_date, end=end_date)

    # Create a DataFrame from the workdays to easily group by week and year later. Extract week number and year for each date.
    df = pd.DataFrame({"date": workdays})
    df["week"] = df["date"].dt.isocalendar().week
    df["year"] = df["date"].dt.isocalendar().year

    # Create a summary section to show the user the collected information and calculated workdays, 
    # and ask for confirmation to proceed with report generation. If user confirms, break the loop. 
    # Otherwise, clear the console and repeat the input process.
    clear_console()
    section("Übersicht")
    info("Dateiname",          file_name,                       C.MAGENTA)
    info("Start Nachweis-Nr.", str(current_report_index),       C.MAGENTA)
    info("Abteilung",         current_department,              C.MAGENTA)
    info("Zeitraum",           f"{start_date}  →  {end_date}",  C.MAGENTA)
    info("Arbeitstage",        str(len(workdays)),              C.MAGENTA)
    info("Bundesland für Feiertage", province if calculate_holidays else "N/A", C.MAGENTA)
    info("Urlaubszeiträume",   ", ".join([f"{start} bis {end}" for period in vacation_periods_list for start, end in period]) if calculate_vacation else "N/A", C.MAGENTA)

    section_end()

    # Confirmation dialog: Waits for ENTER (True) or ESC (False). Ignores key-release events.
    if ask_confirm():
        clear_console()
        break
    clear_console()



print()
subheader("Generiere Berichtshefte …")



# Main Loop for PDF generation: Groups the DataFrame by week and year, checks for complete weeks (at least 5 workdays),
# and generates a PDF report files for each complete week using the template. If calculate_holidays is True, 
# it also checks for holidays in the week and markes them on their respective days. Keeps track of generated and skipped reports for the final summary.

generated = 0
skipped   = 0

for (year, week), group in df.groupby(["year", "week"]):

    # Extract start and end date of the week, and create a list of all dates in that week. Check if the week has at least 5 workdays, otherwise skip it.
    week_start = group["date"].min()
    week_end   = group["date"].max()
    all_week_dates = pd.date_range(start=week_start, end=week_end)
    days_in_week = (week_end - week_start).days + 1
    if days_in_week < 5:
        warn(f"KW {int(week):02d}/{int(year)}: keine vollständige Woche – übersprungen")
        skipped += 1
        continue

    all_holiday_dates = []
    for period in vacation_periods_list:
        for start, end in period:
            all_holiday_dates.extend(pd.date_range(start=start, end=end).tolist())

    # Generate the output path for the PDF report based on the file name and current report index.
    output_path = os.path.join(output_dir, f"{file_name}_{current_report_index}.pdf")

    # Define pdf reader and writer, read the template and get all neede form fields.
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    writer.set_need_appearances_writer(True)
    fields = reader.get_fields()


    # If calculate_holidays is true, get all holidays for the current year and selected province,
    # then check if any of the dates in the current week are holidays, and mark the days with (Feiertag)
    
    week_holidays = []
    if calculate_holidays:
        week_holidays = holidays.country_holidays("DE", years=[year], subdiv=province)

    # Normalize vacation dates to plain date objects for reliable comparison
    vacation_dates_set = {d.date() for d in all_holiday_dates}

    manipulated_days_texts = ["" for _ in range(5)]
    # Only consider Mon–Fri (first 5 days of the week)
    for i, single_date in enumerate(all_week_dates[:5]):
        single_date_only = single_date.date()
        if calculate_holidays and single_date_only in week_holidays:
            manipulated_days_texts[i] = "(Feiertag)"
        elif calculate_vacation and single_date_only in vacation_dates_set:
            manipulated_days_texts[i] = "(Urlaub)"

    # Inject every info into the pdf file form fields
    writer.update_page_form_field_values(
        writer.pages[0],
        {
            "Date1_af_date": week_start.strftime("%d.%m.%Y"),
            "Date2_af_date": week_end.strftime("%d.%m.%Y"),
            "Date5_af_date": week_end.strftime("%d.%m.%Y"),
            "Text3": str(full_name),
            "Text4": str(current_report_index),
            "Text12": str(current_department),
            "Text6": f"Montag: {manipulated_days_texts[0]}\n\n"
                     f"Dienstag: {manipulated_days_texts[1]}\n\n"
                     f"Mittwoch: {manipulated_days_texts[2]}\n\n"
                     f"Donnerstag: {manipulated_days_texts[3]}\n\n"
                     f"Freitag: {manipulated_days_texts[4]}",
        },
    )

    # Write the modified PDF to the output path.
    with open(output_path, "wb") as file:
        writer.write(file)

    # Print a success message for the generated report
    report_row(
        current_report_index,
        int(week),
        int(year),
        week_start,
        week_end,
        os.path.basename(output_path),
    )

    current_report_index += 1
    generated += 1


# After processing all weeks, clear the console and print a summary of generated reports, skipped weeks and output directory.
clear_console()
section("Zusammenfassung")
info("Erstellte Berichte",    str(generated), C.GREEN)
info("Übersprungene Wochen",  str(skipped),   C.YELLOW if skipped else C.GREEN)
info("Ausgabeverzeichnis",    output_dir,     C.DIM)
info("Berichtsheft Konfiguration:", f"\n Dateiname: {file_name}\n "
                                    f"Voller Name: {full_name}\n "
                                    f"Start Nachweis-Nr.: {current_report_index}\n "
                                    f"Abteilung: {current_department}\n "
                                    f"Zeitraum: {start_date}  →  {end_date}\n "
                                    f"Bundesland für Feiertage: {province if calculate_holidays else 'N/A'}\n "
                                    f"Urlaubszeiträume: {', '.join([f'{start} bis {end}' for period in vacation_periods_list for start, end in period]) if calculate_vacation else 'N/A'}", C.CYAN)
section_end()

print(
    f"\n{C.GREEN}{C.BOLD}✔ Fertig!{C.RESET} "
    f"{C.DIM}{generated} Berichtsheft(e) erfolgreich generiert.{C.RESET}\n"
)
