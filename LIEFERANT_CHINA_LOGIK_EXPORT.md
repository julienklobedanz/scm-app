# Lieferant China - Vollständige Logik-Dokumentation

**Datum:** 2026-01-25  
**Datei:** `simulation/china_transport.py` → `get_supplier_log_dataframe()`  
**Zweck:** Vollständige Export-Dokumentation für direkte Verwendung

---

## 📋 Übersicht

Die Funktion `get_supplier_log_dataframe()` berechnet für einen spezifischen Sattel-Typ (z.B. "Fizik Tundra") die komplette Lieferanten-Logik:

1. **Bestelleingang** - Basierend auf Volumenplanung
2. **Freigabedatum** - Nächster chinesischer Arbeitstag
3. **Produktionsdatum** - Freigabedatum + 5 chinesische Arbeitstage
4. **Produktionsmenge** - Summe aller freigegebenen Bestellungen
5. **Warenausgang** - Excel-Formel P172 = ABRUNDEN(P157;0) + P165
6. **Warenbestand** - Vorheriger Bestand + Produziert - Warenausgang

---

## 🔢 Excel-Formeln (Referenz)

### P157 - Anteilige Losgröße (ungerundet)
```
=WENN(P154<>0;(P20+O22)*(P154/(P20+P45+P70+P95+O22+O47+O72+O97));0)
```

**Bedeutung:**
- `P20+O22` = Produziert + Warenbestand (für diesen Sattel)
- `P154` = Berechnete Losgröße (500er-Multiplikator)
- `P20+P45+P70+P95+O22+O47+O72+O97` = Gesamt-Verfügbarkeit (alle Sättel)

**Formel:**
```
Anteilige Losgröße = (Produziert + Warenbestand) * (Losgröße / Gesamt-Verfügbarkeit)
```

### P161 - Summe aller anteiligen Losgrößen (gerundet)
```
=ABRUNDEN(P157;0)+ABRUNDEN(P158;0)+ABRUNDEN(P159;0)+ABRUNDEN(P160;0)
```

**Bedeutung:**
- Summe aller gerundeten anteiligen Losgrößen aller Sättel

### P165 - Korrektur für Rundungsdifferenzen
```
=WENN(P154=P161;0;
WENN((P154-P161)<=(P20+O22-ABRUNDEN(P157;0));P154-P161;P20+O22-ABRUNDEN(P157;0)))
```

**Bedeutung:**
- Wenn Losgröße = Summe anteiliger Losgrößen: Korrektur = 0
- Sonst: Korrektur = MIN(Differenz, Verfügbarer Bestand)
- Verfügbarer Bestand = (Produziert + Warenbestand) - ABRUNDEN(anteilige Losgröße)

### P172 - Warenausgang
```
=ABRUNDEN(P157;0)+P165
```

**Bedeutung:**
- Warenausgang = Gerundete anteilige Losgröße + Korrektur
- **WICHTIG:** Finaler Warenausgang = MIN(Geplante Versandmenge, Verfügbarer Bestand)

---

## 🔄 Implementierungs-Logik

### Schritt 1: Datenbasis vorbereiten

```python
# 1. Finde Start- und Enddatum
earliest_order = min((k[0] for k in self.transport_status.keys()), default=0)
start_date = self.workday_calculator.get_date_from_day(earliest_order)
end_date = date(self.workday_calculator.year, 12, 31)
total_days = (end_date - start_date).days + 1

# 2. Alle Sattel-Typen ermitteln
all_saddles = set(item['saddle'] for item in self.master_data.BOM.values())

# 3. Shares berechnen (für Verteilung)
saddle_shares_all = self.master_data.calculate_saddle_shares()

# 4. Tägliche Produktion pro Sattel initialisieren
daily_prod_all = {day_idx: {s: 0.0 for s in all_saddles} for day_idx in range(total_days)}
```

---

### Schritt 2: Bestelleingang berechnen

```python
# Für jeden Tag:
for day_idx in range(total_days):
    curr_date = start_date + timedelta(days=day_idx)
    
    # Berechne Bestellmenge aus Volumenplanung
    # HINWEIS: Bestelleingang auch an Feiertagen erlaubt (wie in Excel)
    order_qty = self._calculate_order_quantity_from_volume_planning(
        curr_date, 
        saddle_name, 
        daily_demands_actual_cache
    )
    
    if order_qty > 0:
        raw_data_map[day_idx]['order'] = order_qty
        
        # Freigabedatum = Nächster chinesischer Arbeitstag
        order_day = (curr_date - date(self.workday_calculator.year, 1, 1)).days
        released_day = self._get_next_workday(order_day, use_chinese_holidays=True)
        released_date = self.workday_calculator.get_date_from_day(released_day)
        released_day_idx = (released_date - start_date).days
        
        # Produktionsdatum = Freigabedatum + 5 chinesische AT
        production_end_day = self._add_workdays(
            released_day, 
            production_time_days,  # Standard: 5
            exclude_start=True, 
            use_chinese_holidays=True
        )
        production_end_date = self.workday_calculator.get_date_from_day(production_end_day)
        production_end_day_idx = (production_end_date - start_date).days
        
        # Sammle Bestellungen nach Freigabedatum und Produktionsdatum
        order_release_map[released_day_idx].append(order_qty)
        release_production_map[production_end_day_idx].append(order_qty)
```

