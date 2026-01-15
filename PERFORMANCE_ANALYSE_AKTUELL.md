# Performance-Analyse: Simulation-Start (2-4 Minuten)

## Aktuelles Problem

Die Simulation benötigt beim Start **2-4 Minuten**, was für eine Kundenpräsentation zu lange ist.

## Identifizierte Bottlenecks

### 1. **Initialisierung des Simulators (`Simulator.__init__`)**

**Zeitaufwand:** ~60-120 Sekunden

**Probleme:**
- `_place_initial_orders()` (Zeile 71): Iteriert über 49 Tage, berechnet Nachfrage für jeden Tag
- `_warmup_logistics()` (Zeile 75): Iteriert über 49 Tage, prüft jeden Tag auf Mittwoch
- `_initialize_stock_from_inbound()` (Zeile 78): Berechnet Initialbestand aus `transport_status`

**Aktuelle Optimierungen:**
- ✅ `_initialize_stock_from_inbound()` wurde optimiert (berechnet direkt aus `transport_status`, nicht aus vollständiger Inbound-Tabelle)
- ✅ `_warmup_logistics()` wurde optimiert (nur Mittwoche)
- ⚠️ `_place_initial_orders()` berechnet noch Nachfrage für jeden Tag

### 2. **`get_inbound_log_dataframe()` während der Simulation**

**Zeitaufwand:** ~30-60 Sekunden (wenn nicht gecacht)

**Probleme:**
- Wird während der Simulation 365× aufgerufen (einmal pro Tag)
- Berechnet über 426 Tage (01.11.2025 bis 31.12.2026)
- Komplexe Eimer-Logik (Port-Buckets) für jeden Tag

**Aktuelle Optimierungen:**
- ✅ Cache-Mechanismus implementiert
- ✅ Begrenzung auf 365 Tage (bis Ende 2025) für Performance
- ✅ Früher Abbruch, wenn keine Daten mehr kommen
- ⚠️ Erste Berechnung dauert immer noch lange

### 3. **Simulation-Loop (`Simulator.run()`)**

**Zeitaufwand:** ~60-120 Sekunden

**Probleme:**
- Iteriert über 365 Tage
- Für jeden Tag: Nachfrage-Berechnung, Produktionsplanung, Materialverbrauch, Bestellungen
- `get_daily_arrival_qty()` wird 365× aufgerufen (mit Cache, aber erste Berechnung dauert)

**Aktuelle Optimierungen:**
- ✅ Verwendet Nachfrage aus Volumenplanung (keine eigene Berechnung)
- ✅ Cache für `get_daily_arrival_qty()`
- ⚠️ Erste Berechnung von `get_inbound_log_dataframe()` dauert lange

## Root Cause Analysis

### Hauptproblem: `get_inbound_log_dataframe()` wird während der Initialisierung benötigt

**Warum?**
- `_initialize_stock_from_inbound()` benötigt den Initialbestand
- Aber: Diese Methode wurde bereits optimiert und berechnet direkt aus `transport_status`
- **ABER:** `_warmup_logistics()` ruft `process_shipments()` auf, was möglicherweise `get_inbound_log_dataframe()` benötigt

### Sekundäres Problem: `_place_initial_orders()` berechnet Nachfrage

**Warum?**
- Berechnet Nachfrage für 49 Tage (Lead Time)
- Verwendet `demand_calculator._calculate_monthly_base_daily_float()`
- **ABER:** Diese Daten sollten aus der Volumenplanung kommen!

## Mögliche Lösungen

### Lösung 1: **Lazy Initialization** (Empfohlen)

**Idee:** Initialisierung verzögern, bis sie wirklich benötigt wird.

**Umsetzung:**
- `_initialize_stock_from_inbound()` nicht im `__init__` aufrufen
- Stattdessen: Beim ersten Zugriff auf `inventory.stock_saddles` initialisieren
- Oder: In `run()` am Anfang initialisieren (wenn `transport_status` bereits gefüllt ist)

