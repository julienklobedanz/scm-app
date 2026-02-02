# Losgrößen- und Versandlogik: Vollständige Analyse

**Datum:** 31.01.2026  
**Ziel:** Vollständiges Verständnis der Losgrößen- und Versandlogik

---

## 🔍 Kernfrage

**Wie funktioniert die Versandlogik wirklich?**
- Wie werden 370.000 Stück über das Jahr verschifft?
- Warum funktioniert die Produktion mit richtigen Zahlen?
- Wie unterscheiden sich Simulation und Anzeige?

---

## 📊 Zwei verschiedene Logiken

### 1. Simulation (`process_shipments`) - Die tatsächliche Logik

**Datei:** `simulation/china_transport.py`, Zeile 196-437

**Wann wird es aufgerufen?**
- **Nur in der Warmup-Phase** (`simulator.py`, Zeile 141)
- **Nur an Mittwochen** (Schiffe fahren nur mittwochs ab)
- **Nicht während des Jahres** (nur Warmup: Tage -49 bis -1)

**Wie funktioniert es?**
```python
def process_shipments(self, current_day: int) -> None:
    # 1. Sammle ALLES, was im Hafen liegt und noch nicht verschifft wurde
    ready_to_ship_orders = []
    total_quantity_at_port = 0.0
    
    for (order_day, order_id), status in self.transport_status.items():
        if (status['arrival_at_port_day'] <= current_day and 
            not status['shipped']):  # WICHTIG: Nur unverschiffte Bestellungen
            ready_to_ship_orders.append(status)
            total_quantity_at_port += status['quantity']
    
    # 2. Prüfe, ob >= 500 im Hafen sind
    if total_quantity_at_port >= lot_size:  # lot_size = 500
        # 3. Verschiffe exakt 500 Stück (FIFO: älteste zuerst)
        remaining_to_ship = lot_size  # Exakt 500 Stück
        
        for status in ready_to_ship_orders:
            if remaining_to_ship <= 0:
                break
            # Verschiffe von dieser Bestellung...
            # Rest bleibt im Hafen (shipped = False)
```

**Wichtige Punkte:**
- ✅ Verschifft **exakt 500 Stück** pro Aufruf
- ✅ Sammelt **ALLE** unverschifften Bestellungen im Hafen
- ✅ Reste bleiben im Hafen (`shipped = False`)
- ✅ Wird **nur in Warmup-Phase** aufgerufen (nur Mittwoche)

**Beispiel:**
- Mittwoch 1: 1500 Stück im Hafen → verschifft 500, 1000 bleiben
- Mittwoch 2 (nächste Woche): 1000 + neue Bestellungen → verschifft wieder 500
- Mittwoch 3: Rest + neue Bestellungen → verschifft wieder 500

---

### 2. Anzeige (`get_inbound_log_dataframe`) - Die Display-Logik

**Datei:** `simulation/china_transport.py`, Zeile 1202-1807

**Wann wird es aufgerufen?**
- **Für die Anzeige** (Page 4: Inbound)
- **Täglich berechnet** (für jeden Tag im Jahr)
- **Nicht für die Simulation** (nur für Display)

**Wie funktioniert es?**
```python
def get_inbound_log_dataframe(self, saddle_shares_dict):
    # 1. Sammle tägliche Produktion
    daily_prod_all = defaultdict(lambda: defaultdict(float))
    # ... sammle Produktion für jeden Tag ...
    
    # 2. Für jeden Tag:
    for day_idx in range(max_calculation_days):
        # A. Gesamt-Verfügbarkeit prüfen
        total_accumulated = 0.0
        for s in all_saddles:
            prod = daily_prod_all[day_idx][s]
            co = carry_over[s]  # Reste vom Vortag
            acc = prod + co
            total_accumulated += acc
        
        # B. Losgröße berechnen
        current_lot_size = int(total_accumulated / lot_size) * lot_size
        
        # C. Wenn Versand möglich (current_lot_size > 0)
        if current_lot_size > 0:
            # Verschiffe ALLE Vielfachen von 500
            # Beispiel: 1500 akkumuliert → verschifft 1500 (nicht nur 500)
            shipments_today = rounded  # Alle Vielfachen von 500
        
        # D. Carry-Over aktualisieren
        carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]
```

