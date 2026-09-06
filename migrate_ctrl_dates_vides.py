#!/usr/bin/env python3
"""Migration : remplit les dates de contrôle TB vides (M2/M5/M6)
à partir de la date de début de traitement :
    M2 = date_debut_traitement + 2 mois
    M5 = date_debut_traitement + 5 mois
    M6 = date_debut_traitement + 6 mois
Les dates déjà renseignées (saisies manuelles) ne sont jamais écrasées.
"""
import sqlite3
import os
import calendar
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')


def add_months(date_str, months):
    """Ajoute des mois calendaires à une date 'AAAA-MM-JJ' (gère les fins de mois)."""
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    total = d.year * 12 + (d.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def migrate():
    if not os.path.exists(DB_PATH):
        print("Base de données non trouvée. Rien à faire.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, date_debut_traitement, ctrl_m2_date, ctrl_m5_date, ctrl_m6_date FROM suivi_tb"
        ).fetchall()

        remplis = {'ctrl_m2_date': 0, 'ctrl_m5_date': 0, 'ctrl_m6_date': 0}
        sans_debut = 0

        for r in rows:
            debut = r['date_debut_traitement']
            if not debut:
                sans_debut += 1
                continue
            for col, mois in (('ctrl_m2_date', 2), ('ctrl_m5_date', 5), ('ctrl_m6_date', 6)):
                if r[col]:
                    continue  # date déjà renseignée → on ne touche pas
                conn.execute(
                    f"UPDATE suivi_tb SET {col} = ? WHERE id = ?",
                    (add_months(debut, mois), r['id'])
                )
                remplis[col] += 1

        conn.commit()
        print(f"✅ Dates de contrôle remplies : M2={remplis['ctrl_m2_date']}, "
              f"M5={remplis['ctrl_m5_date']}, M6={remplis['ctrl_m6_date']}")
        if sans_debut:
            print(f"⚠️ {sans_debut} suivi(s) sans date de début de traitement (non traités).")
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()