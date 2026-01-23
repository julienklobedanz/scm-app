# Analyse: Warum Marketing-Szenarien keine Auswirkung auf Inbound-Tabelle haben

**Datum:** 2026-01-23  
**Problem:** Marketing-Szenarien haben keine Auswirkung auf die Inbound-Tabelle  
**Vermutung:** Isolierte Berechnungen, die nicht von vorherigen Schritten abhängen

---

## 📊 Datenfluss-Analyse: Inbound-Tabelle

### **1. Datenquelle: `transport_status`**

Die Inbound-Tabelle (`get_inbound_log_dataframe()`) liest ihre Daten aus **`self.transport_status`**:

```python
# Zeilen 917-934 in simulation/china_transport.py
for (o_day, o_id), status in self.transport_status.items():
    p_day_sim = status.get('production_end_day')
    qty_produced = status.get('actual_quantity', status.get('quantity', 0.0))
    
    if p_day_sim is not None and qty_produced > 0:
        # Verteilt Produktion in Sattel-Eimer
        daily_prod_all[effective_day][s] += qty_produced * s_share
```

**Wichtig:** Die Inbound-Tabelle liest **direkt** aus `transport_status`, nicht aus `daily_demands_actual`.

---

### **2. Wie wird `transport_status` befüllt?**

`transport_status` wird während der **Simulation** befüllt:

1. **ProcurementManager** (`simulation/procurement_manager.py`, Zeilen 59-115):
   ```python
   def check_and_order(self, day: int, expected_demand: float = None):
       # expected_demand kommt vom Simulator
       if expected_demand is not None and expected_demand > 0:
           self.china_transport_manager.place_order(day, expected_demand)
   ```

2. **Simulator** (`simulation/simulator.py`):
   - Berechnet `expected_demand` aus `daily_demands_actual` (mit Marketing)
   - Ruft `procurement_manager.check_and_order(day, expected_demand)` auf

3. **ChinaTransportManager.place_order()** (`simulation/china_transport.py`, Zeilen 54-138):
   - Speichert Bestellung in `transport_status`
   - `quantity` = `expected_demand` (aus Simulator, mit Marketing bereits enthalten)

**Ergebnis:** `transport_status` enthält Bestellungen, die **während der Simulation** erstellt wurden, basierend auf `daily_demands_actual` (mit Marketing).

---

### **3. Das Problem: Simulation wird nicht neu gestartet**

**Aktueller Ablauf:**

1. **App-Start:**
   - `run_happy_path_simulation()` wird aufgerufen
   - Simulation läuft mit `daily_demands_actual` (ohne Marketing, da noch kein Marketing aktiv)
   - `transport_status` wird befüllt mit Bestellungen **ohne Marketing**

2. **Marketing-Szenario wird hinzugefügt:**
   - `st.rerun()` wird aufgerufen
   - `calculate_volume_planning_demand()` wird aufgerufen → `daily_demands_actual` wird **neu berechnet** (mit Marketing)
   - **ABER:** `run_happy_path_simulation()` prüft, ob Simulation bereits gelaufen ist → **keine neue Simulation**
   - `transport_status` bleibt **unverändert** (alte Bestellungen ohne Marketing)

3. **Inbound-Tabelle wird angezeigt:**
   - `get_inbound_log_dataframe()` liest aus `transport_status`
   - `transport_status` enthält noch die **alten Bestellungen** (ohne Marketing)
   - **Ergebnis:** Marketing hat keine Auswirkung

---

### **4. Zusätzliches Problem: Cache in `get_inbound_log_dataframe()`**

Die Inbound-Tabelle hat auch einen **Cache**, der nicht invalidiert wird:

```python
# Zeilen 881-884 in simulation/china_transport.py
cache_key = tuple(sorted(saddle_shares_dict.items()))
if cache_key == self._inbound_df_cache_key and cache_key in self._inbound_df_cache:
    return self._inbound_df_cache[cache_key]
```

**Problem:**
- Cache-Key berücksichtigt nur `saddle_shares_dict`
- **NICHT** berücksichtigt: Szenarien, `daily_demands_actual`, `transport_status`-Änderungen
- Wenn Marketing hinzugefügt wird, wird Cache **nicht invalidiert**

---

### **5. Pool-Logik: Berechnet Versandmengen NEU**

Die Inbound-Tabelle berechnet Versandmengen **neu** mit Pool-Logik (Zeilen 984-1018):

```python
# Pool-Logik: Berechnet Versandmengen aus Produktion
for s in all_saddles:
    prod = daily_prod_all[day_idx][s]  # Produktion aus transport_status
    co = carry_over[s]
    acc = prod + co
    accumulated_by_saddle[s] = acc
    total_accumulated += acc

# Wenn Pool >= 500, wird verschifft
if total_accumulated >= lot_size:
    # Verteilung proportional nach Shares
    shipments_today = rounded  # Berechnet NEU
```

**Problem:**
- Pool-Logik verwendet Produktion aus `transport_status`
- Wenn `transport_status` alte Werte hat (ohne Marketing), dann hat Pool-Logik auch alte Werte
- Marketing hat keine Auswirkung, weil die **Datenquelle** (`transport_status`) nicht aktualisiert wurde

---

## 🔍 Zusammenfassung: Warum Marketing keine Auswirkung hat

### **Hauptproblem: Simulation wird nicht neu gestartet**

1. **Simulation läuft einmal** (beim App-Start, ohne Marketing)
2. **`transport_status` wird befüllt** (mit Bestellungen ohne Marketing)
3. **Marketing wird hinzugefügt** → `daily_demands_actual` wird neu berechnet
4. **ABER:** Simulation wird **nicht neu gestartet** → `transport_status` bleibt unverändert
5. **Inbound-Tabelle liest aus `transport_status`** → sieht alte Werte (ohne Marketing)

