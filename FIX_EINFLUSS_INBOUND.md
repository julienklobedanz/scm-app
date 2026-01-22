# Einfluss des empfohlenen Fixes auf Inbound-Tabelle

**Datum:** 2026-01-22  
**Fix:** Vereinfachte Warenausgang-Berechnung in `get_supplier_log_dataframe()`

---

## 🔍 Aktuelle Architektur

### 1. Datenquellen

**Beide Tabellen (Supplier-Log und Inbound-Log) verwenden:**
- **Gemeinsame Datenquelle:** `self.transport_status` (Dict mit Bestellungen und Produktionsdaten)
- **Gemeinsame Pool-Logik:** Beide berechnen Versandmengen mit identischer Logik

### 2. Supplier-Log (`get_supplier_log_dataframe`)

**Ablauf:**
1. **Pool-Logik** (Zeilen 671-714):
   - Berechnet geplante Versandmenge: `shipment_results[day_idx]`
   - Basierend auf: Tägliche Produktion + Carry-Over
   - Verteilung proportional nach Shares

2. **Bestandslogik** (Zeilen 747-784):
   - Berechnet Warenbestand: `current_stock = previous_stock + production_qty`
   - **Begrenzt Warenausgang:** `shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)`
   - **Problem:** Wenn `current_stock - cumulative_shipped < planned_shipment_qty`, wird weniger verschickt als geplant

**Ergebnis:** Warenausgang kann kleiner sein als geplante Versandmenge

### 3. Inbound-Log (`get_inbound_log_dataframe`)

**Ablauf:**
1. **Produktion sammeln** (Zeilen 862-879):
   - Liest aus `transport_status`: `qty_produced = status.get('actual_quantity', ...)`
   - Verteilt Produktion in Sattel-Eimer: `daily_prod_all[effective_day][s] += qty_produced * s_share`

2. **Pool-Logik** (Zeilen 906-963):
   - **GLEICHE Logik** wie Supplier-Log
   - Berechnet Versandmenge: `shipments_today[s]` (proportional nach Shares)
   - **KEINE Bestandsbegrenzung** - verwendet die volle geplante Versandmenge

3. **Inbound-Tabelle füllen** (Zeilen 994-1004):
   - Verwendet `shipments_today[s]` direkt
   - **Keine Prüfung auf verfügbaren Bestand**

**Ergebnis:** Inbound zeigt die volle geplante Versandmenge (ohne Bestandsbegrenzung)

---

## ⚠️ Aktuelles Problem: Inkonsistenz

### Problem 1: Unterschiedliche Versandmengen

**Supplier-Log:**
- Warenausgang: **95.723** (begrenzt durch Bestand)
- Geplante Versandmenge: **99.630** (aus Pool-Logik)
- Differenz: **3.907** (bleibt im Bestand)

**Inbound-Log:**
- Versandmenge: **99.630** (volle geplante Menge, keine Begrenzung)
- **Inkonsistenz:** Inbound zeigt mehr als Supplier-Log verschickt hat

### Problem 2: Massenerhaltung verletzt

**Aktuell:**
- Supplier-Log: Produziert 99.900, verschickt 95.723 → **4.177 bleiben**
- Inbound-Log: Erwartet 99.630 → **Aber nur 95.723 wurden wirklich verschickt**
- **Differenz:** 3.907 Stück "fehlen" in Inbound (oder werden doppelt gezählt)

---

## 🔧 Einfluss des empfohlenen Fixes

### Fix: Vereinfachte Bestandslogik

```python
# VORHER (aktuell):
current_stock = previous_stock + production_qty
if current_stock - cumulative_shipped >= 0:
    shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)
else:
    shipment_qty = min(planned_shipment_qty, current_stock)
cumulative_shipped += shipment_qty
current_stock = current_stock - shipment_qty

# NACHHER (Fix):
current_stock = previous_stock + production_qty
shipment_qty = min(planned_shipment_qty, current_stock)
current_stock = current_stock - shipment_qty
```

### Einfluss auf Supplier-Log

**✅ Positiv:**
- Warenausgang wird konsistent mit Pool-Logik berechnet
- Keine komplexe `cumulative_shipped`-Prüfung mehr
- Sollte die 4.177 Differenz beheben

**Erwartetes Ergebnis:**
- Warenausgang: **99.630** (gleich geplanter Versandmenge)
- Warenbestand (Ende): **270** (99.900 - 99.630 = 270, durch Rundungsfehler)

### Einfluss auf Inbound-Log

**✅ KEIN direkter Einfluss:**
- Inbound-Log verwendet **eigene Pool-Logik** (unabhängig von Supplier-Log)
- Berechnet Versandmengen direkt aus `transport_status` und Pool-Logik
- **NICHT abhängig** von `shipment_qty` aus Supplier-Log

**ABER: Konsistenz wird hergestellt:**
- Beide Tabellen verwenden jetzt die **gleiche Logik** (ohne Bestandsbegrenzung)
- Supplier-Log: Warenausgang = geplante Versandmenge
- Inbound-Log: Versandmenge = geplante Versandmenge
- **Konsistenz:** Beide zeigen jetzt die gleichen Versandmengen

---

