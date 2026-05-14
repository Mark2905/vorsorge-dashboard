import calendar
from html import escape
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st


APP_TITLE = "Vorsorge-Dashboard"
DATA_DIR = Path("data")
DEFAULT_DATA_FILE = DATA_DIR / "vorsorge_default.csv"
SAVED_DATA_FILE = DATA_DIR / "vorsorge.csv"

COLUMNS = [
    "Untersuchung",
    "Person",
    "Kategorie",
    "Priorität",
    "Letzte Durchführung",
    "Intervall in Monaten",
    "Nächster Termin",
    "Status",
    "Kommentar",
]

PERSONEN = ["Mann", "Frau"]
KATEGORIEN = [
    "Hausarzt",
    "Herz-Kreislauf",
    "Krebsfrüherkennung",
    "Impfung",
    "Zahnarzt",
    "Augenarzt",
    "Zusatzdiagnostik",
]
PRIORITAETEN = ["sehr hoch", "hoch", "mittel", "optional"]
STATUSWERTE = ["offen", "geplant", "erledigt", "überfällig"]
MONATSNAMEN = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
PRIORITAET_SORTIERUNG = {
    "sehr hoch": 0,
    "hoch": 1,
    "mittel": 2,
    "optional": 3,
}
KALENDER_FARBEN = {
    "überfällig": ("#ffd6d6", "#c92a2a", "#7a1f1f"),
    "sehr hoch": ("#ffe3e3", "#e03131", "#7a1f1f"),
    "hoch": ("#fff0d6", "#f08c00", "#5f3700"),
    "mittel": ("#dbeafe", "#2563eb", "#1e3a8a"),
    "optional": ("#eef2f7", "#64748b", "#334155"),
    "bisherig": ("#d8f5dd", "#2f9e44", "#165c26"),
}


def load_data() -> pd.DataFrame:
    """Load saved data first. If it does not exist, use the default examples."""
    DATA_DIR.mkdir(exist_ok=True)
    data_file = SAVED_DATA_FILE if SAVED_DATA_FILE.exists() else DEFAULT_DATA_FILE
    df = pd.read_csv(data_file)
    return prepare_data(df)


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns and calculate the next due date."""
    for column in COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[COLUMNS].copy()
    df = df.dropna(how="all")
    df = df[df["Untersuchung"].fillna("").astype(str).str.strip() != ""]
    df = expand_shared_person_rows(df)

    df["Letzte Durchführung"] = pd.to_datetime(df["Letzte Durchführung"], errors="coerce")
    df["Intervall in Monaten"] = pd.to_numeric(
        df["Intervall in Monaten"], errors="coerce"
    ).fillna(12).astype(int)
    df["Person"] = df["Person"].where(df["Person"].isin(PERSONEN), "Mann")
    df["Kategorie"] = df["Kategorie"].where(df["Kategorie"].isin(KATEGORIEN), "Hausarzt")
    df["Priorität"] = df["Priorität"].where(
        df["Priorität"].isin(PRIORITAETEN), "mittel"
    )
    df["Status"] = df["Status"].where(df["Status"].isin(STATUSWERTE), "offen")

    df["Nächster Termin"] = df.apply(calculate_next_date, axis=1)
    df["Status"] = df.apply(update_status, axis=1)
    return df


def expand_shared_person_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Convert old 'beide' rows into one row for Mann and one row for Frau."""
    shared_mask = df["Person"].fillna("").astype(str).str.lower().str.strip() == "beide"
    if not shared_mask.any():
        return df

    shared_rows = []
    for _, row in df[shared_mask].iterrows():
        for person in PERSONEN:
            copied_row = row.copy()
            copied_row["Person"] = person
            shared_rows.append(copied_row)

    personal_rows = df[~shared_mask]
    expanded_rows = pd.DataFrame(shared_rows, columns=df.columns)
    return pd.concat([personal_rows, expanded_rows], ignore_index=True)


def calculate_next_date(row: pd.Series) -> pd.Timestamp:
    """Calculate next due date from last date and interval in months."""
    last_date = row["Letzte Durchführung"]
    if pd.isna(last_date):
        return pd.NaT
    return last_date + pd.DateOffset(months=int(row["Intervall in Monaten"]))


