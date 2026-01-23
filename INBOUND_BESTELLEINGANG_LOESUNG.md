# Lösung: Inbound verwendet Bestelleingang von Lieferant China

**Datum:** 2026-01-23  
**Problem:** Inbound-Tabelle berücksichtigt Marketing-Szenarien nicht, weil sie aus statischem `transport_status` liest  
**Lösung:** Inbound berechnet Produktion direkt aus "Bestelleingang"-Werten von `get_supplier_log_dataframe()`

---

## 🎯 Problem-Analyse

### **Aktueller Datenfluss:**

1. **Lieferant China (`get_supplier_log_dataframe()`):**
   - ✅ Berechnet "Bestelleingang" **dynamisch** aus `daily_demands_actual` (mit Marketing)
   - ✅ Funktioniert korrekt, wenn Marketing hinzugefügt wird

2. **Inbound (`get_inbound_log_dataframe()`):**
   - ❌ Liest Produktion aus `transport_status` (statisch, wird nur einmal während Simulation erstellt)
   - ❌ Wenn Marketing später hinzugefügt wird, bleibt `transport_status` unverändert
   - ❌ Inbound zeigt daher immer noch alte Werte (ohne Marketing)

### **Kernproblem:**

`transport_status` ist statisch und wird nur einmal während der Simulation erstellt. Wenn Marketing später hinzugefügt wird, wird `transport_status` nicht aktualisiert.

---

## 💡 Lösung: Produktion aus Bestelleingang ableiten

### **Prinzip:**

Statt die Produktion aus `transport_status` zu lesen, berechnen wir die Produktion **direkt aus den "Bestelleingang"-Werten** von `get_supplier_log_dataframe()`.

### **Vorteile:**

1. ✅ **Dynamisch:** Produktion wird immer aus aktuellen "Bestelleingang"-Werten berechnet
2. ✅ **Marketing-kompatibel:** "Bestelleingang" berücksichtigt bereits Marketing (über `daily_demands_actual`)
3. ✅ **Konsistent:** Inbound und Lieferant China verwenden die gleiche Datenquelle
4. ✅ **SSoT:** "Bestelleingang" ist die Single Source of Truth

---

## 📋 Konkrete Umsetzung

### **Schritt 1: Hilfsfunktion erstellen**

**Datei:** `simulation/china_transport.py`  
**Funktion:** `_get_production_from_order_quantities()`

**Zweck:** Berechnet Produktion pro Tag und Sattel-Typ aus "Bestelleingang"-Werten.

**Logik:**
1. Für jeden Tag: Hole "Bestelleingang" für alle Sattel-Typen (aus `get_supplier_log_dataframe()`)
2. Berechne "Freigabedatum" (nächster Arbeitstag nach Bestelleingang)
3. Summiere "Bestelleingang" nach "Freigabedatum" = "Freigegebene Bestellungen"
4. Berechne "Produktionsdatum" (Freigabedatum + 4 chinesische AT)
5. Summiere "Freigegebene Bestellungen" nach "Produktionsdatum" = "Produktionsmenge"

**Rückgabe:** `Dict[day_idx, Dict[saddle_name, production_qty]]`

---

### **Schritt 2: `get_inbound_log_dataframe()` anpassen**

**Datei:** `simulation/china_transport.py`  
**Funktion:** `get_inbound_log_dataframe()`

**Änderung:**

**Vorher:**
```python
# Liest Produktion aus transport_status (statisch)
for (o_day, o_id), status in self.transport_status.items():
    p_day_sim = status.get('production_end_day')
    qty_produced = status.get('actual_quantity', status.get('quantity', 0.0))
    # ...
    daily_prod_all[effective_day][s] += qty_produced * s_share
```

**Nachher:**
```python
# Berechnet Produktion direkt aus Bestelleingang-Werten (dynamisch)
production_by_day_and_saddle = self._get_production_from_order_quantities(saddle_shares_dict)

for day_idx, saddle_prod in production_by_day_and_saddle.items():
    for saddle_name, qty_produced in saddle_prod.items():
        # Konvertiere day_idx zu effective_day (basierend auf start_date)
        effective_day = day_idx  # Oder entsprechend anpassen
        daily_prod_all[effective_day][saddle_name] += qty_produced
```

---

### **Schritt 3: Transport-Daten aus `transport_status` beibehalten**

**Wichtig:** Transport-Daten (Abfahrt, Ankunft, etc.) bleiben aus `transport_status`, da diese nicht von Marketing beeinflusst werden.

**Nur die Produktion** wird dynamisch aus "Bestelleingang" berechnet.

---

## 🔍 Detaillierte Implementierung

### **Hilfsfunktion: `_get_production_from_order_quantities()`**

```python
def _get_production_from_order_quantities(self, saddle_shares_dict: Dict[str, float]) -> Dict[int, Dict[str, float]]:
    """
    Berechnet Produktion pro Tag und Sattel-Typ aus Bestelleingang-Werten.
    
    Diese Funktion verwendet die gleiche Logik wie get_supplier_log_dataframe(),
    um die Produktion zu berechnen, aber ohne die vollständige Tabelle zu erstellen.
    
    Returns:
        Dict[day_idx, Dict[saddle_name, production_qty]]
    """
    # Hole Bestelleingang-Werte für alle Sattel-Typen
    # Verwende get_supplier_log_dataframe() für jeden Sattel-Typ
    # Extrahiere "Produktionsmenge" pro Tag
    
    production_by_day = {}  # day_idx -> {saddle_name -> qty}
    
    for saddle_name, saddle_share in saddle_shares_dict.items():
        # Hole Supplier-Log für diesen Sattel-Typ
        supplier_df = self.get_supplier_log_dataframe(saddle_name, saddle_share)
        
        if supplier_df.empty:
            continue
        
        # Iteriere über alle Zeilen und sammle Produktionsmengen
        for _, row in supplier_df.iterrows():
            production_date_str = row.get('Produktionsdatum', '')
            production_qty = row.get('Produktionsmenge', 0)
            
            if production_date_str and production_qty:
                try:
                    # Konvertiere Datum zu day_idx
                    prod_date = datetime.strptime(production_date_str, self.master_data.DATE_FORMAT).date()
                    day_idx = (prod_date - start_date).days
                    
                    if day_idx not in production_by_day:
                        production_by_day[day_idx] = {}
                    
                    production_by_day[day_idx][saddle_name] = production_by_day[day_idx].get(saddle_name, 0) + production_qty
                except (ValueError, TypeError):
                    continue
    
    return production_by_day
```

