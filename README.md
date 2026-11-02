# SCM-Simulation: Lieferkette eines Mountainbike-Herstellers

Interaktive Simulation einer Supply Chain mit Streamlit. Die App plant Nachfrage, Produktion, Beschaffung und Transport eines fiktiven Mountainbike-Herstellers (Adventure Works AG, Werk in Dortmund) über ein Jahr, wertet die Ergebnisse mit SCOR-Kennzahlen aus und spielt Störungen in der Lieferkette durch, zum Beispiel Wasserschaden im Lager, Maschinenausfall beim Lieferanten oder Ladungsverlust auf See.

Entstanden als Gruppenprojekt im Modul WI3 (Wirtschaftsinformatik, HAW Hamburg, Wintersemester 2025/26) und als Prüfungsleistung abgegeben, gemeinsam mit Leif Rudnik. Die Aufgabe: Ein Konzept und einen Demonstrator für eine operative Planungssoftware erarbeiten, die einem Fahrradhersteller mehr Flexibilität bei schwankender Nachfrage und langen Lieferwegen verschafft.

<!-- TODO: Screenshot der Reporting-Seite als docs/img/reporting.png ablegen und hier einbinden:
![Reporting](docs/img/reporting.png)
-->

## Was die App kann

- **Nachfrage und Volumenplanung:** Jahresvolumen von 370.000 Rädern, verteilt über acht Modelle, sechs Absatzmärkte und eine monatliche Saisonalität; die Planung läuft wöchentlich auf Arbeitstage heruntergebrochen (Wochenenden und deutsche Feiertage berücksichtigt).
- **Produktion:** Kapazität pro Stunde, Schichtmodell (1 bis 3 Schichten) und tägliche Arbeitslast aus den Stammdaten; die Produktionsplanung richtet sich nach Materialverfügbarkeit und Bedarf.
- **Beschaffung und Transport:** drei Lieferanten (Heilbronn: Rahmen, Saragossa: Gabeln, China: Sättel) mit eigenen Vorlaufzeiten (7 Tage, 14 Tage, 7 Wochen), Losgrößen und Transportwegen (LKW, Bahn, Schiff); die Strecken nach China und in die USA laufen als Mehrstufenketten aus Vorlauf per LKW, Seefracht und Nachlauf.
- **Lager:** Material- und Fertigproduktelager mit Bestandsverlauf, Reichweiten und farblicher Hervorhebung kritischer Vorlaufzeiten.
- **Szenarien:** Marketingaktion, Wasserschaden im Materiallager, Lieferantenausfall in China, Verspätungen auf einzelnen Transportabschnitten und Ladungsverlust auf See; Szenarien lassen sich in der Seitenleiste hinzufügen und kombinieren.
- **Kennzahlen:** SCOR-Metriken auf der Startseite sowie ein Reporting mit KPI-Dashboard.
- **Stammdaten:** Stückliste, Saisonalität, Märkte, Lieferanten, Routen und Planungsparameter sind in der Oberfläche einsehbar und anpassbar; die Simulation wird nach Änderungen neu berechnet.

## Seiten

| Seite | Inhalt |
|---|---|
| Startseite | SCOR-Metriken |
| Reporting | KPI-Dashboard und Auswertungen |
| Volumenplanung | Wöchentliche Planung nach Modell und Markt |
| Lieferant China | Produktion und Vorlauf beim chinesischen Lieferanten |
| Inbound | Inbound-Logistik und Transportketten |
| Materiallager | Bestände und Reichweiten der Komponenten |
| Produktion | Montage, Schichten, Auslastung |
| Fertigproduktelager | Bestände und Auslieferung |
| Stammdaten | Parameter der Simulation |

## Architektur

Die Simulationslogik liegt getrennt von der Oberfläche und lässt sich ohne Streamlit testen.

```
app.py, pages/      Streamlit-Seiten
ui/                 Oberflächenlogik: Seitenleiste, Tabellen, Diagramme, Berechnungen
simulation/         Simulationskern: Nachfrage, Produktion, Beschaffung, Transport, Arbeitstage
models/             Bestände, Rückstände (Backlog), Szenarien
config/             Stammdaten und Feiertage
tests/              Unit- und Regressionstests
```

## Umfang der Umsetzung

Der Dozent hat den Aufwand bewusst begrenzt: Statt Excel durfte auch eine eigene Anwendung gebaut werden, und es genügte, die Lieferkette des chinesischen Lieferanten vollständig abzubilden. Die beiden anderen Lieferanten (Heilbronn und Saragossa) durften vereinfacht simuliert werden, ohne die gesamte Kette im Detail zu implementieren.

Wir haben uns für die eigene Anwendung entschieden. Die chinesische Lieferkette mit Vorlauf, Seefracht, Nachlauf und den Störungsszenarien ist deshalb im Detail umgesetzt (`simulation/china_transport.py`). Heilbronn und Saragossa laufen über Vorlaufzeit, Losgröße und Transportdauer.

## Starten

Voraussetzung: Python 3.10 oder neuer.

```bash
git clone https://github.com/julienklobedanz/scm-app.git
cd scm-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Die App öffnet sich unter `http://localhost:8501`. Beim ersten Aufruf läuft automatisch eine Simulation im Standardfall.

## Tests

```bash
pip install pytest
pytest
```

Die Tests prüfen unter anderem Datenkonsistenz, Parameter, Randfälle, Robustheit und zirkuläre Abhängigkeiten.

## Technik

Python, Streamlit, pandas, NumPy, Plotly, holidays.

## Aufgabenverteilung

Die Gruppe hatte keine feste Aufgabenteilung. Ich habe das Projekt aufgesetzt (Struktur, Simulationskern, Stammdaten-Modell) und mich danach schwerpunktmäßig um Produktion, Bestelleingang und Materiallager gekümmert. Leif Rudnik hat vor allem an der Oberfläche gearbeitet (Seiten für Inbound und Stammdaten, Tabellen- und Theme-Gestaltung) sowie an Fehlerbehebungen und Verbesserungen im Gesamtsystem.

## Hinweise

- Alle Daten und Parameter sind fiktiv. Sie stammen aus der Aufgabenstellung des Moduls (Produktstruktur, Märkte, Vorlaufzeiten, Losgrößen, Saisonalität) oder wurden für die Simulation angenommen.
- Die Oberfläche ist auf das Wesentliche ausgelegt. Eine modernere Version mit Next.js und einem getrennten FastAPI-Backend ist in Arbeit und noch nicht veröffentlicht.
