# Verspätung UI-Verbesserung: Nur geplante Ankunftsdaten anzeigen

**Datum:** 28.01.2026  
**Problem:** Benutzer kann Datum eingeben, das kein geplantes Ankunftsdatum ist → Verspätung wird nicht angewendet  
**Status:** ✅ **IMPLEMENTIERT**

---

## 🔍 Identifiziertes Problem

### Beschreibung

Bei der Auswahl eines Verspätungs-Szenarios kann der Benutzer ein beliebiges Datum eingeben. Wenn dieses Datum kein geplantes Ankunftsdatum ist, wird die Verspätung nicht angewendet, was verwirrend ist.

**Beispiel:**
- Benutzer wählt: "Ankunft Schiff", Datum: 19.07.2027, Verspätung: 1 Tag
- Problem: Am 19.07.2027 kommt kein Schiff an (geplante Ankünfte: 16.07. und 23.07.)
- Ergebnis: Verspätung wird nicht angewendet, nichts passiert

### Warum passiert nichts?

Die Verspätungsprüfung erfolgt am **geplanten Ankunftsdatum**:
```python
if day_ship_arr_ideal_idx == scenario.start_day:
    ship_arrival_delay = max(ship_arrival_delay, scenario.delay_days)
```

Wenn das eingegebene Datum kein geplantes Ankunftsdatum ist, wird die Bedingung nie erfüllt.

---

## ✅ Implementierte Lösung

### Funktion: `_get_planned_arrival_dates()`

**Zweck:** Extrahiert alle geplanten Ankunftsdaten für einen bestimmten Verspätungstyp aus der Inbound-Tabelle.

**Spalten-Mapping:**
- `truck_china_arrival` → "Ankunft LKW 🇨🇳" (tatsächliche Ankunft = geplante Ankunft ohne Verspätungen)
- `ship_arrival` → "Ankunft Schiff 🇩🇪" (tatsächliche Ankunft = geplante Ankunft ohne Verspätungen)
- `truck_de_arrival` → "Geplante Ankunft LKW 🇩🇪" (explizit geplante Ankunft)

**Hinweis:** Für LKW China und Schiff gibt es keine explizite "Geplante Ankunft" Spalte. Die tatsächlichen Ankünfte werden verwendet, da sie ohne Verspätungen gleich den geplanten Ankünften sind.

### UI-Verbesserung

**Vorher:**
- Freie Datumsauswahl mit `st.date_input()`
- Benutzer kann beliebiges Datum eingeben
- Keine Validierung ob Datum gültig ist

**Nachher:**
- **Wenn geplante Ankunftsdaten verfügbar:**
  - Dropdown-Liste mit nur geplanten Ankunftsdaten
  - Format: "DD.MM.YYYY"
  - Hilfetext erklärt was ausgewählt wird
  - Keine Möglichkeit ungültige Daten einzugeben

- **Wenn keine geplanten Ankunftsdaten verfügbar:**
  - Fallback auf freie Datumsauswahl
  - Warnung dass keine Daten gefunden wurden
  - Hinweis dass Datum geplantem Ankunftsdatum entsprechen muss

---

## 📋 Code-Änderungen

### Neue Funktion: `_get_planned_arrival_dates()`

```python
def _get_planned_arrival_dates(delay_stage: str, planning_year: int) -> List[date]:
    """
    Extrahiert alle geplanten Ankunftsdaten für einen bestimmten Verspätungstyp aus der Inbound-Tabelle.
    
    Args:
        delay_stage: "truck_china_arrival", "ship_arrival", oder "truck_de_arrival"
        planning_year: Planungsjahr
    
    Returns:
        Liste von Datums-Objekten (sortiert)
    """
    # 1. Prüfe ob Simulator verfügbar ist
    # 2. Hole Inbound-Tabelle
    # 3. Extrahiere Datums aus entsprechender Spalte
    # 4. Sortiere und gib zurück
```

