# Ranglogik und Proportionalität - Detaillierte Erklärung

**Datum:** 28.01.2026  
**Zweck:** Vollständige Erklärung der Produktionsplanungs-Logik

---

## 📊 Übersicht

Die Produktionsplanung verwendet ein **zweistufiges System**:
1. **Proportionalität:** Berechnet den anteiligen Produktionsanteil jedes Produkts basierend auf seinem Bedarf
2. **Ranglogik:** Bestimmt die Priorität jedes Produkts und wie Restkapazität verteilt wird

---

## 1️⃣ Proportionalität (Anteilige Produktion)

### Formel

```python
proportional = ABRUNDEN(Produktionsbedarf * Tageskapazität / Gesamtbedarf)
```

### Beispiel

**Annahme:**
- Tageskapazität: 1,040 Einheiten
- Gesamtbedarf (alle Produkte): 2,000 Einheiten
- MTB Allrounder Bedarf: 500 Einheiten
- MTB Performance Bedarf: 300 Einheiten

**Berechnung:**
- **MTB Allrounder:** `ABRUNDEN(500 * 1040 / 2000) = ABRUNDEN(260) = 260`
- **MTB Performance:** `ABRUNDEN(300 * 1040 / 2000) = ABRUNDEN(156) = 156`

**Ergebnis:**
- Jedes Produkt erhält einen **anteiligen Anteil** der Tageskapazität
- Die Summe aller proportionalen Werte kann **kleiner** als die Tageskapazität sein (wegen `ABRUNDEN`)
- **Restkapazität** = Tageskapazität - Summe aller proportionalen Werte

### Code-Stelle

**Datei:** `simulation/production_planner.py` (Zeilen 185-198)

```python
proportional_production_by_product = {}
for product in products_list:
    demand = production_demand_by_product.get(product, 0.0)
    if total_production_demand > 0:
        # ABRUNDEN(Produktionsbedarf * Kapazität / Gesamtbedarf; 0)
        proportional = math.floor(demand * daily_capacity / total_production_demand)
    else:
        proportional = 0
    proportional_production_by_product[product] = proportional
```

---

## 2️⃣ Ranglogik (Priorisierung)

### Schritt 1: Rang-Unterstützung berechnen

**Formel:**
```python
rank_support = Anteilige_Produktion + (Zeile / 1.000.000)
```

**Zeile:** Alphabetische Position des Produkts (1-8)

**Produktreihenfolge (alphabetisch):**
1. MTB Allrounder (Zeile = 1)
2. MTB Competition (Zeile = 2)
3. MTB Downhill (Zeile = 3)
4. MTB Extreme (Zeile = 4)
5. MTB Freeride (Zeile = 5)
6. MTB Marathon (Zeile = 6)
7. MTB Performance (Zeile = 7)
8. MTB Trail (Zeile = 8)

### Beispiel: Rang-Unterstützung

**Annahme:** Beide Produkte haben `proportional = 22`

- **MTB Freeride:**
  - `rank_support = 22 + (5 / 1.000.000) = 22.000005`
  
- **MTB Performance:**
  - `rank_support = 22 + (7 / 1.000.000) = 22.000007`

**Ergebnis:** Performance hat höheren `rank_support` → wird zuerst sortiert → **Rang 1**

### Schritt 2: Sortierung nach Rang-Unterstützung

**Code-Stelle:** `simulation/production_planner.py` (Zeilen 200-215)

```python
# Berechne Rang-Unterstützung
rank_support_by_product = {}
for idx, product in enumerate(products_list):
    row_number = idx + 1
    proportional = proportional_production_by_product.get(product, 0)
    # Rang_Unterstützung = Anteilige_Produktion + Zeile/1000000
    rank_support = (row_number / 1000000.0) + proportional
    rank_support_by_product[product] = rank_support

# Sortiere Produkte nach Rang (Höchster Support-Wert zuerst = Rang 1)
sorted_products = sorted(products_list, key=lambda p: rank_support_by_product[p], reverse=True)

# Berechne Rangnummer für Reporting
rank_by_product = {}
for i, p in enumerate(sorted_products):
    rank_by_product[p] = i + 1
```