**Ergebnis:**
- `order_release_map[released_day_idx]` = Liste aller Bestellungen, die an diesem Tag freigegeben werden
- `release_production_map[production_end_day_idx]` = Liste aller Bestellungen, die an diesem Tag produziert werden

---

### Schritt 3: Freigegebene Bestellungen und Produktionsmenge berechnen

```python
# Freigegebene Bestellungen = Summe aller Bestelleingänge, deren Freigabedatum dem Datum entspricht
for released_day_idx, order_quantities in order_release_map.items():
    if 0 <= released_day_idx < total_days:
        total_released = sum(order_quantities)
        raw_data_map[released_day_idx]['release'] = total_released

# Produktionsmenge = Summe aller freigegebenen Bestellungen mit Produktionsdatum gleich Datum
for production_end_day_idx, order_quantities in release_production_map.items():
    if 0 <= production_end_day_idx < total_days:
        total_production = sum(order_quantities)
        raw_data_map[production_end_day_idx]['prod'] = total_production
```

---

### Schritt 4: Pool-Produktion sammeln (für Versand-Berechnung)

```python
# Scan Transport Status (für Pool-Berechnung)
for (o_day, o_id), status in self.transport_status.items():
    p_day_sim = status.get('production_end_day')
    qty_original = status.get('quantity', 0.0)
    qty_pool = status.get('actual_quantity', qty_original)  # Nach Produktionsverlusten
    
    if p_day_sim is not None:
        p_date = self.workday_calculator.get_date_from_day(p_day_sim)
        day_offset = (p_date - start_date).days
        
        if 0 <= day_offset < total_days:
            # Verteile Pool-Produktion auf alle Sättel anhand ihrer Shares
            for s in all_saddles:
                s_share = saddle_shares_all.get(s, 0.0)
                daily_prod_all[day_offset][s] += qty_pool * s_share
```

**WICHTIG:** 
- `daily_prod_all[day_idx][s]` = Produktionsmenge für Sattel `s` am Tag `day_idx`
- Diese wird für die Pool-Berechnung verwendet (nicht die einzelne Produktionsmenge!)

---

### Schritt 5: Pool- & Versand-Berechnung (KERN-LOGIK)

```python
lot_size = 500  # Feste Losgröße
carry_over = {s: 0.0 for s in all_saddles}  # Übertrag pro Sattel

for day_idx in range(total_days):
    # 1. Gesamt-Verfügbarkeit prüfen
    total_accumulated = 0.0
    accumulated_by_saddle = {}
    
    for s in all_saddles:
        prod = daily_prod_all[day_idx][s]  # Produktion heute
        co = carry_over[s]  # Übertrag vom Vortag
        acc = prod + co  # Gesamt verfügbar
        accumulated_by_saddle[s] = acc
        total_accumulated += acc
    
    # 2. Losgröße berechnen (nur volle 500er-Batches)
    current_lot_size = int(total_accumulated / lot_size) * lot_size
    
    # 3. Wenn Versand möglich -> Verteilen
    shipments_today = {s: 0.0 for s in all_saddles}
    
    if current_lot_size > 0:
        # A. Ungerundete Anteile (Excel P157)
        unrounded = {}
        for s in all_saddles:
            if total_accumulated > 0:
                unrounded[s] = accumulated_by_saddle[s] * (current_lot_size / total_accumulated)
            else:
                unrounded[s] = 0.0
        
        # B. Runden & Differenz finden (Largest Remainder Method)
        # Excel P161 = sum(rounded.values())
        rounded = {s: int(val) for s, val in unrounded.items()}
        diff = current_lot_size - sum(rounded.values())
        
        # C. Differenz verteilen (Largest Remainder Method)
        if diff > 0:
            # Sortieren nach Nachkommastelle (größte Reste zuerst)
            remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
            remainders.sort(key=lambda x: x[1], reverse=True)
            
            for s, rem in remainders:
                if diff <= 0: 
                    break
                rounded[s] += 1
                diff -= 1
        
        # D. Excel P165-Korrektur für jeden Sattel
        remaining_diff = current_lot_size - sum(rounded.values())
        if remaining_diff > 0:
            for s in all_saddles:
                if remaining_diff <= 0:
                    break
                # Verfügbarer Bestand nach anteiliger Losgröße
                available_after_rounded = accumulated_by_saddle[s] - rounded[s]
                # Korrektur = MIN(Differenz, Verfügbarer Bestand)
                correction = min(remaining_diff, available_after_rounded)
                rounded[s] += correction
                remaining_diff -= correction
        
        shipments_today = rounded  # Excel P172 = ABRUNDEN(P157;0) + P165
    
    # 4. Carry-Over aktualisieren
    for s in all_saddles:
        # Was nicht weggeht, bleibt liegen
        carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]
        
        # Speichere für angefragten Sattel
        if s == saddle_name:
            shipment_results[day_idx] = shipments_today[s]
            stock_results[day_idx] = carry_over[s]
```

