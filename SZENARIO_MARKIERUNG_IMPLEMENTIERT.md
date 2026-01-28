# Szenario-Markierung in Tabellen - Implementiert

**Datum:** 28.01.2026  
**Status:** ✅ **IMPLEMENTIERT**

---

## ✅ Implementierte Funktionen

### 1. Neue Hilfsfunktionen (`ui/table_styling.py`)

**`get_scenario_affected_rows(df, table_type)`**
- Identifiziert Zeilen die durch Szenarien beeinflusst werden
- Unterstützt verschiedene Tabellentypen:
  - `'production'`: Markiert wenn `tatsächliche PM != geplante PM` oder `Backlog > 0`
  - `'inbound'`: Markiert wenn `Verspätung > 0`, `Ladungsverlust > 0`, oder `geplante != tatsächliche Ankunft`
  - `'volume_planning'`: Markiert wenn `geplant != tatsächlich` für Produkte
  - `'material'`: Markiert wenn Bestände durch Szenarien beeinflusst werden

**`style_row_with_scenarios(row, affected_flags, weekend_flags, holiday_flags)`**
- Styling-Funktion für DataFrame-Zeilen
- Priorität: Wochenende > Feiertag > Szenario > Normal
- Gelber Hintergrund (`#fff9c4`) für szenario-beeinflusste Zeilen

---

## 📋 Geänderte Seiten

### 1. Produktion (`pages/6_produktion.py`)
- ✅ Szenario-Markierung hinzugefügt
- ✅ Legende erweitert (⚠️ Szenario)
- ✅ Markiert Zeilen wenn:
  - `tatsächliche PM != geplante PM`
  - `Backlog > 0`

### 2. Inbound (`pages/4_inbound.py`)
- ✅ Szenario-Markierung hinzugefügt
- ✅ Legende hinzugefügt (⚠️ Szenario)
- ✅ Markiert Zeilen wenn:
  - `Verspätung > 0`
  - `Ladungsverlust > 0`
  - `Geplante Ankunft != Tatsächliche Ankunft`

### 3. Volumenplanung (`pages/2_volumenplanung.py`)
- ✅ Szenario-Markierung hinzugefügt
- ✅ Legende hinzugefügt (⚠️ Szenario)
- ✅ Markiert Zeilen wenn:
  - `geplant != tatsächlich` für Produkte

---

## 🎨 Farbcodierung

| Farbe | Bedeutung |
|-------|-----------|
| `#ffebee` (Rosa) | Wochenende |
| `#c8e6c9` (Grün) | Feiertag |
| `#fff9c4` (Gelb) | ⚠️ **Szenario-beeinflusst** |
| `#e0e0e0` (Grau) | Summenzeile |

---

## 📝 Code-Beispiel

**Vorher:**
```python
def style_row(row):
    idx = row.name
    if weekend_flags[idx]:
        return ['background-color: #ffebee'] * len(row)
    return [''] * len(row)
```

**Nachher:**
```python
from ui.table_styling import get_scenario_affected_rows, style_row_with_scenarios

affected_flags = get_scenario_affected_rows(df, 'production')
affected_flags_extended = list(affected_flags) + [False]

def style_row_with_sum(row):
    return style_row_with_scenarios(
        row, 
        affected_flags_extended, 
        weekend_flags_extended, 
        holiday_flags_extended
    )
```

---

## ✅ Vorteile

1. **Wiederverwendbar:** Eine Funktion für alle Tabellentypen
2. **Wenig Code:** Nur 2-3 Zeilen pro Seite
3. **Konsistent:** Einheitliche Markierung über alle Seiten
4. **Erweiterbar:** Einfach neue Tabellentypen hinzufügen

---

## 🧪 Test-Empfehlungen

### Test 1: Verspätung-Szenario
1. Füge Verspätung "Ankunft LKW China" hinzu
2. Gehe zu **Inbound**
3. Prüfe ob betroffene Zeile gelb markiert ist

### Test 2: Marketing-Szenario
1. Füge Marketing-Kampagne hinzu
2. Gehe zu **Volumenplanung**
3. Prüfe ob Tage mit erhöhter Nachfrage gelb markiert sind

### Test 3: Produktion mit Backlog
1. Erzeuge Backlog (z.B. durch Materialmangel)
2. Gehe zu **Produktion**
3. Prüfe ob Zeilen mit Backlog gelb markiert sind

---

## ✅ Status

- ✅ **IMPLEMENTIERT**
- ✅ **BEREIT FÜR TESTS**
