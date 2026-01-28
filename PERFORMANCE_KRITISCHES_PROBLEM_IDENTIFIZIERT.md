# Performance: Kritisches Problem identifiziert

**Datum:** 28.01.2026  
**Problem:** Simulation lädt immer noch nicht (1+ Minute)  
**Status:** 🔍 **HAUPTPROBLEM IDENTIFIZIERT**

---

## 🔴 KRITISCHES PROBLEM: `get_supplier_log_dataframe()` wird mehrfach aufgerufen

### Problem-Analyse:

**In `get_inbound_log_dataframe()` (Zeile 1249-1251):**
```python
# Berechne Produktion für jeden Sattel-Typ aus Bestelleingang-Werten
for saddle_name, saddle_share in saddle_shares_dict.items():
    # Hole Supplier-Log für diesen Sattel-Typ (enthält bereits Marketing)
    supplier_df = self.get_supplier_log_dataframe(saddle_name, saddle_share)
```

**Das bedeutet:**
- `get_inbound_log_dataframe()` wird aufgerufen
- Für **JEDEN Sattel-Typ** (3 Stück: Fizik Tundra, Selle Italia SLR, Selle Italia Flite) wird `get_supplier_log_dataframe()` aufgerufen
- Jede `get_supplier_log_dataframe()` Berechnung iteriert über **~426 Tage** (Zeile 784: `for day_idx in range(total_days)`)
- **Das bedeutet: 3x die Berechnung!**

### Warum ist das so langsam?

**`get_supplier_log_dataframe()` (Zeile 784-1125):**
- Iteriert über `total_days` (~426 Tage)
- Für jeden Tag werden komplexe Berechnungen durchgeführt:
  - Bestelleingang aus Volumenplanung
  - Freigabedatum berechnen
  - Produktionsdatum berechnen
  - Warenausgang berechnen
- Bei 3 Sattel-Typen = **3 × 426 Tage = 1278 Iterationen**

### Cache hilft nicht genug:

**Cache-Key (Zeile 740):**
```python
cache_key = (saddle_name, saddle_share)
```

**Problem:** Der Cache wird nur pro Sattel-Typ gespeichert, aber:
- Beim ersten Aufruf von `get_inbound_log_dataframe()` werden alle 3 Sattel-Typen berechnet
- Das dauert sehr lange, auch wenn gecacht

---

## 💡 Lösungsansätze

### Ansatz 1: **Lazy Loading für `get_inbound_log_dataframe()`**
- `get_inbound_log_dataframe()` wird nur aufgerufen, wenn wirklich benötigt
- Nicht beim App-Start, sondern erst wenn eine Seite sie benötigt

### Ansatz 2: **Optimierung von `get_supplier_log_dataframe()`**
- Berechnung früher beenden wenn keine Daten mehr kommen
- Bereits teilweise implementiert (Zeile 812-825), könnte weiter optimiert werden

### Ansatz 3: **Parallele Berechnung der Sattel-Typen**
- Aber: Streamlit ist single-threaded, daher nicht möglich

### Ansatz 4: **Caching verbessern**
- Cache wird bereits verwendet, aber die erste Berechnung dauert trotzdem lange

---

## 🎯 Empfohlener Ansatz

**Ansatz 1 + Ansatz 2:** Kombination aus Lazy Loading und Optimierung

1. **Lazy Loading:** `get_inbound_log_dataframe()` wird nur aufgerufen wenn benötigt
2. **Optimierung:** `get_supplier_log_dataframe()` früher beenden wenn möglich

---

**Status:** 🔍 **IN ANALYSE**  
**Nächster Schritt:** Implementierung von Ansatz 1 + 2
