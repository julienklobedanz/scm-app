# Gesamtmengen-Problem bei geänderten Beschaffungszeiten

**Datum:** 2026-01-30

## Problem

Wenn sich die Beschaffungszeiten ändern (z.B. 4AT statt 2AT für LKW China), ändern sich die Gesamtmengen in Materiallager, Produktion und Fertigproduktelager. Das sollte nicht passieren - nur die Zeiten sollten sich ändern, nicht die Mengen.

## Ursachen-Analyse

### Problem 1: Initial Orders basieren auf lead_time_days

**Aktuell:**
- `_place_initial_orders()` bestellt nur für die ersten `lead_time_days` Tage
- Wenn sich die Beschaffungszeiten ändern, ändert sich die Anzahl der vorbestellten Tage
- Das führt zu unterschiedlichen Gesamtmengen

**Beispiel:**
- Standard: 2AT, 30KT, 2AT → lead_time = 49 Tage → initial orders für 49 Tage
- Geändert: 4AT, 30KT, 2AT → lead_time könnte sich ändern → initial orders für unterschiedliche Anzahl Tage

### Problem 2: Tägliche Bestellungen verwenden lead_time

**Aktuell:**
- `procurement_manager.py` verwendet `lead_time` für tägliche Bestellungen
- Wenn sich die Beschaffungszeiten ändern, ändert sich das Timing der Bestellungen
- Das kann zu unterschiedlichen Gesamtmengen führen

### Problem 3: Gesamtmenge sollte immer 370.000 sein

**Anforderung:**
- Die Gesamtmenge sollte immer 370.000 sein, unabhängig von den Beschaffungszeiten
- Die Beschaffungszeiten sollten nur das Timing beeinflussen, nicht die Gesamtmenge

## Lösung

### Option 1: Initial Orders für gesamtes Jahr (365 Tage)

**Vorteile:**
- Gesamtmenge bleibt immer gleich
- Unabhängig von Beschaffungszeiten

**Nachteile:**
- Mehr initial orders
- Könnte Performance-Probleme verursachen

### Option 2: Dynamische Anpassung der initial orders

**Vorgehen:**
- Initial orders immer für `max(lead_time_days, 365)` Tage
- Stellt sicher, dass immer genug Material vorbestellt ist

### Option 3: Gesamtmenge-Korrektur am Jahresende

**Vorgehen:**
- Am Jahresende prüfen, ob Gesamtmenge = 370.000
- Falls nicht, korrigieren durch zusätzliche Bestellungen/Produktion

## Empfehlung

**Option 2** ist am besten:
- Initial orders für `max(lead_time_days, 365)` Tage
- Stellt sicher, dass immer genug Material vorbestellt ist
- Gesamtmenge bleibt konstant

## Implementierung

1. Ändere `_place_initial_orders()` um für `max(lead_time_days, 365)` Tage zu bestellen
2. Stelle sicher, dass tägliche Bestellungen immer die gleiche Gesamtmenge produzieren
3. Teste mit verschiedenen Beschaffungszeiten (2AT, 4AT, etc.)