### **Zusätzliches Problem: Cache**

- Cache in `get_inbound_log_dataframe()` wird nicht invalidiert
- Cache-Key berücksichtigt keine Szenarien oder `transport_status`-Änderungen

### **Isolierte Berechnungen?**

**Nein, nicht wirklich isoliert:**
- Inbound-Tabelle liest aus `transport_status` (korrekt)
- `transport_status` wird während Simulation befüllt (korrekt)
- **Problem:** Simulation wird nicht neu gestartet, wenn Marketing hinzugefügt wird

---

## 💡 Lösungsansätze

### **Option 1: Simulation neu starten bei Szenario-Änderungen**

**Prinzip:** Wenn Marketing hinzugefügt wird, Simulation automatisch neu starten.

**Umsetzung:**
- In `ui/scenario_sidebar.py`: Wenn Szenario hinzugefügt wird, setze `st.session_state.run_simulation = True`
- In `run_happy_path_simulation()`: Prüfe, ob Szenarien sich geändert haben → starte Simulation neu

**Vorteile:**
- ✅ `transport_status` wird mit neuen Bestellungen (mit Marketing) befüllt
- ✅ Inbound-Tabelle sieht korrekte Werte
- ✅ Konsistenz: Alle Tabellen sehen gleiche Daten

**Nachteile:**
- ⚠️ Simulation dauert ~60 Sekunden (Performance-Problem)
- ⚠️ Benutzer muss warten

---

### **Option 2: Cache-Invalidierung + Explizite Neubewertung**

**Prinzip:** Cache invalidiert, aber Simulation wird nicht neu gestartet. Stattdessen: Inbound-Tabelle berechnet Versandmengen aus aktualisierten `daily_demands_actual`.

**Problem:** Inbound-Tabelle kann nicht einfach `daily_demands_actual` verwenden, weil:
- Sie zeigt **tatsächliche Versandmengen** (nicht geplante Nachfrage)
- Versandmengen hängen von **Produktion** ab (nicht direkt von Nachfrage)
- Produktion kommt aus `transport_status` (wurde während Simulation erstellt)

**Fazit:** Diese Option funktioniert **nicht**, weil Inbound-Tabelle auf `transport_status` angewiesen ist.

---

### **Option 3: Hybrid-Ansatz (Empfohlen)**

**Prinzip:** 
1. Cache-Key erweitern (um Szenarien und `transport_status`-Fingerprint)
2. Wenn Cache-Miss: Prüfe, ob Simulation neu gestartet werden muss
3. Optional: Warnung anzeigen, wenn `transport_status` veraltet ist

**Umsetzung:**
- Cache-Key in `get_inbound_log_dataframe()` erweitern (ähnlich wie bei Supplier-Log)
- Prüfe, ob `transport_status` mit aktuellen Szenarien konsistent ist
- Wenn nicht: Zeige Warnung "Simulation muss neu gestartet werden"

**Vorteile:**
- ✅ Cache wird korrekt invalidiert
- ✅ Benutzer wird informiert, wenn Simulation neu gestartet werden muss
- ✅ Keine automatische Neustartung (Performance)

**Nachteile:**
- ⚠️ Benutzer muss manuell Simulation neu starten

---

## 📋 Detaillierte Analyse: Datenquellen

### **Was liest die Inbound-Tabelle?**

| Datenquelle | Verwendet für | Enthält Marketing? | Problem |
|-------------|---------------|-------------------|---------|
| **`transport_status`** | Produktion (`actual_quantity`) | ❌ Nein (wurde während Simulation ohne Marketing erstellt) | ❌ **Hauptproblem** |
| **Pool-Logik** | Versandmengen (berechnet NEU) | ❌ Nein (basiert auf `transport_status`) | ❌ Abhängig von `transport_status` |
| **`daily_demands_actual`** | ❌ Wird **NICHT** verwendet | ✅ Ja (wird neu berechnet) | ⚠️ Wird nicht verwendet |

---

### **Warum wird `daily_demands_actual` nicht verwendet?**

Die Inbound-Tabelle zeigt **tatsächliche Versandmengen**, nicht geplante Nachfrage:
- **Nachfrage** (`daily_demands_actual`) = Was wird benötigt
- **Produktion** (`transport_status`) = Was wurde produziert
- **Versand** (Pool-Logik) = Was wurde verschifft

**Problem:** Wenn `transport_status` alte Werte hat (ohne Marketing), dann zeigt Inbound-Tabelle auch alte Versandmengen.

---

## 🎯 Fazit

### **Hauptproblem:**

Die Inbound-Tabelle ist **nicht isoliert** von vorherigen Schritten, sondern **abhängig** von `transport_status`, das während der Simulation erstellt wurde. Wenn Marketing hinzugefügt wird:

1. ✅ `daily_demands_actual` wird neu berechnet (mit Marketing)
2. ❌ Simulation wird **nicht** neu gestartet
3. ❌ `transport_status` bleibt **unverändert** (alte Bestellungen ohne Marketing)
4. ❌ Inbound-Tabelle liest aus `transport_status` → sieht alte Werte

### **Lösung:**

**Option 1 (Empfohlen):** Simulation automatisch neu starten, wenn Marketing-Szenarien hinzugefügt werden.

**Option 2:** Cache-Key erweitern + Warnung anzeigen, wenn Simulation neu gestartet werden muss.

---

**Die vollständige Analyse wurde in `INBOUND_MARKETING_ANALYSE.md` gespeichert.**