**Erklärung:**
- **P157 (ungerundet):** `unrounded[s] = accumulated_by_saddle[s] * (current_lot_size / total_accumulated)`
- **P161 (gerundet):** `sum(rounded.values())` nach Largest Remainder Method
- **P165 (Korrektur):** `MIN(remaining_diff, available_after_rounded)` für jeden Sattel
- **P172 (Warenausgang):** `rounded[s] + P165-Korrektur` = `shipments_today[s]`

---

### Schritt 6: Finale Tabelle bauen

```python
previous_stock = 0.0  # Warenbestand vom Vortag

for day_idx in range(total_days):
    raw = raw_data_map[day_idx]
    curr_date = raw['date']
    is_weekend = raw['weekday'] in ['Sa', 'So']
    has_breakdown = raw['breakdown'] == "Ja"
    
    # PRODUKTIONSMENGE
    if is_weekend or has_breakdown:
        production_qty = 0
    else:
        production_qty = raw['prod']  # Summe aller freigegebenen Bestellungen
    
    # WARENBESTAND (VOR Warenausgang)
    current_stock = previous_stock + production_qty
    
    # WARENAUSGANG
    planned_shipment_qty = shipment_results[day_idx]  # Bereits berechnet (P172)
    
    # Prüfe DeliveryProblemScenario (100% Verlust = "Ausgefallen")
    if self.scenario_manager:
        day_index = (curr_date - date(self.workday_calculator.year, 1, 1)).days
        delivery_problems = self.scenario_manager.get_delivery_problem_scenarios(day_index)
        for scenario in delivery_problems:
            if scenario.component_type == 'saddles' and scenario.loss_percentage >= 1.0:
                shipment_qty = 0
                break
        else:
            # Excel-Formel: Warenausgang = Min(Geplante Versandmenge, Verfügbarer Bestand)
            shipment_qty = min(planned_shipment_qty, current_stock)
    else:
        shipment_qty = min(planned_shipment_qty, current_stock)
    
    # WARENBESTAND (NACH Warenausgang)
    current_stock = current_stock - shipment_qty
    previous_stock = current_stock  # Für nächsten Tag
    
    # Zeile erstellen
    daily_data = {
        'Wochentag': raw['weekday'],
        'Datum': curr_date.strftime(self.master_data.DATE_FORMAT),
        'Bestelleingang': int(round(raw['order'])) if raw['order'] > 0 else '',
        'Freigabedatum': raw['released_date_str'],
        'Freigegebene Bestellungen': int(round(raw['release'])) if raw['release'] > 0 else 0,
        'Störung': raw['breakdown'],
        'Produktionsdatum': raw['production_date_str'],
        'Produktionsmenge': int(round(production_qty)) if production_qty > 0 else 0,
        'Warenausgang': int(round(shipment_qty)) if shipment_qty > 0 else 0,
        'Warenbestand': int(round(current_stock)),
        'Is_Weekend': is_weekend,
        'Is_Holiday': is_holiday
    }
    table_rows.append(daily_data)
```

---

## 🔑 Wichtige Punkte

### 1. Bestelleingang an Feiertagen
- **Excel-Verhalten:** Bestelleingang wird auch an Feiertagen erlaubt
- **Implementierung:** `if not self.workday_calculator.is_weekend(day):` (nur Wochenende ausgeschlossen)

### 2. Produktionsmenge
- **Wochenende:** Produktionsmenge = 0
- **Störung:** Produktionsmenge = 0
- **Sonst:** Produktionsmenge = Summe aller freigegebenen Bestellungen mit Produktionsdatum = heute

### 3. Warenausgang
- **Berechnung:** Excel P172 = ABRUNDEN(P157;0) + P165
- **Finale Formel:** `MIN(Geplante Versandmenge, Verfügbarer Bestand)`
- **100% Verlust:** Wenn DeliveryProblemScenario mit `loss_percentage >= 1.0`, dann Warenausgang = 0

