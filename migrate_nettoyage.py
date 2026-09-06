#!/usr/bin/env python3
"""Nettoyage de la base : suppression des données de test et renumérotation
des numéros de registre VIH des données réelles (importées).

Ce script :
1. Supprime TOUTES les données antérieures à la migration (patients de
   démonstration/test PAT-*, leurs suivis TB/VIH, historiques et audits) —
   ne conserve que les patients importés depuis l'ancienne app (PVVIH-*).
2. Renumérote les numéros de registre VIH des données réelles à partir
   de 001 (ex : VIH-2026-002..015 → VIH-2026-001..014), triés par patient.

⚠️ DESTRUCTIF : aucune restauration automatique. Une sauvegarde est
recommandée avant exécution.
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')


def nettoyer():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        avant = {
            'patients': conn.execute('SELECT COUNT(*) c FROM patients').fetchone()['c'],
            'suivi_vih': conn.execute('SELECT COUNT(*) c FROM suivi_vih').fetchone()['c'],
            'suivi_tb': conn.execute('SELECT COUNT(*) c FROM suivi_tb').fetchone()['c'],
            'historique': conn.execute('SELECT COUNT(*) c FROM historique_statut').fetchone()['c'],
            'audit': conn.execute('SELECT COUNT(*) c FROM journal_audit').fetchone()['c'],
        }

        # ── 1. Suppression des données de test (tout sauf PVVIH-*) ──
        conn.execute("DELETE FROM journal_audit WHERE id_cible NOT LIKE 'PVVIH-%'")
        conn.execute("DELETE FROM historique_statut")
        conn.execute("DELETE FROM suivi_tb")
        conn.execute("DELETE FROM suivi_vih WHERE patient_id NOT LIKE 'PVVIH-%'")
        conn.execute("DELETE FROM patients WHERE id NOT LIKE 'PVVIH-%'")

        # ── 2. Renumérotation des registres VIH des données réelles ──
        year = datetime.now().year
        rows = conn.execute(
            "SELECT patient_id, numero_registre FROM suivi_vih "
            "WHERE patient_id LIKE 'PVVIH-%' ORDER BY patient_id"
        ).fetchall()
        print('Renumérotation des registres VIH :')
        for i, row in enumerate(rows, 1):
            ancien = row['numero_registre']
            nouveau = f'VIH-{year}-{i:03d}'
            conn.execute(
                "UPDATE suivi_vih SET numero_registre = ? WHERE patient_id = ?",
                (nouveau, row['patient_id'])
            )
            print(f"  {row['patient_id']} : {ancien} → {nouveau}")

        # Audit de l'opération
        conn.execute("""
            INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur, date)
            VALUES (?, ?, 'delete', ?, ?, ?)
        """, (
            'patients', 'purge-test',
            'Purge des données de test + renumérotation VIH depuis 001',
            'maintenance', datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

        conn.commit()

        apres = {
            'patients': conn.execute('SELECT COUNT(*) c FROM patients').fetchone()['c'],
            'suivi_vih': conn.execute('SELECT COUNT(*) c FROM suivi_vih').fetchone()['c'],
            'suivi_tb': conn.execute('SELECT COUNT(*) c FROM suivi_tb').fetchone()['c'],
            'historique': conn.execute('SELECT COUNT(*) c FROM historique_statut').fetchone()['c'],
        }

        print(f"\n✅ Purge terminée :")
        print(f"   patients : {avant['patients']} → {apres['patients']}")
        print(f"   suivi_vih : {avant['suivi_vih']} → {apres['suivi_vih']}")
        print(f"   suivi_tb : {avant['suivi_tb']} → {apres['suivi_tb']}")
        print(f"   historique : {avant['historique']} → {apres['historique']}")
        print(f"   audit : {avant['audit']} → conservé (import + purge)")

    except Exception as e:
        conn.rollback()
        print(f'❌ Erreur : {e}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    nettoyer()