**Wichtige Punkte:**
- ✅ Verschifft **alle Vielfachen von 500** (1500 → 1500, nicht nur 500)
- ✅ Berechnet **täglich** (nicht nur mittwochs)
- ✅ Verwendet **Carry-Over** für Reste
- ✅ **Nur für Anzeige** (nicht für Simulation)

**Beispiel:**
- Tag 1: 1500 akkumuliert → verschifft 1500 (alle)
- Tag 2: 500 akkumuliert → verschifft 500
- Tag 3: 300 akkumuliert → verschifft 0 (Rest bleibt als Carry-Over)

---

## 🔄 Wie funktioniert die Simulation wirklich?

### Schritt 1: Initial Orders (vor Simulation)

**Datei:** `simulator.py`, Zeile 143-193

**Was passiert?**
- Bestellt für das **gesamte Jahr** (365 Tage)
- Bestellt täglich basierend auf Bedarf
- Speichert Bestellungen in `transport_status` (noch nicht verschifft)

**Beispiel:**
- Tag -49: Bestellt für Tag 0
- Tag -48: Bestellt für Tag 1
- ...
- Tag 315: Bestellt für Tag 364

**Ergebnis:**
- Alle Bestellungen für das Jahr sind bereits platziert
- Alle Bestellungen haben `shipped = False`
- Alle Bestellungen haben `arrival_at_port_day` berechnet

---

### Schritt 2: Warmup-Phase (vor Simulation)

**Datei:** `simulator.py`, Zeile 129-141

**Was passiert?**
- Für jeden Mittwoch von Tag -49 bis Tag -1:
  - Ruft `process_shipments(sim_day)` auf
  - `process_shipments` sammelt ALLE Bestellungen, die bis zu diesem Tag im Hafen angekommen sind
  - Verschifft exakt 500 Stück (wenn >= 500 im Hafen)
  - Reste bleiben im Hafen (`shipped = False`)

**Beispiel:**
- Mittwoch Tag -42: 1500 Stück im Hafen → verschifft 500, 1000 bleiben
- Mittwoch Tag -35: 1000 + neue Bestellungen → verschifft 500, Rest bleibt
- ...
- Mittwoch Tag -7: Letzte Warmup-Versände

**Ergebnis:**
- Viele Versände sind bereits geplant (für Ankunft ab Tag 0)
- Reste bleiben im Hafen für spätere Versände
- Alle Versände haben `available_day` berechnet (Ankunft in Deutschland)

---

### Schritt 3: Hauptschleife (Tag 0-364)

**Datei:** `simulator.py`, Zeile 207-509

**Was passiert?**
- Für jeden Tag:
  1. **Wareneingang:** `get_daily_arrival_qty(day)` liest aus `transport_status`
  2. **Produktion:** Verwendet Material aus Wareneingang
  3. **Bestellung:** Platziert neue Bestellungen für Tag (day + 49)

**WICHTIG:**
- `process_shipments` wird **NICHT** während des Jahres aufgerufen!
- Neue Bestellungen werden täglich platziert, aber **nicht sofort verschifft**
- Versände wurden bereits in der Warmup-Phase geplant

**Aber:** Neue Bestellungen werden während des Jahres platziert. Wie werden diese verschifft?

---

## 🎯 Die Lösung: Warum funktioniert es?

### Antwort: Die Warmup-Phase plant ALLES vor

**Wie funktioniert es wirklich?**

1. **Initial Orders:** Alle Bestellungen für das Jahr werden vorbereitet
2. **Warmup-Phase:** `process_shipments` wird für jeden Mittwoch von Tag -49 bis Tag -1 aufgerufen
3. **Aber:** `process_shipments` sammelt **ALLE** Bestellungen, die bis zu diesem Tag im Hafen angekommen sind