### UI-Anpassung in `render_scenario_sidebar()`

```python
# Hole geplante Ankunftsdaten für den ausgewählten Verspätungstyp
planned_dates = _get_planned_arrival_dates(delay_stage, planning_year)

if planned_dates:
    # Zeige nur geplante Ankunftsdaten als Optionen
    date_options = {d.strftime(MasterData.DATE_FORMAT): d for d in planned_dates}
    selected_date_str = st.selectbox(...)
    delay_date = date_options[selected_date_str]
else:
    # Fallback: Freie Datumsauswahl
    delay_date = st.date_input(...)
```

---

## 🎯 Vorteile

1. **Benutzerfreundlichkeit:**
   - Nur gültige Daten werden angezeigt
   - Keine Verwirrung mehr durch ungültige Eingaben
   - Klare Auswahlmöglichkeiten

2. **Fehlerprävention:**
   - Unmögliche Eingaben werden verhindert
   - Verspätungen werden immer korrekt angewendet
   - Weniger Support-Anfragen

3. **Transparenz:**
   - Benutzer sieht welche Ankunftsdaten verfügbar sind
   - Hilfetext erklärt was ausgewählt wird
   - Warnung wenn keine Daten verfügbar

---

## ⚠️ Einschränkungen

### Wenn bereits Verspätungen aktiv sind:

**Problem:** Die Spalten "Ankunft LKW 🇨🇳" und "Ankunft Schiff 🇩🇪" zeigen dann die **tatsächlichen** (verspäteten) Ankünfte, nicht die geplanten.

**Lösung:** 
- Die Funktion verwendet die tatsächlichen Ankünfte
- Wenn Verspätungen aktiv sind, können die angezeigten Daten von den geplanten abweichen
- **Workaround:** Verspätungen nacheinander hinzufügen (nicht gleichzeitig)

**Zukünftige Verbesserung:**
- Separate Spalten für geplante Ankünfte in der Inbound-Tabelle
- Oder: Berechnung der geplanten Ankünfte direkt aus der Logik (ohne Tabelle)

---

## 🧪 Test-Empfehlungen

### Test 1: Ankunft Schiff - Geplante Daten anzeigen

**Schritte:**
1. Starte Simulation
2. Gehe zu Szenarien-Sidebar
3. Wähle "Verspätung" → "Ankunft Schiff"
4. Prüfe: Werden nur geplante Ankunftsdaten angezeigt?

**Erwartung:**
- Dropdown zeigt nur Daten wie 16.07.2027, 23.07.2027, etc.
- Kein 19.07.2027 (kein geplantes Ankunftsdatum)

### Test 2: Verspätung hinzufügen

**Schritte:**
1. Wähle geplantes Ankunftsdatum (z.B. 23.07.2027)
2. Setze Verspätung: 1 Tag
3. Füge Verspätung hinzu
4. Prüfe Inbound-Tabelle: Wird Verspätung angewendet?

**Erwartung:**
- Verspätung wird korrekt angewendet
- Ankunft Schiff verschiebt sich um 1 Tag

### Test 3: Fallback bei fehlender Simulation

**Schritte:**
1. Starte Simulation NICHT
2. Gehe zu Szenarien-Sidebar
3. Wähle "Verspätung"
4. Prüfe: Wird Fallback angezeigt?

**Erwartung:**
- Warnung: "Keine geplanten Ankunftsdaten gefunden"
- Freie Datumsauswahl wird angezeigt

---

## ✅ Status

- ✅ Funktion `_get_planned_arrival_dates()` implementiert
- ✅ UI angepasst: Dropdown mit geplanten Ankunftsdaten
- ✅ Fallback für fehlende Daten implementiert
- ✅ Hilfetexte hinzugefügt
- ⚠️ Einschränkung: Funktioniert nur wenn keine Verspätungen aktiv sind (siehe oben)

---

**Status:** ✅ **IMPLEMENTIERT - BEREIT FÜR TESTS**