**Ergebnis:**
- Produkte werden nach `rank_support` **absteigend** sortiert
- Höchster `rank_support` = **Rang 1** (höchste Priorität)
- Niedrigster `rank_support` = **Rang 8** (niedrigste Priorität)

---

## 3️⃣ Produktionsmengen-Berechnung

### Rang 1-4: Basis-Produktion

**Formel:**
```python
scheduled_qty = MIN(Produktionsbedarf, Anteilige_Produktion, Materiallimit)
```

**Erklärung:**
- Produkte mit **Rang 1-4** erhalten **nur** ihre anteilige Produktion
- **Keine** Restkapazität wird verwendet
- Materiallimit = Verfügbarer Sattel-Bestand

**Code-Stelle:** `simulation/production_planner.py` (Zeilen 246-248)

```python
if rank <= 4:
    scheduled_qty = min(demand, proportional, minimal)
```

### Rang 5-8: Basis + Rest-Verteilung

**Formel:**
```python
base_qty = MIN(Produktionsbedarf, Anteilige_Produktion, Materiallimit)
rest_production = MIN(Restkapazität, Materiallimit, Rest_Bedarf)
scheduled_qty = base_qty + rest_production
```

**Erklärung:**
- Produkte mit **Rang 5-8** erhalten ihre anteilige Produktion **PLUS** Restkapazität
- Restkapazität = Tageskapazität - Summe aller bereits geplanten Produktionen
- Restkapazität wird **nur** verwendet, wenn noch Kapazität verfügbar ist

**Code-Stelle:** `simulation/production_planner.py` (Zeilen 250-261)

```python
else:
    # Für Rang 5-8: MIN(Bedarf, Anteilige, Minimale) + Rest-Verteilung
    base_qty = min(demand, proportional, minimal)
    
    # Wenn Summe < Kapazität: MIN(Rest_Kapazität, Minimale, Rest_Bedarf), sonst 0
    remaining_capacity = daily_capacity - total_scheduled_so_far
    remaining_demand = max(0.0, demand - base_qty)
    
    if total_scheduled_so_far < daily_capacity and remaining_capacity > 0:
        rest_production = min(remaining_capacity, minimal, remaining_demand)
        scheduled_qty = base_qty + rest_production
    else:
        scheduled_qty = base_qty
```

---

## 4️⃣ Praktisches Beispiel

### Szenario

**Tageskapazität:** 1,040 Einheiten  
**Produktionsbedarf:**
- MTB Allrounder: 500
- MTB Competition: 400
- MTB Downhill: 300
- MTB Performance: 200
- **Gesamt:** 1,400

**Materiallimit:** Alle Sättel verfügbar (unbegrenzt)

### Schritt 1: Proportionalität berechnen

- **MTB Allrounder:** `ABRUNDEN(500 * 1040 / 1400) = 371`
- **MTB Competition:** `ABRUNDEN(400 * 1040 / 1400) = 297`
- **MTB Downhill:** `ABRUNDEN(300 * 1040 / 1400) = 222`
- **MTB Performance:** `ABRUNDEN(200 * 1040 / 1400) = 148`
- **Summe:** 371 + 297 + 222 + 148 = **1,038**
- **Restkapazität:** 1040 - 1038 = **2**

### Schritt 2: Rang-Unterstützung berechnen

- **MTB Allrounder:** `371 + (1 / 1.000.000) = 371.000001` → **Rang 1**
- **MTB Competition:** `297 + (2 / 1.000.000) = 297.000002` → **Rang 2**
- **MTB Downhill:** `222 + (3 / 1.000.000) = 222.000003` → **Rang 3**
- **MTB Performance:** `148 + (7 / 1.000.000) = 148.000007` → **Rang 4**

### Schritt 3: Produktionsmengen berechnen

**Rang 1 (MTB Allrounder):**
- `scheduled_qty = MIN(500, 371, ∞) = 371`
- `total_scheduled_so_far = 371`

