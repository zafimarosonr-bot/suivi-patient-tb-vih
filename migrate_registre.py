#!/usr/bin/env python3
"""Migration : ajout des colonnes numero_registre aux tables suivi_tb et suivi_vih.

Ce script :
1. Ajoute la colonne numero_registre à suivi_tb et suivi_vih si elle n'existe pas
2. Génère les numéros de registre pour les enregistrements existants
   en se basant sur la date de début de traitement/suivi
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # ── Vérifier et ajouter les colonnes ──────────────────────
        # Suivi TB
        cols_tb = [row[1] for row in conn.execute("PRAGMA table_info(suivi_tb)").fetchall()]
        if 'numero_registre' not in cols_tb:
            conn.execute("ALTER TABLE suivi_tb ADD COLUMN numero_registre TEXT DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tb_registre ON suivi_tb(numero_registre)")
            print("✅ Colonne 'numero_registre' ajoutée à suivi_tb.")
        else:
            print("ℹ️  La colonne 'numero_registre' existe déjà dans suivi_tb.")

        # Suivi VIH
        cols_vih = [row[1] for row in conn.execute("PRAGMA table_info(suivi_vih)").fetchall()]
        if 'numero_registre' not in cols_vih:
            conn.execute("ALTER TABLE suivi_vih ADD COLUMN numero_registre TEXT DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vih_registre ON suivi_vih(numero_registre)")
            print("✅ Colonne 'numero_registre' ajoutée à suivi_vih.")
        else:
            print("ℹ️  La colonne 'numero_registre' existe déjà dans suivi_vih.")

        # ── Générer les numéros pour les enregistrements existants ──
        # TB : trier par date_debut_traitement pour assigner les numéros dans l'ordre chronologique
        tb_rows = conn.execute("""
            SELECT id, patient_id, numero_registre, date_debut_traitement
            FROM suivi_tb
            WHERE numero_registre = '' OR numero_registre IS NULL
            ORDER BY date_debut_traitement ASC, id ASC
        """).fetchall()

        # Compteurs par année pour TB
        tb_counters = {}
        for row in tb_rows:
            date_debut = row['date_debut_traitement'] or '2026-01-01'
            year = date_debut[:4]  # Extraire l'année
            if year not in tb_counters:
                tb_counters[year] = 1
            else:
                tb_counters[year] += 1
            num = tb_counters[year]
            registre = f"TB-{year}-{num:03d}"
            conn.execute(
                "UPDATE suivi_tb SET numero_registre = ? WHERE id = ?",
                (registre, row['id'])
            )
            print(f"  TB: {row['patient_id']} → {registre}")

        # VIH : trier par date_debut_suivi
        vih_rows = conn.execute("""
            SELECT id, patient_id, numero_registre, date_debut_suivi
            FROM suivi_vih
            WHERE numero_registre = '' OR numero_registre IS NULL
            ORDER BY date_debut_suivi ASC, id ASC
        """).fetchall()

        # Compteurs par année pour VIH
        vih_counters = {}
        for row in vih_rows:
            date_debut = row['date_debut_suivi'] or '2026-01-01'
            year = date_debut[:4]
            if year not in vih_counters:
                vih_counters[year] = 1
            else:
                vih_counters[year] += 1
            num = vih_counters[year]
            registre = f"VIH-{year}-{num:03d}"
            conn.execute(
                "UPDATE suivi_vih SET numero_registre = ? WHERE id = ?",
                (registre, row['id'])
            )
            print(f"  VIH: {row['patient_id']} → {registre}")

        conn.commit()
        print(f"\n✅ Migration terminée : {len(tb_rows)} enregistrements TB, {len(vih_rows)} enregistrements VIH mis à jour.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