def update_status(row: pd.Series) -> str:
    """Calculate the status from the next due date and the current workflow state."""
    status = str(row["Status"]).strip() or "offen"
    next_date = row["Nächster Termin"]
    today = pd.Timestamp.today().normalize()

    if pd.notna(next_date) and next_date.normalize() < today:
        return "überfällig"
    if status == "überfällig":
        return "offen"
    if status == "erledigt":
        return "erledigt"
    if status == "geplant":
        return "geplant"
    return status if status in STATUSWERTE else "offen"


def update_completion_dates(
    edited_df: pd.DataFrame, original_df: pd.DataFrame
) -> pd.DataFrame:
    """Set last done date to today when a row is newly marked as done."""
    today = pd.Timestamp.today().normalize()
    updated_df = edited_df.copy()
    updated_df["Letzte Durchführung"] = pd.to_datetime(
        updated_df["Letzte Durchführung"], errors="coerce"
    )

    for index, row in updated_df.iterrows():
        status = str(row.get("Status", "")).strip()
        if status != "erledigt":
            continue

        old_status = ""
        if index in original_df.index:
            old_status = str(original_df.loc[index, "Status"]).strip()

        last_done = pd.to_datetime(row.get("Letzte Durchführung"), errors="coerce")
        is_newly_done = old_status != "erledigt"
        has_no_date = pd.isna(last_done)

        if is_newly_done or has_no_date:
            updated_df.at[index, "Letzte Durchführung"] = today

    return updated_df


def save_data(df: pd.DataFrame) -> None:
    """Save the current table to data/vorsorge.csv."""
    DATA_DIR.mkdir(exist_ok=True)
    export_df = df.copy()
    export_df["Letzte Durchführung"] = export_df["Letzte Durchführung"].dt.strftime(
        "%Y-%m-%d"
    )
    export_df = export_df.drop(columns=["Nächster Termin"], errors="ignore")
    export_df.to_csv(SAVED_DATA_FILE, index=False)


