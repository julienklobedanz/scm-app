# Feature-Plan: Materialverbrauch pro Datum/Produkt

**Datum:** 31.01.2026  
**Feature:** Materialverbrauch-Analyse pro Datum in Produktion-Seite  
**Status:** 📋 Planungsphase

---

## 🎯 Ziel

In der Produktion-Seite soll oben ein Datum auswählbar sein. Nach Auswahl wird automatisch eine Übersicht angezeigt, die zeigt:
- Wie viel welchen Materials an diesem Tag für welches Fertigprodukt verwendet wurde
- Welche tatsächliche PM produziert wurde
- Vergleich mit geplanter PM
- Abweichungen und Ursachen

---

## 📊 Berechnung der tatsächlichen PM - Die Wurzel

### Datenfluss (von der Wurzel nach oben):

```
1. VOLUMENPLANUNG (daily_demands_actual)
   ↓
   calculate_volume_planning_demand()
   → Berechnet tägliche Nachfrage pro Produkt (mit Marketing-Szenarien)
   → Speichert in: st.session_state.daily_demands_actual[day][product] = demand

2. MATERIALVERFÜGBARKEIT (running_stock)
   ↓
   calculate_production_logs() → HAUPTSCHLEIFE (Tag 0-364)
   → Lädt Material aus Inbound: running_stock[saddle] += inbound_qty
   → Startbestand wird aus Inbound-Tabelle berechnet (kein transport_status mehr!)

3. RANGLÖGIK (_recalculate_all_products_with_rank_logic)
   ↓
   Input:
   - todays_demand_map = daily_demands_actual[day]
   - running_stock = verfügbares Material pro Sattel-Typ
   - daily_capacity = Schichten × Stunden × Kapazität/Stunde × Linien
   - current_backlog = Backlog vom Vortag
   
   Berechnungsschritte:
   
   a) Bedarf = Tagesbedarf + Backlog
      production_demand_by_product[product] = demand + backlog
   
   b) Anteilige Produktion (proportional)
      proportional = floor(demand × daily_capacity / total_demand)
      → Verteilt Kapazität proportional nach Bedarf
   
   c) Ranking
      rank_support = (row_number / 1000000.0) + proportional
      → Sortiert Produkte nach Rang (höherer Rang = wird zuerst produziert)
   
   d) Material-Check & Verteilung
      Für jedes Produkt (nach Rang sortiert):
      - minimal = verfügbares Material (saddle_available)
      - scheduled_qty = min(demand, proportional, minimal)
      - Bei Rang > 4: zusätzliche Rest-Kapazität wird verteilt
      - Material wird reserviert: stock_by_saddle_type[saddle] -= scheduled_qty
   
   Output:
   - scheduled_production[product] = geplante Menge (vor Material-Check)

4. MATERIAL-CAPPING (qty_to_book)
   ↓
   calculate_production_logs() → Zeile 413
   qty_to_book = min(scheduled_production[product], running_stock[saddle])
   → Tatsächliche PM kann NICHT höher sein als verfügbares Material!

5. VERBUCHUNG
   ↓
   - running_stock[saddle] -= qty_to_book  (Material wird verbraucht)
   - df.at[idx, 'tatsächliche PM'] = qty_to_book  (wird gespeichert)
   - df.at[idx, 'material_verbrauch'] = qty_to_book  (für Materiallager)

6. MATERIALVERBRAUCH → MATERIALAGER
   ↓
   calculate_material_inventory()
   → Liest 'material_verbrauch' oder 'tatsächliche PM' aus production_logs_cache
   → Summiert pro Tag und Sattel-Typ
   → Berechnet Materiallager-Bestand
```

### Warum weicht tatsächliche PM vom geplanten Bedarf ab?

**Beispiel: Geplanter Bedarf = 529 (Allrounder), Tatsächliche PM = 765**

**Ursachen:**

