# Merge-Anleitung: Arbeitslast-Fix

**Datum:** 31.01.2026  
**Commit:** `107bd11` - "Fix: Tägliche Arbeitslast wird korrekt in Produktion und Materiallager übernommen"

---

## 🎯 Ziel

Beim Mergen sollen **nur die spezifischen Änderungen zur Arbeitslast-Übernahme** aus diesem Commit erhalten bleiben. Alle anderen Änderungen deines Kollegen sollen dominieren.

---

## 📋 Betroffene Dateien

Die folgenden Dateien wurden für den Arbeitslast-Fix geändert:

1. `pages/8_stammdaten.py`
2. `pages/5_materiallager.py`
3. `pages/6_produktion.py`
4. `simulation/production_planner.py`
5. `ui/material_calculations.py`

---

## 🔧 Merge-Strategie

### Option 1: Manueller Merge (Empfohlen)

**Schritt 1: Pull von main**
```bash
git pull origin main
```

**Schritt 2: Bei Konflikten in den betroffenen Dateien**

Für jede Datei mit Konflikten:

#### `pages/8_stammdaten.py`
**BEHALTEN (aus diesem Fix):**
- Zeilen ~471-477: Simulator-Reset bei `workload_changed`
  ```python
  # KRITISCH: Setze Simulator zurück, damit neue DAILY_WORKLOAD-Werte verwendet werden
  st.session_state.happy_path_run = False
  st.session_state.results_df = None
  st.session_state.simulator = None
  st.session_state.simulation_running = False
  st.session_state.simulation_started = False
  ```

**REST:** Alle anderen Änderungen deines Kollegen behalten

---

#### `simulation/production_planner.py`
**BEHALTEN (aus diesem Fix):**
- Zeile ~577: `'Is_Workday': is_workday` zur Log-Entry hinzufügen
  ```python
  'Is_Weekend': is_weekend,
  'Is_Holiday': is_holiday,
  'Is_Workday': is_workday  # <-- Diese Zeile hinzufügen
  ```

**REST:** Alle anderen Änderungen deines Kollegen behalten

---

#### `ui/material_calculations.py`
**BEHALTEN (aus diesem Fix):**
- Zeilen ~204-209: `is_workday` Berechnung hinzufügen
  ```python
  is_workday = False
  
  if 0 <= day < 365:
      # Prüfe ob Arbeitstag (berücksichtigt DAILY_WORKLOAD)
      is_workday = workday_calc.is_workday(day)
  ```

- Zeile ~262: `'Is_Workday': is_workday` zur Log-Entry hinzufügen
  ```python
  'Is_Weekend': is_workday,
  'Is_Holiday': is_holiday,
  'Is_Workday': is_workday  # <-- Diese Zeile hinzufügen
  ```

**REST:** Alle anderen Änderungen deines Kollegen behalten

---

#### `pages/6_produktion.py`
**BEHALTEN (aus diesem Fix):**
- Zeilen ~149-153: `workday_flags` und `non_workday_flags` hinzufügen
  ```python
  workday_flags = df_prod_filtered['Is_Workday'].values if 'Is_Workday' in df_prod_filtered.columns else None
  # Nicht-Arbeitstage: Tage die nicht Wochenende sind, aber auch kein Arbeitstag (DAILY_WORKLOAD = 0.0)
  non_workday_flags = None
  if workday_flags is not None:
      non_workday_flags = ~workday_flags & ~weekend_flags
  ```

- Zeilen ~257-258: `non_workday_flags_extended` hinzufügen
  ```python
  non_workday_flags_extended = list(non_workday_flags) + [False] if non_workday_flags is not None else None
  ```

- Zeilen ~261-262: `non_workday_flags_extended` im else-Block
  ```python
  non_workday_flags_extended = non_workday_flags
  ```

- Zeilen ~279-281: Nicht-Arbeitstage grün einfärben
  ```python
  # Nicht-Arbeitstage (DAILY_WORKLOAD = 0.0) - grün wie Feiertage
  if non_workday_flags_extended is not None and idx < len(non_workday_flags_extended) and non_workday_flags_extended[idx]:
      return ['background-color: #c8e6c9'] * len(row)
  ```