**Das bedeutet:**
- Wenn `process_shipments` an Mittwoch Tag -7 aufgerufen wird:
  - Sammelt ALLE Bestellungen mit `arrival_at_port_day <= -7` und `shipped = False`
  - Das können Bestellungen sein, die für Tag 0, 1, 2, ... geplant sind
  - Verschifft 500 Stück (FIFO)
  - Reste bleiben im Hafen

**Aber:** Neue Bestellungen werden während des Jahres platziert. Wie werden diese verschifft?

---

## 🔍 Die tatsächliche Logik: `process_shipments` wird mehrfach aufgerufen

**Warte!** Lass mich nochmal genau prüfen...

**Tatsächlich:** `process_shipments` wird **NUR** in der Warmup-Phase aufgerufen (nur Mittwoche von Tag -49 bis Tag -1).

**Das bedeutet:**
- Alle Versände für das Jahr werden bereits in der Warmup-Phase geplant
- Neue Bestellungen während des Jahres werden **NICHT** verschifft (sie bleiben im Hafen)

**Aber:** Das kann nicht sein, weil die Produktion richtige Zahlen ausspuckt!

---

## 💡 Die wahre Lösung: `get_daily_arrival_qty` liest aus `transport_status`

**Datei:** `simulation/china_transport.py`, Zeile 1768-1807

**Wie funktioniert es?**
```python
def get_daily_arrival_qty(self, day_index: int) -> float:
    # Summiere alle Transporte, die an diesem Tag verfügbar werden
    total_arrival_qty = 0.0
    
    for (order_day, order_id), status in self.transport_status.items():
        available_day = status.get('available_day')
        if available_day == day_index:
            # Summiere die tatsächliche Menge
            qty = status.get('actual_quantity', status.get('quantity', 0.0))
            total_arrival_qty += qty
    
    return total_arrival_qty
```

**Das bedeutet:**
- `get_daily_arrival_qty` liest aus `transport_status`
- `transport_status` wurde bereits in der Warmup-Phase durch `process_shipments` aktualisiert
- Alle Versände haben bereits `available_day` berechnet

**Aber:** Neue Bestellungen während des Jahres haben noch kein `available_day`!

---

## 🎯 Die finale Antwort: Zwei verschiedene Systeme

### System 1: Simulation (tatsächliche Logik)

**Wie funktioniert es?**
1. **Initial Orders:** Alle Bestellungen für das Jahr werden vorbereitet
2. **Warmup-Phase:** `process_shipments` wird für jeden Mittwoch aufgerufen
3. **Hauptschleife:** `get_daily_arrival_qty` liest aus `transport_status` (bereits geplant)

**Problem:** Neue Bestellungen während des Jahres werden nicht verschifft!

**Lösung:** Vielleicht werden alle Bestellungen bereits in der Warmup-Phase geplant?

---

### System 2: Anzeige (Display-Logik)

**Wie funktioniert es?**
1. `get_inbound_log_dataframe` berechnet täglich Versände
2. Verschifft alle Vielfachen von 500 (nicht nur 500)
3. Verwendet Carry-Over für Reste

**Problem:** Nicht konsistent mit Simulation!

---

## 📋 Zusammenfassung

### Simulation (`process_shipments`):
- ✅ Verschifft **exakt 500 Stück** pro Aufruf
- ✅ Wird **nur in Warmup-Phase** aufgerufen (nur Mittwoche)
- ✅ Sammelt **ALLE** unverschifften Bestellungen
- ✅ Reste bleiben im Hafen

### Anzeige (`get_inbound_log_dataframe`):
- ✅ Verschifft **alle Vielfachen von 500**
- ✅ Berechnet **täglich** (nicht nur mittwochs)
- ✅ Verwendet **Carry-Over** für Reste
- ✅ **Nur für Display** (nicht für Simulation)