### 4. Carry-Over
- **Berechnung:** `carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]`
- **Bedeutung:** Was nicht verschickt wird, bleibt im Hafen liegen
- **Übertrag:** Wird am nächsten Tag zur Produktion addiert

### 5. Pool-Logik
- **Gesamt-Verfügbarkeit:** Summe aller Sättel (Produktion + Carry-Over)
- **Losgröße:** Nur volle 500er-Batches: `int(total_accumulated / 500) * 500`
- **Verteilung:** Anteilig basierend auf verfügbarem Bestand pro Sattel

---

## 📊 Datenfluss

```
Bestelleingang (Volumenplanung)
    ↓
Freigabedatum (Nächster chinesischer AT)
    ↓
Produktionsdatum (Freigabedatum + 5 chinesische AT)
    ↓
Produktionsmenge (Summe aller freigegebenen Bestellungen)
    ↓
Pool-Berechnung (Alle Sättel zusammen)
    ↓
Versand-Berechnung (P157 + P165 = P172)
    ↓
Warenausgang (MIN(Geplante Versandmenge, Verfügbarer Bestand))
    ↓
Warenbestand (Vorheriger Bestand + Produziert - Warenausgang)
```

---

## 🐍 Python-Code (Kern-Logik)

### Vollständige Pool- & Versand-Berechnung

```python
lot_size = 500
carry_over = {s: 0.0 for s in all_saddles}

for day_idx in range(total_days):
    # 1. Gesamt-Verfügbarkeit
    total_accumulated = 0.0
    accumulated_by_saddle = {}
    
    for s in all_saddles:
        prod = daily_prod_all[day_idx][s]
        co = carry_over[s]
        acc = prod + co
        accumulated_by_saddle[s] = acc
        total_accumulated += acc
    
    # 2. Losgröße (nur volle 500er)
    current_lot_size = int(total_accumulated / lot_size) * lot_size
    
    shipments_today = {s: 0.0 for s in all_saddles}
    
    if current_lot_size > 0:
        # A. P157: Ungerundete Anteile
        unrounded = {}
        for s in all_saddles:
            if total_accumulated > 0:
                unrounded[s] = accumulated_by_saddle[s] * (current_lot_size / total_accumulated)
            else:
                unrounded[s] = 0.0
        
        # B. P161: Runden (Largest Remainder Method)
        rounded = {s: int(val) for s, val in unrounded.items()}
        diff = current_lot_size - sum(rounded.values())
        
        if diff > 0:
            remainders = [(s, unrounded[s] - rounded[s]) for s in all_saddles]
            remainders.sort(key=lambda x: x[1], reverse=True)
            
            for s, rem in remainders:
                if diff <= 0:
                    break
                rounded[s] += 1
                diff -= 1
        
        # C. P165: Korrektur für Rundungsdifferenzen
        remaining_diff = current_lot_size - sum(rounded.values())
        if remaining_diff > 0:
            for s in all_saddles:
                if remaining_diff <= 0:
                    break
                available_after_rounded = accumulated_by_saddle[s] - rounded[s]
                correction = min(remaining_diff, available_after_rounded)
                rounded[s] += correction
                remaining_diff -= correction
        
        shipments_today = rounded  # P172 = ABRUNDEN(P157;0) + P165
    
    # 4. Carry-Over
    for s in all_saddles:
        carry_over[s] = accumulated_by_saddle[s] - shipments_today[s]
        
        if s == saddle_name:
            shipment_results[day_idx] = shipments_today[s]
            stock_results[day_idx] = carry_over[s]
```

---

## ✅ Validierung

### Erwartete Ergebnisse:
- **Gesamtmenge:** 370000 (Summe aller Warenausgänge)
- **Fizik Tundra:** 99900 (Summe aller Warenausgänge für Fizik Tundra)
- **Warenbestand:** Am Ende sollte Carry-Over übrig bleiben (wird in nächste Versendung übernommen)

### Prüfungen:
1. ✅ P157-Berechnung: Anteilig basierend auf verfügbarem Bestand
2. ✅ P165-Korrektur: MIN(Differenz, Verfügbarer Bestand)
3. ✅ P172-Berechnung: ABRUNDEN(P157;0) + P165
4. ✅ Finaler Warenausgang: MIN(Geplante Versandmenge, Verfügbarer Bestand)
5. ✅ Carry-Over: Was nicht verschickt wird, bleibt liegen

---

## 📝 Notizen

- **Cache:** Funktion verwendet Cache für Performance (wird invalidiert bei Szenarien-Änderungen)
- **Szenarien:** Marketing-Szenarien werden in Bestelleingang berücksichtigt
- **Störungen:** SupplierBreakdownScenario setzt Produktionsmenge = 0
- **Verluste:** DeliveryProblemScenario kann zu 100% Verlust führen (Warenausgang = 0)

---

**Ende der Dokumentation**
