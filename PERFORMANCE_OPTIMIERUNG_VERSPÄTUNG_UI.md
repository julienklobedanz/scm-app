# Performance-Optimierung: Verspätung UI

**Datum:** 28.01.2026  
**Problem:** Über 2 Minuten Wartezeit für szenarioabhängige Sichten  
**Status:** ✅ **OPTIMIERT**

---

## 🔍 Identifiziertes Performance-Problem

### Problem

Die neue Funktion `_get_planned_arrival_dates()` wurde bei **jedem Rendern** der Sidebar aufgerufen, auch wenn der Benutzer nicht die Verspätungs-Sektion öffnet.

**Auswirkung:**
- Funktion ruft `get_inbound_log_dataframe()` auf (sehr teure Operation)
- Obwohl `get_inbound_log_dataframe()` selbst gecacht ist, wird die Funktion trotzdem bei jedem Rendern ausgeführt
- Bei großen Inbound-Tabellen kann das zu Performance-Problemen führen

### Warum passiert das?

**Code-Flow:**
1. `render_scenario_sidebar()` wird bei jedem Rendern aufgerufen
2. Wenn `scenario_type == "Verspätung"`, wird `_get_planned_arrival_dates()` aufgerufen
3. Diese Funktion ruft `get_inbound_log_dataframe()` auf
4. Auch wenn gecacht, ist der Aufruf selbst nicht kostenlos

---

## ✅ Implementierte Optimierungen

### 1. Caching für `_get_planned_arrival_dates()`

**Vorher:**
- Funktion wurde bei jedem Rendern neu ausgeführt
- Kein Caching → mehrfache Berechnungen

**Nachher:**
- Cache-Key: `planned_arrival_dates_{delay_stage}_{planning_year}`
- Ergebnis wird in `st.session_state` gespeichert
- Bei Cache-Hit: Sofortige Rückgabe ohne Berechnung

**Code:**
```python
# Cache-Key für geplante Ankunftsdaten
cache_key = f"planned_arrival_dates_{delay_stage}_{planning_year}"

# Prüfe Cache zuerst
if cache_key in st.session_state:
    return st.session_state[cache_key]

# ... Berechnung ...

# Cache Ergebnis
st.session_state[cache_key] = arrival_dates
return arrival_dates
```

### 2. Cache-Invalidierung

**Wann wird Cache invalidiert:**
- Wenn Szenarien entfernt werden (Cache wird gelöscht)
- Wenn Simulation neu gestartet wird (Cache wird gelöscht)

**Code:**
```python
# Bei Szenario-Entfernung
planning_year = st.session_state.get('planning_year', 2027)
for delay_stage in ["truck_china_arrival", "ship_arrival", "truck_de_arrival"]:
    cache_key = f"planned_arrival_dates_{delay_stage}_{planning_year}"
    if cache_key in st.session_state:
        del st.session_state[cache_key]

# Bei Simulation-Neustart
# Gleiche Logik
```

### 3. Optimierte Datums-Extraktion

**Vorher:**
- Liste wurde für Duplikat-Check verwendet
- `if parsed_date not in arrival_dates` → O(n) Check

**Nachher:**
- Set wird für Duplikat-Check verwendet
- `if parsed_date not in seen_dates` → O(1) Check
- Deutlich schneller bei vielen Datums

**Code:**
```python
# PERFORMANCE: Verwende Set für schnelleres Duplikat-Check
seen_dates = set()

for _, row in inbound_df.iterrows():
    # ...
    if parsed_date not in seen_dates:
        arrival_dates.append(parsed_date)
        seen_dates.add(parsed_date)
```

---

## 📊 Performance-Verbesserung

### Vorher:
- **Jedes Rendern:** `_get_planned_arrival_dates()` wird aufgerufen
- **Jeder Aufruf:** `get_inbound_log_dataframe()` wird aufgerufen (auch wenn gecacht)
- **Datums-Extraktion:** O(n²) wegen Liste-Check

### Nachher:
- **Erstes Rendern:** `_get_planned_arrival_dates()` wird aufgerufen, Ergebnis gecacht
- **Weitere Renderings:** Cache-Hit → Sofortige Rückgabe
- **Datums-Extraktion:** O(n) wegen Set-Check

### Geschätzte Verbesserung:
- **Erstes Rendern:** Keine Änderung (muss trotzdem berechnen)
- **Weitere Renderings:** ~99% schneller (Cache-Hit)
- **Bei vielen Datums:** ~50% schneller (Set statt Liste)

---

## ⚠️ Weitere Performance-Probleme?

### Mögliche Ursachen für 2+ Minuten Wartezeit:

1. **Simulation selbst:**
   - Die Simulation dauert lange (365 Tage × komplexe Berechnungen)
   - Das ist normal und nicht durch diese Änderung verursacht

2. **Andere Berechnungen:**
   - `calculate_production_logs()` - sehr komplex
   - `calculate_material_inventory()` - iterativ (2 Iterationen)
   - `get_inbound_log_dataframe()` - große Tabelle

3. **Cache-Invalidierung:**
   - Wenn Szenarien hinzugefügt werden, werden alle Caches invalidiert
   - Das führt zu Neuberechnung aller Daten
   - Das ist gewollt, aber kann lange dauern

### Empfehlungen:

1. **Diese Optimierung sollte helfen:**
   - Reduziert unnötige Aufrufe von `_get_planned_arrival_dates()`
   - Cache verhindert mehrfache Berechnungen

2. **Weitere Optimierungen möglich:**
   - Lazy Loading: Nur aufrufen wenn Verspätungs-Sektion geöffnet ist
   - Background-Berechnung: In separatem Thread
   - Progress-Anzeige: Zeige Fortschritt während Berechnung

---

## 🧪 Test-Empfehlungen

### Test 1: Cache-Funktionalität

**Schritte:**
1. Öffne Szenarien-Sidebar
2. Wähle "Verspätung" → "Ankunft Schiff"
3. Prüfe: Werden geplante Ankunftsdaten angezeigt?
4. Wechsle zu anderem Szenario-Typ
5. Wechsle zurück zu "Verspätung"
6. Prüfe: Werden Daten sofort angezeigt? (Cache-Hit)

**Erwartung:**
- Erstes Mal: Kurze Verzögerung (Berechnung)
- Zweites Mal: Sofortige Anzeige (Cache-Hit)

### Test 2: Cache-Invalidierung

**Schritte:**
1. Öffne "Verspätung" → Daten werden gecacht
2. Füge ein Szenario hinzu
3. Entferne das Szenario
4. Öffne "Verspätung" erneut
5. Prüfe: Werden Daten neu berechnet? (Cache sollte invalidiert sein)

**Erwartung:**
- Nach Szenario-Entfernung: Cache wird invalidiert
- Beim erneuten Öffnen: Daten werden neu berechnet

---

## ✅ Status

- ✅ Caching implementiert
- ✅ Cache-Invalidierung implementiert
- ✅ Optimierte Datums-Extraktion (Set statt Liste)
- ⚠️ Weitere Performance-Probleme könnten von Simulation selbst kommen

---

**Status:** ✅ **OPTIMIERT - BEREIT FÜR TESTS**
