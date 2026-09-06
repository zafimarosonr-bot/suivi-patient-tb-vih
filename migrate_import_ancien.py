#!/usr/bin/env python3
"""Import des données de l'ancienne application VIH (07-2026_pvvih.html)
vers la nouvelle application Flask (suivi_patients.db).

Source : suivi_pvvih_sauvegarde.json (export JSON de l'ancienne app PVVIH).
L'import FUSIONNE avec les données existantes (INSERT uniquement, aucun DELETE).

Cartographie ancien → nouveau :
  id               → conservé (PVVIH-2026-NNN) pour traçabilité
  nom              → découpé : nom = token le plus long (nom de famille), prénoms = le reste
  genre            → sexe
  birthYear        → age (l'ancien app ne stockait pas la date de naissance exacte)
  quartier         → inchangé (toutes les valeurs sont valides dans la nouvelle app)
  observation      → 'Libéré' → statut 'libere', sinon 'incarcere'
                     + valeur conservée dans suivi_vih.observation
  date_debut_suivi → ABSENT de l'ancien app → NULL (à compléter)
  situation_penale → ABSENTE → '' (à compléter lors de l'édition)
  code VIH         → généré (DDMMYY + 3 lettres NOM + 2 lettres PRÉNOMS)
  numero_registre  → VIH-AAAA-NNN (prochain numéro disponible)

Usage : python3 migrate_import_ancien.py [fichier_json]
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

from app import generate_vih_code

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')
DEFAULT_SOURCE = os.path.join(os.path.dirname(__file__), 'suivi_pvvih_sauvegarde.json')

OBSERVATIONS_VALIDES = ('', 'Nouveau', 'Transfert', 'Libéré', 'Décédé')


def split_nom(nom_complet):
    """Sépare un nom complet en (nom, prenoms).

    Règle : le token le plus long est considéré comme le nom de famille,
    le reste comme les prénoms. En cas d'égalité de longueur, le premier
    token est pris comme nom (convention locale : famille en premier).
    """
    tokens = [t for t in (nom_complet or '').split() if t]
    if not tokens:
        return '', ''
    if len(tokens) == 1:
        return tokens[0], ''
    longest = max(tokens, key=len)
    if tokens.count(longest) == 1:
        idx = tokens.index(longest)
        nom = longest
        prenoms = ' '.join(t for i, t in enumerate(tokens) if i != idx)
    else:
        nom = tokens[0]
        prenoms = ' '.join(tokens[1:])
    return nom, prenoms


def importer(source_path):
    with open(source_path, encoding='utf-8') as f:
        anciens = json.load(f)

    if not isinstance(anciens, list):
        print('❌ Format invalide : le fichier doit contenir une liste de patients.')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        existants = {r['id'] for r in conn.execute('SELECT id FROM patients').fetchall()}

        year = datetime.now().year
        row = conn.execute(
            "SELECT numero_registre FROM suivi_vih WHERE numero_registre LIKE ? "
            "ORDER BY numero_registre DESC LIMIT 1",
            (f'VIH-{year}-%',)
        ).fetchone()
        next_num = (int(row['numero_registre'].split('-')[-1]) + 1) if row else 1

        importes = 0
        ignores = 0
        for p in anciens:
            pid = p.get('id', '')
            if not pid:
                continue
            if pid in existants:
                print(f"⏭️  {pid} déjà présent — ignoré")
                ignores += 1
                continue

            nom, prenoms = split_nom(p.get('nom', ''))
            age = None
            if p.get('birthYear'):
                try:
                    age = year - int(p['birthYear'])
                except (ValueError, TypeError):
                    age = None
            sexe = 'F' if p.get('genre') == 'F' else 'M'
            quartier = p.get('quartier', '')
            observation = p.get('observation', '')
            if observation not in OBSERVATIONS_VALIDES:
                observation = ''
            statut = 'libere' if observation == 'Libéré' else 'incarcere'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            code = generate_vih_code(nom, prenoms, None, age)
            registre = f"VIH-{year}-{next_num:03d}"
            next_num += 1

            conn.execute("""
                INSERT INTO patients (id, nom, prenoms, date_naissance, age, sexe,
                                      statut, quartier, situation_penale,
                                      telephone, adresse, contact_nom, contact_tel,
                                      created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, nom, prenoms, None, age, sexe, statut, quartier, '',
                '', '', '', '',
                now, now, 'import ancien PVVIH'
            ))

            conn.execute("""
                INSERT INTO suivi_vih (patient_id, numero_registre, code, date_debut_suivi, observation)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, registre, code, None, observation))

            conn.execute("""
                INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur, date)
                VALUES (?, ?, 'create', ?, ?, ?)
            """, (
                'patients', pid,
                json.dumps({'source': 'ancien PVVIH', 'ancien_id': pid}, ensure_ascii=False),
                'import ancien PVVIH', now
            ))

            importes += 1
            print(f"✅ {pid} {nom} {prenoms} → {registre} · code {code} · {statut} · {quartier}")

        conn.commit()
        print(f"\n✅ Import terminé : {importes} patient(s) importé(s), {ignores} ignoré(s).")

        if importes:
            print("\n⚠️  Champs absents de l'ancienne app, laissés vides (à compléter) :")
            print("   - date_debut_suivi = NULL pour tous les patients importés")
            print("   - situation_penale = '' pour tous les patients importés")
            print("   - historique_statut : non recréé (date de libération inconnue)")

    except Exception as e:
        conn.rollback()
        print(f'❌ Erreur : {e}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not os.path.exists(source):
        print(f'❌ Fichier introuvable : {source}')
        sys.exit(1)
    importer(source)