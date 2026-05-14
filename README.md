# Vorsorge-Dashboard

Eine einfache Streamlit-App zur Übersicht von Vorsorgeuntersuchungen für zwei Personen:

- Mann, 64 Jahre
- Frau, 57 Jahre

Die App berechnet automatisch den nächsten Termin aus der letzten Durchführung und dem Intervall in Monaten. Überfällige Untersuchungen werden farblich markiert.
In der Kalenderansicht werden bisherige und anstehende Untersuchungen nach Jahr und Monat angezeigt.

## Projektstruktur

```text
.
├── app.py
├── data/
│   └── vorsorge_default.csv
├── requirements.txt
└── README.md
```

## Installation

Öffne ein Terminal im Projektordner und installiere die benötigten Pakete:

```bash
pip install -r requirements.txt
```

Falls Windows meldet, dass `python` oder `pip` nicht gefunden wurde, installiere zuerst Python von <https://www.python.org/downloads/> und aktiviere bei der Installation die Option **Add Python to PATH**.

## App starten

```bash
streamlit run app.py
```

Streamlit zeigt danach eine lokale Adresse an, meistens:

```text
http://localhost:8501
```

## Daten speichern und laden

- Die App startet mit Beispieldaten aus `data/vorsorge_default.csv`.
- Über **Aktuelle Daten speichern** wird der aktuelle Stand als `data/vorsorge.csv` gespeichert.
- Beim nächsten Start lädt die App automatisch `data/vorsorge.csv`, falls diese Datei vorhanden ist.
- Über **CSV herunterladen** kann die Tabelle exportiert werden.
- Über **CSV-Datei laden** kann eine eigene CSV-Datei importiert werden.

## Kalender

Die Kalenderansicht zeigt:

- bisherige Untersuchungen aus der Spalte `Letzte Durchführung`
- anstehende Untersuchungen aus der automatisch berechneten Spalte `Nächster Termin`
- Farben nach Dringlichkeit, Priorität und Status
- Monatsnavigation mit Pfeilen
- eine Detailtabelle für die aktuell sichtbaren Kalendereinträge

## Spalten

Die Tabelle enthält:

- Untersuchung
- Person (`Mann` oder `Frau`)
- Kategorie
- Priorität
- Letzte Durchführung
- Intervall in Monaten
- Nächster Termin
- Status
- Kommentar

## Hinweis

Die Beispieldaten sind als praktische Startwerte gedacht. Medizinische Intervalle und persönliche Empfehlungen sollten immer mit Ärztin, Arzt oder Krankenkasse abgestimmt werden.