1. **Backlog-Abbau:**
   - Wenn am Vortag Backlog vorhanden war, wird zusätzlich produziert
   - `production_demand = todays_demand + backlog`
   - Beispiel: 529 (heute) + 236 (Backlog) = 765 Gesamtbedarf

2. **Ranglogik:**
   - Produkte mit höherem Rang werden bevorzugt produziert
   - Wenn Allrounder Rang 1 hat und mehr Material verfügbar ist, wird mehr produziert

3. **Materialverfügbarkeit:**
   - `qty_to_book = min(scheduled_production, running_stock)`
   - Wenn mehr Material verfügbar ist als geplant, kann mehr produziert werden
   - ABER: Wenn weniger Material verfügbar ist, wird weniger produziert

4. **Kapazitätsverteilung:**
   - Rest-Kapazität wird nach Rang verteilt
   - Produkte mit Rang > 4 können zusätzliche Kapazität bekommen

---

## 🏗️ Implementierungsplan

### Phase 1: UI-Komponente (Datum-Auswahl)

**Datei:** `pages/6_produktion.py`

**Änderungen:**
1. **Datum-Auswahl oben einfügen** (nach Titel, vor Tabellen)
   ```python
   # Datum-Auswahl für Materialverbrauch-Analyse
   col1, col2 = st.columns([1, 3])
   with col1:
       selected_date = st.date_input(
           "📅 Materialverbrauch analysieren für:",
           value=date(planning_year, 1, 1),
           min_value=date(planning_year, 1, 1),
           max_value=date(planning_year, 12, 31),
           key="material_consumption_date"
       )
   ```

2. **Bedingte Anzeige:**
   - Nur anzeigen wenn `production_logs_cache` verfügbar ist
   - Nur anzeigen wenn Datum ein Arbeitstag ist (optional)

**Performance:**
- Keine zusätzlichen Berechnungen
- Nur UI-Rendering
- Kein Cache-Impact

---

### Phase 2: Datenaggregation (Materialverbrauch pro Datum)

**Datei:** `ui/production_calculations.py` (NEUE Funktion)

**Neue Funktion:**
```python
def get_material_consumption_by_date(
    selected_date: date,
    production_logs_cache: Dict[str, pd.DataFrame],
    planning_year: int
) -> pd.DataFrame:
    """
    Aggregiert Materialverbrauch pro Produkt für ein bestimmtes Datum.
    
    Returns:
        DataFrame mit Spalten:
        - Produkt
        - Material-Typ (Sattel)
        - Geplante PM
        - Tatsächliche PM
        - Materialverbrauch
        - Abweichung (Tatsächliche - Geplante)
        - Materialverfügbarkeit (morgens)
    """
```

**Logik:**
1. Iteriere durch alle Produkte in `production_logs_cache`
2. Für jedes Produkt:
   - Finde Zeile für `selected_date`
   - Extrahiere: geplante PM, tatsächliche PM, material_verbrauch, Material-Typ (aus BOM)
3. Erstelle DataFrame mit aggregierten Daten
4. Berechne Abweichungen

**Performance:**
- Wird nur bei Datum-Änderung aufgerufen
- Keine Schleifen über alle 365 Tage
- O(Anzahl Produkte) = O(8) = konstant

**Caching:**
- Optional: Cache pro Datum (aber nicht notwendig, da sehr schnell)

---

### Phase 3: UI-Anzeige (Tabelle/Visualisierung)

**Datei:** `pages/6_produktion.py`

**Anzeige-Optionen:**

**Option A: Kompakte Tabelle (empfohlen)**
```python
if selected_date:
    consumption_df = get_material_consumption_by_date(
        selected_date, production_logs_cache, planning_year
    )
    
    if not consumption_df.empty:
        st.subheader(f"📊 Materialverbrauch am {selected_date.strftime('%d.%m.%Y')}")
        
        # Gruppiere nach Material-Typ
        for saddle_type in consumption_df['Material-Typ'].unique():
            st.markdown(f"**{saddle_type}:**")
            saddle_df = consumption_df[consumption_df['Material-Typ'] == saddle_type]
            
            # Zeige Tabelle
            st.dataframe(
                saddle_df[['Produkt', 'Geplante PM', 'Tatsächliche PM', 
                          'Materialverbrauch', 'Abweichung']],
                use_container_width=True,
                hide_index=True
            )
            
            # Summe
            total_consumption = saddle_df['Materialverbrauch'].sum()
            st.markdown(f"**Gesamtverbrauch {saddle_type}: {total_consumption}**")
```