**Rang 2 (MTB Competition):**
- `scheduled_qty = MIN(400, 297, ∞) = 297`
- `total_scheduled_so_far = 371 + 297 = 668`

**Rang 3 (MTB Downhill):**
- `scheduled_qty = MIN(300, 222, ∞) = 222`
- `total_scheduled_so_far = 668 + 222 = 890`

**Rang 4 (MTB Performance):**
- `base_qty = MIN(200, 148, ∞) = 148`
- `remaining_capacity = 1040 - 890 = 150`
- `remaining_demand = 200 - 148 = 52`
- `rest_production = MIN(150, ∞, 52) = 52`
- `scheduled_qty = 148 + 52 = 200`
- `total_scheduled_so_far = 890 + 200 = 1090` ⚠️ **Überschreitet Kapazität!**

### Schritt 4: Sicherheitsprüfung

**Problem:** Summe (1,090) > Kapazität (1,040)

**Lösung:** Proportionale Reduktion

```python
scale_factor = 1040 / 1090 = 0.9541
```

**Neue Mengen:**
- MTB Allrounder: `371 * 0.9541 = 354`
- MTB Competition: `297 * 0.9541 = 283`
- MTB Downhill: `222 * 0.9541 = 212`
- MTB Performance: `200 * 0.9541 = 191`
- **Summe:** 354 + 283 + 212 + 191 = **1,040** ✅

---

## 5️⃣ Materiallimit (Dynamische Reduktion)

### Wichtiger Mechanismus

**Material wird SOFORT reduziert** während der Berechnung:

```python
# Nach jeder Produktionsplanung:
if scheduled_qty > 0:
    stock_by_saddle_type[required_saddle_type] -= scheduled_qty
```

**Ergebnis:**
- Nachfolgende Produkte sehen den **reduzierten** Bestand
- Wenn Material knapp wird, werden nachfolgende Produkte **automatisch reduziert**

### Beispiel: Materiallimit

**Annahme:** Nur 22 Fizik Tundra verfügbar

**Produkte die Fizik Tundra benötigen:**
- MTB Downhill (Rang 3)
- MTB Freeride (Rang 5)
- MTB Performance (Rang 4)

**Berechnung:**
1. **MTB Downhill (Rang 3):** `MIN(300, 222, 22) = 22`
   - Material reduziert: `22 - 22 = 0`
2. **MTB Performance (Rang 4):** `MIN(200, 148, 0) = 0`
   - Kein Material mehr verfügbar
3. **MTB Freeride (Rang 5):** `MIN(250, 185, 0) = 0`
   - Kein Material mehr verfügbar

**Ergebnis:** MTB Downhill erhält alle 22 Sättel (höchster Rang)

---

## 6️⃣ Zusammenfassung

### Proportionalität
- **Zweck:** Faire Verteilung der Kapazität basierend auf Bedarf
- **Formel:** `ABRUNDEN(Bedarf * Kapazität / Gesamtbedarf)`
- **Ergebnis:** Anteiliger Produktionsanteil pro Produkt

### Ranglogik
- **Zweck:** Priorisierung und Restkapazitäts-Verteilung
- **Berechnung:** `Anteilige_Produktion + (Zeile / 1.000.000)`
- **Ergebnis:** Rang 1-4 = Basis-Produktion, Rang 5-8 = Basis + Rest

### Materiallimit
- **Zweck:** Sicherstellen, dass nicht mehr produziert wird als Material verfügbar
- **Mechanismus:** Dynamische Reduktion während Berechnung
- **Ergebnis:** Nachfolgende Produkte sehen reduzierten Bestand

### Sicherheitsprüfungen
1. **Kapazitätsprüfung:** Summe ≤ Tageskapazität
2. **Bedarfsprüfung:** Produktion ≤ Produktionsbedarf
3. **Materialprüfung:** Produktion ≤ Materiallimit

---

**Status:** ✅ **VOLLSTÄNDIG ERKLÄRT**