## 📊 Erwartete Änderungen nach Fix

### Vorher (aktuell)

| Metrik | Supplier-Log | Inbound-Log | Differenz |
|--------|--------------|-------------|-----------|
| Produktionsmenge | 99.900 | 99.900 | 0 |
| Geplante Versandmenge | 99.630 | 99.630 | 0 |
| Tatsächliche Versandmenge | 95.723 | 99.630 | **-3.907** |
| Verbleibender Bestand | 4.177 | - | - |

### Nachher (mit Fix)

| Metrik | Supplier-Log | Inbound-Log | Differenz |
|--------|--------------|-------------|-----------|
| Produktionsmenge | 99.900 | 99.900 | 0 |
| Geplante Versandmenge | 99.630 | 99.630 | 0 |
| Tatsächliche Versandmenge | **99.630** | 99.630 | **0** ✅ |
| Verbleibender Bestand | **270** | - | - |

**Hinweis:** Die 270 Differenz (99.900 - 99.630) entsteht durch:
- Rundungsfehler in der Largest Remainder Method
- Timing-Unterschiede zwischen Produktion und Versand

---

## ⚠️ Potenzielle Probleme nach Fix

### Problem 1: Negativer Warenbestand möglich?

**Aktuell:**
- Bestandsbegrenzung verhindert negativen Bestand
- `shipment_qty = min(planned_shipment_qty, current_stock - cumulative_shipped)`

**Nach Fix:**
- `shipment_qty = min(planned_shipment_qty, current_stock)`
- **Schutz bleibt:** `min()` verhindert negativen Bestand
- **ABER:** Wenn `planned_shipment_qty > current_stock`, wird weniger verschickt als geplant

**Lösung:** Das ist korrekt - man kann nicht mehr verschicken als vorhanden ist.

### Problem 2: Timing-Probleme

**Szenario:**
- Tag 1: Produktion = 200, Bestand = 0 → `current_stock = 200`
- Tag 1: Geplante Versandmenge = 500 → `shipment_qty = min(500, 200) = 200`
- **Problem:** Pool-Logik plant 500, aber nur 200 werden verschickt

**Ursache:** Pool-Logik berücksichtigt Carry-Over, aber Bestand berücksichtigt nur aktuelle Produktion.

**Lösung:** Pool-Logik sollte bereits korrekt sein (berücksichtigt Carry-Over). Der Fix stellt sicher, dass der Versand nicht größer ist als der verfügbare Bestand.

### Problem 3: Materiallager-Berechnung

**Aktuell:**
- Materiallager liest aus Inbound-Tabelle: `get_inbound_log_dataframe()`
- Verwendet `row.get(saddle_name, 0)` für Bestandsberechnung
- **Abhängig von:** Inbound-Tabelle-Mengen

**Nach Fix:**
- Inbound-Tabelle ändert sich **NICHT** (verwendet eigene Pool-Logik)
- Materiallager-Berechnung bleibt **unverändert**
- **KEIN Einfluss** auf Materiallager

---

## ✅ Zusammenfassung: Einfluss des Fixes

### Direkter Einfluss

1. **Supplier-Log (`get_supplier_log_dataframe`):**
   - ✅ Warenausgang wird konsistent mit Pool-Logik berechnet
   - ✅ 4.177 Differenz wird behoben
   - ✅ Warenbestand wird korrekt berechnet

2. **Inbound-Log (`get_inbound_log_dataframe`):**
   - ✅ **KEIN direkter Einfluss** (verwendet eigene Pool-Logik)
   - ✅ **Konsistenz wird hergestellt** (beide zeigen gleiche Versandmengen)

### Indirekter Einfluss

1. **Materiallager:**
   - ✅ **KEIN Einfluss** (liest aus Inbound-Tabelle, die sich nicht ändert)

2. **Produktionsplaner:**
   - ✅ **KEIN Einfluss** (liest aus Inbound-Tabelle für Materialbestände)

3. **Simulator:**
   - ✅ **KEIN Einfluss** (verwendet `transport_status` direkt)

### Erwartete Verbesserungen

1. **Konsistenz:**
   - Supplier-Log und Inbound-Log zeigen jetzt **gleiche Versandmengen**
   - Massenerhaltung wird **respektiert**

2. **Korrektheit:**
   - Warenbestand wird **korrekt berechnet**
   - Keine "verlorenen" 4.177 Stück mehr

3. **Einfachheit:**
   - Code wird **einfacher und verständlicher**
   - Keine komplexe `cumulative_shipped`-Logik mehr

---

## 🎯 Fazit

**Der empfohlene Fix hat KEINEN negativen Einfluss auf die Inbound-Tabelle.**

**Vorteile:**
- ✅ Konsistenz zwischen Supplier-Log und Inbound-Log
- ✅ Korrekte Warenbestandsberechnung
- ✅ Einfacherer Code

**Risiken:**
- ⚠️ Minimal: Timing-Probleme möglich (aber bereits durch `min()` abgefangen)
- ⚠️ Minimal: Rundungsfehler können zu kleinen Bestandsdifferenzen führen (erwartet)

**Empfehlung:** Fix implementieren - die Vorteile überwiegen deutlich.