- Zeile ~189: Legende aktualisieren
  ```python
  <span style="background-color: #c8e6c9; ...">Feiertag / Kein Arbeitstag</span>
  ```

**REST:** Alle anderen Änderungen deines Kollegen behalten

---

#### `pages/5_materiallager.py`
**BEHALTEN (aus diesem Fix):**
- Zeilen ~172-177: `workday_flags` und `non_workday_flags` hinzufügen
  ```python
  workday_flags = df_filt['Is_Workday'].values if 'Is_Workday' in df_filt.columns else None
  # Nicht-Arbeitstage: Tage die nicht Wochenende sind, aber auch kein Arbeitstag (DAILY_WORKLOAD = 0.0)
  non_workday_flags = None
  if workday_flags is not None:
      non_workday_flags = ~workday_flags & ~weekend_flags
  ```

- Zeilen ~180-182: Nicht-Arbeitstage grün einfärben in `style_row_safe`
  ```python
  # Nicht-Arbeitstage (DAILY_WORKLOAD = 0.0) - grün wie Feiertage
  if non_workday_flags is not None and row.name < len(non_workday_flags) and non_workday_flags[row.name]:
      return ['background-color: #c8e6c9'] * len(row)
  ```

- Zeilen ~211-212: `non_workday_flags_extended` hinzufügen
  ```python
  non_workday_flags_extended = list(non_workday_flags) + [False] if non_workday_flags is not None else None
  ```

- Zeilen ~215-216: `non_workday_flags_extended` im else-Block
  ```python
  non_workday_flags_extended = non_workday_flags
  ```

- Zeilen ~231-233: Nicht-Arbeitstage grün einfärben in `style_row_with_sum`
  ```python
  # Nicht-Arbeitstage (DAILY_WORKLOAD = 0.0) - grün wie Feiertage
  if non_workday_flags_extended is not None and idx < len(non_workday_flags_extended) and non_workday_flags_extended[idx]:
      return ['background-color: #c8e6c9'] * len(row)
  ```

- Zeile ~234: Legende aktualisieren
  ```python
  <span style="background-color: #c8e6c9; ...">Feiertag / Kein Arbeitstag</span>
  ```

**REST:** Alle anderen Änderungen deines Kollegen behalten

---

### Option 2: Cherry-Pick spezifischer Zeilen (Fortgeschritten)

Falls der Kollege sehr viele Änderungen hat, kann er auch nur die spezifischen Zeilen aus diesem Commit übernehmen:

```bash
# 1. Pull von main
git pull origin main

# 2. Bei Konflikten: Nur die oben genannten Zeilen aus diesem Commit übernehmen
# (Manuell in den betroffenen Dateien)
```

---

## ✅ Verifikation nach dem Merge

Nach dem Merge sollte der Kollege testen:

1. **Stammdaten → Planung → Tägliche Arbeitslast**: Montag auf 0.0 setzen
2. **Produktion**: Montag sollte grün eingefärbt sein (wie Feiertag)
3. **Materiallager**: Montag sollte grün eingefärbt sein (wie Feiertag)
4. **Simulation**: Sollte neu starten, wenn Arbeitslast geändert wird

---

## 📝 Zusammenfassung

**Kern-Änderungen die erhalten bleiben müssen:**
- ✅ Simulator-Reset bei `DAILY_WORKLOAD`-Änderung (`pages/8_stammdaten.py`)
- ✅ `Is_Workday` Spalte in Logs (`simulation/production_planner.py`, `ui/material_calculations.py`)
- ✅ Grüne Einfärbung für Nicht-Arbeitstage (`pages/5_materiallager.py`, `pages/6_produktion.py`)
- ✅ Aktualisierte Legenden

**Alles andere:** Sollte vom Kollegen kommen.

---

## 🆘 Bei Problemen

Falls es zu komplexen Konflikten kommt:
1. Kollege kann auch erstmal seine Änderungen committen
2. Dann diesen Fix als separaten Commit aufsetzen
3. Oder: Gemeinsam die Konflikte lösen