**Vorteile:**
- `__init__` wird schneller
- Initialisierung erfolgt erst, wenn Daten verfügbar sind

**Nachteile:**
- Komplexere Logik
- Mögliche Race Conditions

### Lösung 2: **Vorberechnung der Inbound-Tabelle**

**Idee:** Inbound-Tabelle bereits in Volumenplanung berechnen und cachen.

**Umsetzung:**
- Volumenplanung berechnet nicht nur Nachfrage, sondern auch Bestellungen
- Bestellungen werden in `procurement_plan` gespeichert
- Simulator verwendet `procurement_plan` statt selbst zu berechnen

**Vorteile:**
- Berechnung nur einmal (in Volumenplanung)
- Simulator nur Lookup, keine Berechnung

**Nachteile:**
- Größere Architektur-Änderung
- Benötigt Umstellung auf "Volumenplanung als Single Source of Truth"

### Lösung 3: **Parallelisierung der Initialisierung**

**Idee:** Initialisierung in separatem Thread/Prozess.

**Umsetzung:**
- `_place_initial_orders()` und `_warmup_logistics()` parallel ausführen
- Aber: Streamlit unterstützt kein echtes Threading

**Vorteile:**
- Theoretisch schneller

**Nachteile:**
- Nicht mit Streamlit kompatibel
- Komplexe Synchronisation

### Lösung 4: **Weitere Optimierung von `get_inbound_log_dataframe()`**

**Idee:** Berechnung noch weiter optimieren.

**Umsetzung:**
- Nur relevante Tage berechnen (nicht alle 426 Tage)
- Früherer Abbruch
- Caching verbessern

**Vorteile:**
- Schnell umsetzbar
- Keine Architektur-Änderung

**Nachteile:**
- Begrenzte Verbesserung
- Mögliche Dateninkonsistenzen

### Lösung 5: **Verzögerte Initialisierung von `_initialize_stock_from_inbound()`**

**Idee:** `_initialize_stock_from_inbound()` erst nach `_warmup_logistics()` aufrufen, wenn `transport_status` bereits gefüllt ist.

**Umsetzung:**
- `_initialize_stock_from_inbound()` aus `__init__` entfernen
- In `run()` am Anfang aufrufen (nachdem alle Bestellungen platziert sind)

**Vorteile:**
- Schnell umsetzbar
- Keine Architektur-Änderung
- Nutzt bereits vorhandene Daten

**Nachteile:**
- Initialbestand ist erst nach `run()` verfügbar

## Empfohlene Lösung: Kombination aus Lösung 2 und 5

**Kurzfristig (Lösung 5):**
- `_initialize_stock_from_inbound()` aus `__init__` entfernen
- In `run()` am Anfang aufrufen (wenn `transport_status` bereits gefüllt ist)
- **Erwartete Verbesserung:** ~30-60 Sekunden

**Langfristig (Lösung 2):**
- Volumenplanung als "Single Source of Truth" etablieren
- Bestellungen in Volumenplanung berechnen
- Simulator verwendet vorgegebene Daten
- **Erwartete Verbesserung:** ~60-120 Sekunden

## Nächste Schritte

1. **Sofort:** Lösung 5 implementieren (verzögerte Initialisierung)
2. **Dann:** Lösung 2 implementieren (Volumenplanung als Single Source of Truth)
3. **Optional:** Weitere Optimierungen in `get_inbound_log_dataframe()`

## Messungen

**Aktuell:**
- Initialisierung: ~60-120 Sekunden
- Simulation-Loop: ~60-120 Sekunden
- **Gesamt: ~2-4 Minuten**

**Ziel:**
- Initialisierung: ~10-20 Sekunden
- Simulation-Loop: ~30-60 Sekunden
- **Gesamt: ~40-80 Sekunden**

**Ideal:**
- Initialisierung: ~5-10 Sekunden
- Simulation-Loop: ~20-40 Sekunden
- **Gesamt: ~25-50 Sekunden**