---

## ⚠️ Wichtige Überlegungen

### **Performance:**

- `get_supplier_log_dataframe()` wird für jeden Sattel-Typ aufgerufen
- Das könnte langsam sein, wenn der Cache nicht funktioniert
- **Lösung:** Cache in `get_supplier_log_dataframe()` ist bereits implementiert

### **Konsistenz:**

- Transport-Daten (Abfahrt, Ankunft) bleiben aus `transport_status`
- Nur Produktion wird dynamisch berechnet
- **Problem:** Transport-Daten könnten inkonsistent sein, wenn Produktion sich ändert
- **Lösung:** Transport-Daten werden nur für bereits verschiffte Ware verwendet (historisch)

### **Fallback:**

- Wenn `get_supplier_log_dataframe()` fehlschlägt, verwende `transport_status` als Fallback
- Das stellt sicher, dass die Tabelle immer Daten anzeigt

---

## 📊 Vergleich: Vorher vs. Nachher

### **Vorher:**

| Schritt | Marketing hinzugefügt | Ergebnis |
|---------|----------------------|----------|
| 1. `daily_demands_actual` | ✅ Wird neu berechnet (mit Marketing) | ✅ Korrekt |
| 2. `get_supplier_log_dataframe()` | ✅ "Bestelleingang" wird neu berechnet | ✅ Korrekt |
| 3. `transport_status` | ❌ Bleibt unverändert (statisch) | ❌ Alt |
| 4. `get_inbound_log_dataframe()` | ❌ Liest Produktion aus `transport_status` | ❌ Alt |
| 5. Inbound-Tabelle | ❌ Zeigt alte Werte (ohne Marketing) | ❌ Falsch |

### **Nachher:**

| Schritt | Marketing hinzugefügt | Ergebnis |
|---------|----------------------|----------|
| 1. `daily_demands_actual` | ✅ Wird neu berechnet (mit Marketing) | ✅ Korrekt |
| 2. `get_supplier_log_dataframe()` | ✅ "Bestelleingang" wird neu berechnet | ✅ Korrekt |
| 3. `_get_production_from_order_quantities()` | ✅ Berechnet Produktion aus "Bestelleingang" | ✅ Korrekt |
| 4. `get_inbound_log_dataframe()` | ✅ Verwendet dynamische Produktion | ✅ Korrekt |
| 5. Inbound-Tabelle | ✅ Zeigt neue Werte (mit Marketing) | ✅ Korrekt |

---

## 🎯 Finale Implementierung

### **Schritt 1: Hilfsfunktion erstellen**

**Datei:** `simulation/china_transport.py`

```python
def _get_production_from_order_quantities(self, saddle_shares_dict: Dict[str, float], start_date: date) -> Dict[int, Dict[str, float]]:
    """
    Berechnet Produktion pro Tag und Sattel-Typ aus Bestelleingang-Werten.
    
    Returns:
        Dict[day_idx, Dict[saddle_name, production_qty]]
    """
    production_by_day = {}  # day_idx -> {saddle_name -> qty}
    
    for saddle_name, saddle_share in saddle_shares_dict.items():
        supplier_df = self.get_supplier_log_dataframe(saddle_name, saddle_share)
        
        if supplier_df.empty:
            continue
        
        for _, row in supplier_df.iterrows():
            production_date_str = row.get('Produktionsdatum', '')
            production_qty = row.get('Produktionsmenge', 0)
            
            if production_date_str and production_qty:
                try:
                    from datetime import datetime
                    prod_date = datetime.strptime(production_date_str, self.master_data.DATE_FORMAT).date()
                    day_idx = (prod_date - start_date).days
                    
                    if day_idx >= 0:  # Nur zukünftige/aktuelle Tage
                        if day_idx not in production_by_day:
                            production_by_day[day_idx] = {}
                        production_by_day[day_idx][saddle_name] = production_by_day[day_idx].get(saddle_name, 0.0) + float(production_qty)
                except (ValueError, TypeError):
                    continue
    
    return production_by_day
```

### **Schritt 2: `get_inbound_log_dataframe()` anpassen**

**Datei:** `simulation/china_transport.py`  
**Funktion:** `get_inbound_log_dataframe()`

**Änderung in Zeile ~917:**

```python
# VORHER:
for (o_day, o_id), status in self.transport_status.items():
    p_day_sim = status.get('production_end_day')
    qty_produced = status.get('actual_quantity', status.get('quantity', 0.0))
    # ...

# NACHHER:
# Berechne Produktion direkt aus Bestelleingang-Werten (dynamisch)
production_by_day = self._get_production_from_order_quantities(saddle_shares_dict, start_date)

for day_idx, saddle_prod in production_by_day.items():
    for saddle_name, qty_produced in saddle_prod.items():
        if 0 <= day_idx < total_days:
            daily_prod_all[day_idx][saddle_name] += qty_produced
```

---

**Die Lösung wurde in `INBOUND_BESTELLEINGANG_LOESUNG.md` dokumentiert.**