**Option B: Erweiterte Visualisierung**
- Charts für Abweichungen
- Vergleich mit Materialverfügbarkeit
- Backlog-Information

**Performance:**
- Nur Rendering, keine Berechnungen
- Tabelle wird nur bei Datum-Änderung neu gerendert

---

### Phase 4: Integration & Testing

**Integration:**
1. Funktion in `ui/production_calculations.py` hinzufügen
2. UI-Komponente in `pages/6_produktion.py` einfügen
3. Import-Statements aktualisieren

**Testing:**
1. Test mit verschiedenen Daten
2. Test mit Materialmangel-Szenarien
3. Test mit Backlog-Szenarien
4. Performance-Test (sollte < 100ms sein)

**Edge Cases:**
- Datum ohne Produktion (Wochenende/Feiertag)
- Datum ohne Materialverbrauch
- Datum mit mehreren Produkten gleichen Materials

---

## ⚠️ Wichtige Hinweise

### Performance:
- ✅ Keine zusätzlichen Schleifen über alle 365 Tage
- ✅ Berechnung nur bei Datum-Änderung
- ✅ Keine Cache-Invalidierung notwendig
- ✅ Nutzt bereits vorhandene `production_logs_cache`

### Bestehende Logiken:
- ✅ Überschreibt KEINE bestehenden Berechnungen
- ✅ Nutzt nur bereits berechnete Daten (`production_logs_cache`)
- ✅ Keine Änderungen an `calculate_production_logs()`
- ✅ Keine Änderungen an `_recalculate_all_products_with_rank_logic()`

### Datenkonsistenz:
- ✅ Nutzt dieselben Daten wie Materiallager (`material_verbrauch` oder `tatsächliche PM`)
- ✅ Konsistent mit bestehenden Anzeigen
- ✅ Keine neuen Berechnungslogiken

---

## 📝 Code-Struktur

```
pages/6_produktion.py
├── [Bestehender Code]
├── [NEU] Datum-Auswahl (Zeile ~50)
├── [NEU] Materialverbrauch-Anzeige (Zeile ~60)
└── [Bestehender Code - Tabellen]

ui/production_calculations.py
├── [Bestehender Code]
└── [NEU] get_material_consumption_by_date() (am Ende)
```

---

## 🎯 Erfolgskriterien

1. ✅ Datum kann ausgewählt werden
2. ✅ Materialverbrauch wird korrekt angezeigt
3. ✅ Abweichungen sind nachvollziehbar
4. ✅ Performance < 100ms
5. ✅ Keine Regressionen in bestehenden Features
6. ✅ Code ist wartbar und dokumentiert

---

## 📅 Zeitplan

- **Phase 1 (UI):** 30 Minuten
- **Phase 2 (Datenaggregation):** 60 Minuten
- **Phase 3 (Anzeige):** 45 Minuten
- **Phase 4 (Integration & Testing):** 45 Minuten

**Gesamt:** ~3 Stunden

---

## 🔄 Alternative: Einfacheres Feature

Falls das Feature zu komplex ist, kann auch eine einfachere Version implementiert werden:

**Einfache Version:**
- Nur Tabelle mit: Produkt | Material-Typ | Tatsächliche PM | Materialverbrauch
- Keine Abweichungen, keine Gruppierung
- ~1 Stunde Implementierung

**Erweiterte Version (später):**
- Charts, Vergleich, Backlog-Information
- ~2 zusätzliche Stunden
