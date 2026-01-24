#!/usr/bin/env python3
"""
Prüft Konsistenz zwischen Materiallager und Produktion
"""

import pandas as pd
from datetime import datetime

# Lade Dateien
materiallager_path = '/Users/julienklobedanz/Downloads/2026-01-24T15-48_export.csv'
produktion_allrounder_path = '/Users/julienklobedanz/Downloads/2026-01-24T15-48_export-3.csv'
produktion_extreme_path = '/Users/julienklobedanz/Downloads/2026-01-24T15-52_export.csv'

print("=" * 80)
print("MATERIALLAGER UND PRODUKTION - KONSISTENZPRÜFUNG")
print("=" * 80)

# Lade Materiallager (Spark)
df_material = pd.read_csv(materiallager_path)
print(f"\nMateriallager Spark: {len(df_material)} Zeilen")

# Lade Produktion MTB Allrounder
df_allrounder = pd.read_csv(produktion_allrounder_path)
print(f"Produktion MTB Allrounder: {len(df_allrounder)} Zeilen")

# Lade Produktion MTB Extreme
df_extreme = pd.read_csv(produktion_extreme_path)
print(f"Produktion MTB Extreme: {len(df_extreme)} Zeilen")

# Prüfe Spalten
print("\n" + "=" * 80)
print("SPALTEN-ANALYSE")
print("=" * 80)

print("\nMateriallager Spalten:")
print(df_material.columns.tolist())

print("\nProduktion Allrounder Spalten:")
print(df_allrounder.columns.tolist())

print("\nProduktion Extreme Spalten:")
print(df_extreme.columns.tolist())

# Prüfe Datumsformat
print("\n" + "=" * 80)
print("DATUMS-PRÜFUNG")
print("=" * 80)

date_col = None
for col in df_material.columns:
    if 'Datum' in col or 'datum' in col.lower():
        date_col = col
        break

if date_col:
    print(f"\nDatumsspalte gefunden: {date_col}")
    print(f"Erste Zeile Datum: {df_material[date_col].iloc[0] if len(df_material) > 0 else 'N/A'}")
    print(f"Letzte Zeile Datum: {df_material[date_col].iloc[-1] if len(df_material) > 0 else 'N/A'}")

# Prüfe Materiallager
print("\n" + "=" * 80)
print("MATERIALLAGER ANALYSE (Spark)")
print("=" * 80)

# Finde relevante Spalten
zugang_col = None
abgang_col = None
bestand_morgen_col = None
bestand_abend_col = None

for col in df_material.columns:
    if 'Zugang' in col or 'zugang' in col.lower():
        zugang_col = col
    if 'Abgang' in col or 'abgang' in col.lower():
        abgang_col = col
    if 'Bestand' in col and ('Morgen' in col or 'morgen' in col.lower()):
        bestand_morgen_col = col
    if 'Bestand' in col and ('Abend' in col or 'abend' in col.lower()):
        bestand_abend_col = col

print(f"\nZugang Spalte: {zugang_col}")
print(f"Abgang Spalte: {abgang_col}")
print(f"Bestand Morgen Spalte: {bestand_morgen_col}")
print(f"Bestand Abend Spalte: {bestand_abend_col}")

if zugang_col and abgang_col and bestand_morgen_col and bestand_abend_col:
    # Prüfe Konsistenz: Bestand_Abend = Bestand_Morgen + Zugang - Abgang
    print("\nPrüfe Konsistenz: Bestand_Abend = Bestand_Morgen + Zugang - Abgang")
    inconsistencies = []
    
    for idx, row in df_material.iterrows():
        if pd.isna(row[date_col]) or row[date_col] == '':
            continue
        
        bestand_morgen = row[bestand_morgen_col] if not pd.isna(row[bestand_morgen_col]) else 0
        zugang = row[zugang_col] if not pd.isna(row[zugang_col]) else 0
        abgang = row[abgang_col] if not pd.isna(row[abgang_col]) else 0
        bestand_abend = row[bestand_abend_col] if not pd.isna(row[bestand_abend_col]) else 0
        
        try:
            bestand_morgen = float(bestand_morgen) if bestand_morgen != '' else 0
            zugang = float(zugang) if zugang != '' else 0
            abgang = float(abgang) if abgang != '' else 0
            bestand_abend = float(bestand_abend) if bestand_abend != '' else 0
        except (ValueError, TypeError):
            continue
        
        expected_abend = bestand_morgen + zugang - abgang
        diff = abs(bestand_abend - expected_abend)
        
        if diff > 0.01:  # Toleranz für Rundungsfehler
            inconsistencies.append({
                'date': row[date_col],
                'bestand_morgen': bestand_morgen,
                'zugang': zugang,
                'abgang': abgang,
                'bestand_abend': bestand_abend,
                'expected_abend': expected_abend,
                'diff': diff
            })
    
    if inconsistencies:
        print(f"\n❌ {len(inconsistencies)} Inkonsistenzen gefunden:")
        for inc in inconsistencies[:10]:  # Zeige erste 10
            print(f"  {inc['date']}: Bestand_Morgen={inc['bestand_morgen']}, "
                  f"Zugang={inc['zugang']}, Abgang={inc['abgang']}, "
                  f"Bestand_Abend={inc['bestand_abend']}, Erwartet={inc['expected_abend']:.2f}, "
                  f"Differenz={inc['diff']:.2f}")
        if len(inconsistencies) > 10:
            print(f"  ... und {len(inconsistencies) - 10} weitere")
    else:
        print("\n✅ Keine Inkonsistenzen in Materiallager-Berechnung gefunden")

# Prüfe Produktion
print("\n" + "=" * 80)
print("PRODUKTION ANALYSE")
print("=" * 80)