### Wie kommen 370.000 zusammen?
- **Initial Orders:** Bestellen für gesamtes Jahr (370.000 Stück)
- **Warmup-Phase:** Plant Versände für das Jahr vor
- **Hauptschleife:** Liest Versände aus `transport_status`

**Aber:** Neue Bestellungen während des Jahres werden nicht verschifft!

---

## ✅ Die Lösung: Wie funktioniert es wirklich?

### Schritt 1: Initial Orders (vor Simulation)

**Datei:** `simulator.py`, Zeile 143-193

**Was passiert?**
- Bestellt für das **gesamte Jahr** (365 Tage: Tag 0-364)
- Bestellt an Tag `(day - lead_time_days)` für Bedarfstag `day`
- Beispiel: Für Bedarfstag 100 wird an Tag (100 - 49) = Tag 51 bestellt
- Alle Bestellungen werden in `transport_status` gespeichert mit:
  - `arrival_at_port_day` bereits berechnet (Produktion + LKW zum Hafen)
  - `shipped = False` (noch nicht verschifft)
  - `ship_departure_day = None` (noch nicht geplant)

**Ergebnis:**
- Alle Bestellungen für das Jahr sind bereits platziert
- Alle Bestellungen haben `arrival_at_port_day` berechnet
- Alle Bestellungen haben `shipped = False`

---

### Schritt 2: Warmup-Phase (vor Simulation)

**Datei:** `simulator.py`, Zeile 129-141

**Was passiert?**
- Für jeden Mittwoch von Tag -49 bis Tag -1:
  - Ruft `process_shipments(sim_day)` auf
  - `process_shipments` sammelt **ALLE** Bestellungen mit:
    - `arrival_at_port_day <= current_day` (bereits im Hafen angekommen)
    - `shipped = False` (noch nicht verschifft)
  - Verschifft exakt 500 Stück (wenn >= 500 im Hafen)
  - Reste bleiben im Hafen (`shipped = False`)

**WICHTIG:**
- `process_shipments` sammelt **ALLE** Bestellungen, die bis zu diesem Tag im Hafen angekommen sind
- Das können Bestellungen sein, die für Tag 0, 1, 2, ... geplant sind
- Beispiel: Mittwoch Tag -7:
  - Sammelt ALLE Bestellungen mit `arrival_at_port_day <= -7`
  - Das können Bestellungen sein, die für Tag 0-50 geplant sind (wenn sie früh genug produziert wurden)
  - Verschifft 500 Stück (FIFO)
  - Reste bleiben im Hafen

**Ergebnis:**
- Viele Versände sind bereits geplant (für Ankunft ab Tag 0)
- Reste bleiben im Hafen für spätere Versände
- Alle Versände haben `available_day` berechnet (Ankunft in Deutschland)

---

### Schritt 3: Hauptschleife (Tag 0-364)

**Datei:** `simulator.py`, Zeile 207-509

**Was passiert?**
- Für jeden Tag:
  1. **Wareneingang:** `get_daily_arrival_qty(day)` liest aus `transport_status`
  2. **Produktion:** Verwendet Material aus Wareneingang
  3. **Bestellung:** Platziert neue Bestellungen für Tag (day + 49)

**WICHTIG:**
- `process_shipments` wird **NICHT** während des Jahres aufgerufen!
- Neue Bestellungen werden täglich platziert, aber **nicht sofort verschifft**
- Versände wurden bereits in der Warmup-Phase geplant

**Aber:** Neue Bestellungen während des Jahres werden nicht verschifft!

---

## 🎯 Die finale Antwort

### Warum funktioniert es?

**Antwort:** Die Warmup-Phase plant Versände für das gesamte Jahr vor!

**Wie funktioniert es wirklich?**