def format_dates_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with readable date strings for tables and downloads."""
    display_df = df.copy()
    for column in ["Letzte Durchführung", "Nächster Termin"]:
        display_df[column] = display_df[column].dt.strftime("%Y-%m-%d").fillna("")
    return display_df


def highlight_overdue(row: pd.Series) -> list[str]:
    """Color overdue rows in the main table."""
    if row["Status"] == "überfällig":
        return ["background-color: #ffd6d6; color: #7a1f1f"] * len(row)
    if row["Status"] == "geplant":
        return ["background-color: #fff3bf; color: #5f4700"] * len(row)
    if row["Status"] == "erledigt":
        return ["background-color: #d8f5dd; color: #165c26"] * len(row)
    return [""] * len(row)


def build_calendar_events(df: pd.DataFrame) -> pd.DataFrame:
    """Create one calendar event for last and one for next date."""
    events = []

    for _, row in df.iterrows():
        base_event = {
            "Untersuchung": row["Untersuchung"],
            "Person": row["Person"],
            "Kategorie": row["Kategorie"],
            "Priorität": row["Priorität"],
            "Status": row["Status"],
            "Kommentar": row["Kommentar"],
        }

        if pd.notna(row["Letzte Durchführung"]):
            events.append(
                {
                    **base_event,
                    "Datum": row["Letzte Durchführung"].normalize(),
                    "Art": "Bisherig",
                }
            )

        if pd.notna(row["Nächster Termin"]):
            events.append(
                {
                    **base_event,
                    "Datum": row["Nächster Termin"].normalize(),
                    "Art": "Anstehend",
                }
            )

    if not events:
        event_df = pd.DataFrame(
            columns=[
                "Datum",
                "Art",
                "Untersuchung",
                "Person",
                "Kategorie",
                "Priorität",
                "Status",
                "Kommentar",
            ]
        )
        event_df["Datum"] = pd.to_datetime(event_df["Datum"])
        return event_df

    event_df = pd.DataFrame(events)
    event_df["Datum"] = pd.to_datetime(event_df["Datum"])
    event_df["Sortierung"] = event_df["Priorität"].map(PRIORITAET_SORTIERUNG).fillna(9)
    return event_df.sort_values(["Datum", "Art", "Sortierung", "Untersuchung"])


def get_calendar_color(event: pd.Series) -> tuple[str, str, str]:
    """Return background, border and text color for one calendar event."""
    if event["Art"] == "Bisherig":
        return KALENDER_FARBEN["bisherig"]
    if event["Status"] == "überfällig":
        return KALENDER_FARBEN["überfällig"]
    return KALENDER_FARBEN.get(event["Priorität"], KALENDER_FARBEN["mittel"])


def render_event_chip(event: pd.Series) -> str:
    """Render one compact event chip for the HTML calendar."""
    background, border, color = get_calendar_color(event)
    art_label = "bisherig" if event["Art"] == "Bisherig" else "fällig"
    title = (
        f"{event['Datum'].strftime('%d.%m.%Y')} | {event['Art']} | "
        f"{event['Person']} | {event['Untersuchung']} | {event['Priorität']}"
    )
    return (
        f'<div class="calendar-event" title="{escape(title)}" '
        f'style="background:{background}; border-left-color:{border}; color:{color};">'
        f'<span class="calendar-event-type">{escape(art_label)}</span>'
        f'<span>{escape(str(event["Person"]))}: '
        f'{escape(str(event["Untersuchung"]))}</span></div>'
    )


def render_month_calendar(events: pd.DataFrame, year: int, month: int) -> None:
    """Render one month as a calendar grid."""
    month_events = events[
        (events["Datum"].dt.year == year) & (events["Datum"].dt.month == month)
    ].copy()
    events_by_day = {
        day: day_events
        for day, day_events in month_events.groupby(month_events["Datum"].dt.date)
    }

    today = pd.Timestamp.today().normalize().date()
    calendar_month = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    rows = []

    for week in calendar_month:
        day_cells = []
        for day in week:
            classes = ["calendar-day"]
            if day.month != month:
                classes.append("calendar-day-muted")
            if day == today:
                classes.append("calendar-day-today")

            day_events = events_by_day.get(day, pd.DataFrame())
            chips = "".join(render_event_chip(event) for _, event in day_events.iterrows())
            day_cells.append(
                f'<div class="{" ".join(classes)}">'
                f'<div class="calendar-date">{day.day}</div>'
                f'<div class="calendar-events">{chips}</div>'
                f"</div>"
            )
        rows.append(f"<div class='calendar-week'>{''.join(day_cells)}</div>")

    weekday_header = "".join(f"<div>{weekday}</div>" for weekday in WOCHENTAGE)
    html = (
        '<div class="calendar-month">'
        f'<div class="calendar-month-title">{MONATSNAMEN[month - 1]} {year}</div>'
        f'<div class="calendar-weekdays">{weekday_header}</div>'
        f'{"".join(rows)}'
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def get_available_years(df: pd.DataFrame, fallback_year: int) -> list[int]:
    """Return all years with previous or upcoming examinations."""
    years = [fallback_year]
    for column in ["Letzte Durchführung", "Nächster Termin"]:
        years.extend(df[column].dropna().dt.year.astype(int).tolist())
    return sorted(set(years))


def shift_calendar_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """Move a year/month pair by offset months."""
    month_index = year * 12 + (month - 1) + offset
    return month_index // 12, month_index % 12 + 1


def render_calendar_styles() -> None:
    """Add CSS for the Streamlit calendar."""
    st.markdown(
        dedent(
            """
        <style>
        .calendar-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.25rem 0 1rem;
        }
        .calendar-legend-item {
            align-items: center;
            border: 1px solid #d6dbe3;
            border-radius: 999px;
            display: inline-flex;
            font-size: 0.85rem;
            gap: 0.35rem;
            padding: 0.25rem 0.6rem;
        }
        .calendar-legend-dot {
            border-radius: 999px;
            display: inline-block;
            height: 0.7rem;
            width: 0.7rem;
        }
        .calendar-month {
            border: 1px solid #dfe3ea;
            border-radius: 0.5rem;
            margin-bottom: 1.25rem;
            overflow: hidden;
        }
        .calendar-month-title {
            background: #f6f8fb;
            border-bottom: 1px solid #dfe3ea;
            font-size: 1.05rem;
            font-weight: 700;
            padding: 0.8rem 0.9rem;
        }
        .calendar-weekdays,
        .calendar-week {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
        }
        .calendar-weekdays div {
            background: #fbfcfe;
            border-bottom: 1px solid #e7eaf0;
            color: #667085;
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.45rem 0.55rem;
            text-align: center;
        }
        .calendar-day {
            border-bottom: 1px solid #edf0f5;
            border-right: 1px solid #edf0f5;
            min-height: 8.25rem;
            padding: 0.4rem;
        }
        .calendar-week .calendar-day:nth-child(7) {
            border-right: none;
        }
        .calendar-week:last-child .calendar-day {
            border-bottom: none;
        }
        .calendar-day-muted {
            background: #fafbfc;
            color: #98a2b3;
        }
        .calendar-day-today {
            box-shadow: inset 0 0 0 2px #2563eb;
        }
        .calendar-date {
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        .calendar-events {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        .calendar-event {
            border-left: 4px solid;
            border-radius: 0.35rem;
            font-size: 0.72rem;
            line-height: 1.2;
            padding: 0.25rem 0.35rem;
            word-break: break-word;
        }
        .calendar-event-type {
            display: block;
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        @media (max-width: 900px) {
            .calendar-weekdays,
            .calendar-week {
                grid-template-columns: 1fr;
            }
            .calendar-weekdays {
                display: none;
            }
            .calendar-day {
                border-right: none;
                min-height: auto;
            }
            .calendar-day-muted {
                display: none;
            }
        }
        </style>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_calendar_legend() -> None:
    """Show the meaning of the calendar colors."""
    items = [
        ("Überfällig", KALENDER_FARBEN["überfällig"][1]),
        ("Sehr hoch", KALENDER_FARBEN["sehr hoch"][1]),
        ("Hoch", KALENDER_FARBEN["hoch"][1]),
        ("Mittel", KALENDER_FARBEN["mittel"][1]),
        ("Optional", KALENDER_FARBEN["optional"][1]),
        ("Bisherig", KALENDER_FARBEN["bisherig"][1]),
    ]
    legend = "".join(
        f'<span class="calendar-legend-item">'
        f'<span class="calendar-legend-dot" style="background:{color};"></span>'
        f"{escape(label)}</span>"
        for label, color in items
    )
    st.markdown(f"<div class='calendar-legend'>{legend}</div>", unsafe_allow_html=True)


def render_calendar_details(events: pd.DataFrame) -> None:
    """Render a table for the events currently visible in the calendar."""
    if events.empty:
        return

    detail_df = events[
        [
            "Datum",
            "Art",
            "Person",
            "Untersuchung",
            "Kategorie",
            "Priorität",
            "Status",
            "Kommentar",
        ]
    ].copy()
    detail_df["Datum"] = detail_df["Datum"].dt.strftime("%Y-%m-%d")

    with st.expander("Termindetails anzeigen"):
        st.dataframe(detail_df, use_container_width=True, hide_index=True)


def apply_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Render sidebar filters and return the filtered table plus a stable key."""
    st.sidebar.header("Filter")

    selected_person = st.sidebar.radio(
        "Person",
        PERSONEN,
        horizontal=True,
        key="filter_person",
    )
    selected_category = st.sidebar.multiselect(
        "Kategorie", KATEGORIEN, default=KATEGORIEN, key="filter_category"
    )
    selected_priority = st.sidebar.multiselect(
        "Priorität", PRIORITAETEN, default=PRIORITAETEN, key="filter_priority"
    )
    selected_status = st.sidebar.multiselect(
        "Status", STATUSWERTE, default=STATUSWERTE, key="filter_status"
    )

    filter_key = "|".join(
        [
            selected_person,
            ",".join(selected_category),
            ",".join(selected_priority),
            ",".join(selected_status),
        ]
    )

    filtered_df = df[
        (df["Person"] == selected_person)
        & df["Kategorie"].isin(selected_category)
        & df["Priorität"].isin(selected_priority)
        & df["Status"].isin(selected_status)
    ].copy()
    return filtered_df, str(abs(hash(filter_key)))


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🩺", layout="wide")
    st.title(APP_TITLE)

    if "vorsorge_df" not in st.session_state:
        st.session_state.vorsorge_df = load_data()

    df = prepare_data(st.session_state.vorsorge_df)
    st.session_state.vorsorge_df = df
    filtered_df, filter_key = apply_filters(df)

    today = pd.Timestamp.today().normalize()
    this_year = today.year

    overdue_count = int((filtered_df["Status"] == "überfällig").sum())
    due_this_year_count = int(
        (filtered_df["Nächster Termin"].dt.year == this_year).sum()
    )
    done_count = int((filtered_df["Status"] == "erledigt").sum())
    optional_count = int((filtered_df["Priorität"] == "optional").sum())

    metric_cols = st.columns(4)
    metric_cols[0].metric("Überfällig", overdue_count)
    metric_cols[1].metric(f"{this_year} fällig", due_this_year_count)
    metric_cols[2].metric("Erledigt", done_count)
    metric_cols[3].metric("Optional", optional_count)

    st.subheader("Fälligkeiten")
    display_filtered = format_dates_for_display(filtered_df)
    st.dataframe(
        display_filtered.style.apply(highlight_overdue, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Kalender")
    render_calendar_styles()
    render_calendar_legend()

    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = this_year
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = today.month

    nav_cols = st.columns([1, 4, 1, 1])
    previous_month_clicked = nav_cols[0].button("<", use_container_width=True)
    next_month_clicked = nav_cols[2].button(">", use_container_width=True)
    today_clicked = nav_cols[3].button("Heute", use_container_width=True)

    if previous_month_clicked:
        (
            st.session_state.calendar_year,
            st.session_state.calendar_month,
        ) = shift_calendar_month(
            st.session_state.calendar_year, st.session_state.calendar_month, -1
        )

    if next_month_clicked:
        (
            st.session_state.calendar_year,
            st.session_state.calendar_month,
        ) = shift_calendar_month(
            st.session_state.calendar_year, st.session_state.calendar_month, 1
        )

    if today_clicked:
        st.session_state.calendar_year = this_year
        st.session_state.calendar_month = today.month

    nav_cols[1].markdown(
        f"### {MONATSNAMEN[st.session_state.calendar_month - 1]} "
        f"{st.session_state.calendar_year}"
    )

    selected_year = st.session_state.calendar_year
    selected_month_number = st.session_state.calendar_month

    calendar_filter_cols = st.columns([1, 1, 2])
    show_previous = calendar_filter_cols[0].checkbox(
        "Bisherige Untersuchungen", value=True
    )
    show_upcoming = calendar_filter_cols[1].checkbox(
        "Anstehende Untersuchungen", value=True
    )

    calendar_events = build_calendar_events(filtered_df)
    calendar_events = calendar_events[calendar_events["Datum"].dt.year == selected_year]
    selected_types = []
    if show_previous:
        selected_types.append("Bisherig")
    if show_upcoming:
        selected_types.append("Anstehend")
    calendar_events = calendar_events[calendar_events["Art"].isin(selected_types)]
    calendar_events = calendar_events[
        calendar_events["Datum"].dt.month == selected_month_number
    ]

    render_month_calendar(calendar_events, selected_year, selected_month_number)
    if calendar_events.empty:
        st.info("Für diesen Monat gibt es mit den aktuellen Filtern keine Termine.")
    else:
        render_calendar_details(calendar_events)

    st.subheader("Vorsorge-Tabelle bearbeiten")
    st.write(
        "Hier kannst du Einträge direkt ändern, neue Zeilen hinzufügen oder Zeilen löschen."
    )

    editor_df = filtered_df.copy()

    edited_df = st.data_editor(
        editor_df,
        key=f"vorsorge_editor_{filter_key}",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Person": st.column_config.SelectboxColumn("Person", options=PERSONEN),
            "Kategorie": st.column_config.SelectboxColumn(
                "Kategorie", options=KATEGORIEN
            ),
            "Priorität": st.column_config.SelectboxColumn(
                "Priorität", options=PRIORITAETEN
            ),
            "Status": st.column_config.SelectboxColumn("Status", options=STATUSWERTE),
            "Letzte Durchführung": st.column_config.DateColumn(
                "Letzte Durchführung", format="YYYY-MM-DD"
            ),
            "Nächster Termin": st.column_config.DateColumn(
                "Nächster Termin", format="YYYY-MM-DD", disabled=True
            ),
            "Intervall in Monaten": st.column_config.NumberColumn(
                "Intervall in Monaten", min_value=1, step=1
            ),
        },
    )

    if st.button("Änderungen speichern"):
        edited_with_completion_dates = update_completion_dates(edited_df, filtered_df)
        updated_part = prepare_data(edited_with_completion_dates)
        unchanged_rows = df.drop(index=filtered_df.index)
        new_df = pd.concat([unchanged_rows, updated_part], ignore_index=True)
        st.session_state.vorsorge_df = prepare_data(new_df)
        save_data(st.session_state.vorsorge_df)
        st.success(f"Änderungen wurden gespeichert und sind beim nächsten Start wieder da.")
        st.rerun()

    st.info(
        "Hinweis: Diese App ersetzt keine medizinische Beratung. Intervalle und Empfehlungen bitte mit Ärztin, Arzt oder Krankenkasse abstimmen."
    )


if __name__ == "__main__":
    main()