# Finde relevante Spalten in Produktion
tatsaechliche_pm_col = None
for col in df_allrounder.columns:
    if 'tatsächliche' in col.lower() and 'pm' in col.lower():
        tatsaechliche_pm_col = col
        break

print(f"\nTatsächliche PM Spalte (Allrounder): {tatsaechliche_pm_col}")
if tatsaechliche_pm_col:
    total_allrounder = df_allrounder[tatsaechliche_pm_col].sum() if not df_allrounder[tatsaechliche_pm_col].isna().all() else 0
    print(f"Summe Tatsächliche PM (Allrounder): {total_allrounder}")

tatsaechliche_pm_col_extreme = None
for col in df_extreme.columns:
    if 'tatsächliche' in col.lower() and 'pm' in col.lower():
        tatsaechliche_pm_col_extreme = col
        break

print(f"\nTatsächliche PM Spalte (Extreme): {tatsaechliche_pm_col_extreme}")
if tatsaechliche_pm_col_extreme:
    total_extreme = df_extreme[tatsaechliche_pm_col_extreme].sum() if not df_extreme[tatsaechliche_pm_col_extreme].isna().all() else 0
    print(f"Summe Tatsächliche PM (Extreme): {total_extreme}")

# Prüfe Konsistenz: Materiallager Abgang = Summe Produktion (Allrounder + Extreme)
print("\n" + "=" * 80)
print("KONSISTENZ: MATERIALABGANG vs PRODUKTION")
print("=" * 80)

if abgang_col and tatsaechliche_pm_col and tatsaechliche_pm_col_extreme:
    # Merge DataFrames nach Datum
    df_allrounder_date = df_allrounder.copy()
    df_extreme_date = df_extreme.copy()
    df_material_date = df_material.copy()
    
    # Finde Datumsspalte in allen DataFrames
    date_col_allrounder = None
    date_col_extreme = None
    
    for col in df_allrounder.columns:
        if 'Datum' in col or 'datum' in col.lower():
            date_col_allrounder = col
            break
    
    for col in df_extreme.columns:
        if 'Datum' in col or 'datum' in col.lower():
            date_col_extreme = col
            break
    
    if date_col and date_col_allrounder and date_col_extreme:
        # Merge
        merged = df_material_date.merge(
            df_allrounder_date[[date_col_allrounder, tatsaechliche_pm_col]],
            left_on=date_col,
            right_on=date_col_allrounder,
            how='left',
            suffixes=('', '_allrounder')
        )
        
        merged = merged.merge(
            df_extreme_date[[date_col_extreme, tatsaechliche_pm_col_extreme]],
            left_on=date_col,
            right_on=date_col_extreme,
            how='left',
            suffixes=('', '_extreme')
        )
        
        # Prüfe Konsistenz
        inconsistencies_prod = []
        
        for idx, row in merged.iterrows():
            if pd.isna(row[date_col]) or row[date_col] == '':
                continue
            
            abgang = row[abgang_col] if not pd.isna(row[abgang_col]) else 0
            prod_allrounder = row[tatsaechliche_pm_col] if not pd.isna(row[tatsaechliche_pm_col]) else 0
            prod_extreme = row[tatsaechliche_pm_col_extreme] if not pd.isna(row[tatsaechliche_pm_col_extreme]) else 0
            
            try:
                abgang = float(abgang) if abgang != '' else 0
                prod_allrounder = float(prod_allrounder) if prod_allrounder != '' else 0
                prod_extreme = float(prod_extreme) if prod_extreme != '' else 0
            except (ValueError, TypeError):
                continue
            
            expected_abgang = prod_allrounder + prod_extreme
            diff = abs(abgang - expected_abgang)
            
            if diff > 0.01:  # Toleranz für Rundungsfehler
                inconsistencies_prod.append({
                    'date': row[date_col],
                    'abgang': abgang,
                    'prod_allrounder': prod_allrounder,
                    'prod_extreme': prod_extreme,
                    'expected_abgang': expected_abgang,
                    'diff': diff
                })
        
        if inconsistencies_prod:
            print(f"\n❌ {len(inconsistencies_prod)} Inkonsistenzen zwischen Materialabgang und Produktion:")
            for inc in inconsistencies_prod[:20]:  # Zeige erste 20
                print(f"  {inc['date']}: Abgang={inc['abgang']}, "
                      f"Allrounder={inc['prod_allrounder']}, Extreme={inc['prod_extreme']}, "
                      f"Erwartet={inc['expected_abgang']:.2f}, Differenz={inc['diff']:.2f}")
            if len(inconsistencies_prod) > 20:
                print(f"  ... und {len(inconsistencies_prod) - 20} weitere")
        else:
            print("\n✅ Keine Inkonsistenzen zwischen Materialabgang und Produktion gefunden")
        
        # Summen
        total_abgang = merged[abgang_col].sum()
        total_prod_allrounder = merged[tatsaechliche_pm_col].sum()
        total_prod_extreme = merged[tatsaechliche_pm_col_extreme].sum()
        total_expected = total_prod_allrounder + total_prod_extreme
        
        print(f"\nSummen:")
        print(f"  Materialabgang (gesamt): {total_abgang}")
        print(f"  Produktion Allrounder (gesamt): {total_prod_allrounder}")
        print(f"  Produktion Extreme (gesamt): {total_prod_extreme}")
        print(f"  Erwarteter Abgang (gesamt): {total_expected}")
        print(f"  Differenz (gesamt): {abs(total_abgang - total_expected):.2f}")

print("\n" + "=" * 80)
print("ANALYSE ABGESCHLOSSEN")
print("=" * 80)