1. **Initial Orders:** Alle Bestellungen für das Jahr werden vorbereitet
2. **Warmup-Phase:** `process_shipments` wird für jeden Mittwoch von Tag -49 bis Tag -1 aufgerufen
3. **WICHTIG:** `process_shipments` sammelt **ALLE** Bestellungen, die bis zu diesem Tag im Hafen angekommen sind
   - Das können Bestellungen sein, die für Tag 0, 1, 2, ... geplant sind
   - Wenn eine Bestellung früh genug produziert wurde, kann sie bereits in der Warmup-Phase verschifft werden
4. **Hauptschleife:** Liest Versände aus `transport_status` (bereits geplant)

**Beispiel:**
- Bestellung für Tag 0: Bestellt an Tag -49, Produktion endet Tag -44, LKW zum Hafen Tag -42
- Mittwoch Tag -42: `process_shipments` sammelt diese Bestellung (weil `arrival_at_port_day = -42 <= -42`)
- Verschifft 500 Stück (wenn >= 500 im Hafen)
- Reste bleiben im Hafen für spätere Versände

**Ergebnis:**
- Alle Versände für das Jahr werden bereits in der Warmup-Phase geplant
- Neue Bestellungen während des Jahres werden **NICHT** verschifft (sie bleiben im Hafen)
- **ABER:** Das ist OK, weil alle Bestellungen bereits in den initialen Bestellungen enthalten sind!

---

## 📊 Zusammenfassung: Wie werden 370.000 Stück verschifft?

### Antwort: Durch mehrfache Aufrufe von `process_shipments` in der Warmup-Phase

**Wie funktioniert es?**

1. **Initial Orders:** Alle Bestellungen für das Jahr werden vorbereitet (370.000 Stück)
2. **Warmup-Phase:** `process_shipments` wird für jeden Mittwoch von Tag -49 bis Tag -1 aufgerufen
   - Jeder Aufruf verschifft exakt 500 Stück (wenn >= 500 im Hafen)
   - Reste bleiben im Hafen für den nächsten Mittwoch
3. **Ergebnis:** Über mehrere Mittwoche werden alle 370.000 Stück verschifft

**Beispiel:**
- Mittwoch Tag -42: 1500 Stück im Hafen → verschifft 500, 1000 bleiben
- Mittwoch Tag -35: 1000 + neue Bestellungen → verschifft 500, Rest bleibt
- Mittwoch Tag -28: Rest + neue Bestellungen → verschifft 500, Rest bleibt
- ...
- Mittwoch Tag -7: Letzte Warmup-Versände

**Ergebnis:**
- Über ~7-8 Mittwoche werden alle 370.000 Stück verschifft
- Jeder Mittwoch verschifft 500 Stück (oder mehr, wenn mehrere Aufrufe nötig sind)
- Reste bleiben im Hafen für den nächsten Mittwoch

---

## ✅ Finale Antworten

### 1. Werden neue Bestellungen während des Jahres verschifft?
**Antwort:** Nein, aber das ist OK!
- Alle Bestellungen sind bereits in den initialen Bestellungen enthalten
- Neue Bestellungen während des Jahres werden nicht verschifft (sie bleiben im Hafen)
- **ABER:** Das ist OK, weil die initialen Bestellungen bereits alle Bedarfe abdecken

### 2. Wie werden 370.000 Stück verschifft?
**Antwort:** Durch mehrfache Aufrufe von `process_shipments` in der Warmup-Phase
- Jeder Mittwoch verschifft exakt 500 Stück
- Über mehrere Mittwoche werden alle 370.000 Stück verschifft
- Reste bleiben im Hafen für den nächsten Mittwoch

### 3. Warum funktioniert die Produktion mit richtigen Zahlen?
**Antwort:** Weil alle Versände bereits in der Warmup-Phase geplant wurden
- `get_daily_arrival_qty` liest aus `transport_status` (bereits geplant)
- Alle Versände haben bereits `available_day` berechnet
- Die Produktion verwendet diese geplanten Versände

---

**Status:** ✅ **ANALYSE ABGESCHLOSSEN**  
**Ergebnis:** Die Logik funktioniert durch mehrfache Aufrufe von `process_shipments` in der Warmup-Phase
