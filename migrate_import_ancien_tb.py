#!/usr/bin/env python3
"""Import des données de l'ancienne application TB (07-2026_SUIVI_TB.html)
vers la nouvelle application Flask (suivi_patients.db).

Source : export JSON de l'ancienne app TB (Sauvegarde → « Créer une sauvegarde »),
format attendu : liste d'objets avec les clés
id, labId, nom, dateMD, dateDebut, age, sexe, situation, forme, type,
p0, p2, p5, p6, c2date, c2fait, c5date, c5fait, c6date, c6fait,
decision, dateDecision, updatedAt.

⚠️ Le fichier `suivi_tb_sauvegarde.json` actuellement présent contient en
réalité un export VIH (clés genre/birthYear) — ce script refuse ce format.

Cartographie ancien → nouveau :
  id               → conservé (PAT-2026-NNN) pour traçabilité
  nom              → découpé : nom = token le plus long, prénoms = le reste
  dateDebut        → suivi_tb.date_debut_traitement
  age, sexe        → patients.age, patients.sexe
  situation        → situation_penale ('Prévenue' → 'Prévenu')
  forme, type      → forme_clinique, type_cas
  p0/p2/p5/p6      → poids_m0/m2/m5/m6
  c2/c5/c6 date+fait → ctrl_mX_date + ctrl_mX_fait (résultat absent → '')
  decision         → 'Non évalué ou transféré' → 'Transféré' ; 'Décédé' → statut 'decede'
  dateDecision     → date_decision
  dateMD           → ABSENT du nouveau schéma (ignoré)
  quartier, téléphone, contact → non renseignés dans l'ancien app → ''

Usage : python3 migrate_import_ancien_tb.py [fichier_json]
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'suivi_patients.db')
DEFAULT_SOURCE = os.path.join(os.path.dirname(__file__), 'suivi_tb_sauvegarde.json')

DECISIONS_VALIDES = ('', 'Guéri', 'Traitement terminé', 'Echec', 'Perdu de vue', 'Décédé', 'Transféré')
FORMES_VALIDES = ('', 'TPB+', 'TPB-', 'TEP')
TYPES_VALIDES = ('', 'Nouveau', 'Echec', 'Rechute', 'Reprise', 'Transfert entrant')


def split_nom(nom_complet):
    """Sépare un nom complet en (nom, prenoms) — token le plus long = nom de famille,
    premier token en cas d'égalité (convention locale)."""
    tokens = [t for t in (nom_complet or '').split() if t]
    if not tokens:
        return '', ''
    if len(tokens) == 1:
        return tokens[0], ''
    longest = max(tokens, key=len)
    if tokens.count(longest) == 1:
        idx = tokens.index(longest)
        return longest, ' '.join(t for i, t in enumerate(tokens) if i != idx)
    return tokens[0], ' '.join(tokens[1:])


def to_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def importer(source_path):
    with open(source_path, encoding='utf-8') as f:
        anciens = json.load(f)

    if not isinstance(anciens, list) or not anciens:
        print('❌ Format invalide : le fichier doit contenir une liste de patients.')
        sys.exit(1)

    # Détection du format : un export TB a la clé 'labId' (pas 'genre'/'birthYear')
    keys = set(anciens[0].keys())
    if 'labId' not in keys or 'dateDebut' not in keys:
        print('❌ Ce fichier n\'est pas un export TB.')
        print('   (Le fichier `suivi_tb_sauvegarde.json` actuel contient un export VIH —')
        print('    ré-exportez depuis l\'ancienne app TB : ouvrir 07-2026_SUIVI_TB.html,')
        print('    onglet Sauvegarde → « Créer une sauvegarde ».)')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        existants = {r['id'] for r in conn.execute('SELECT id FROM patients').fetchall()}

        year = datetime.now().year
        row = conn.execute(
            "SELECT numero_registre FROM suivi_tb WHERE numero_registre LIKE ? "
            "UNION ALL "
            "SELECT numero_registre FROM suivi_vih WHERE numero_registre LIKE ? "
            "ORDER BY numero_registre DESC LIMIT 1",
            (f'TB-{year}-%', f'TB-{year}-%')
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
            situation = p.get('situation', '')
            if situation == 'Prévenue':
                situation = 'Prévenu'
            if situation not in ('', 'Condamné', 'Prévenu'):
                situation = ''

            decision = p.get('decision', '')
            if decision == 'Non évalué ou transféré':
                decision = 'Transféré'
            if decision not in DECISIONS_VALIDES:
                decision = ''
            forme = p.get('forme', '')
            if forme not in FORMES_VALIDES:
                forme = ''
            type_cas = p.get('type', '')
            if type_cas not in TYPES_VALIDES:
                type_cas = ''

            statut = 'decede' if decision == 'Décédé' else 'incarcere'
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            registre = f'TB-{year}-{next_num:03d}'
            next_num += 1

            def v(key):
                val = p.get(key, '')
                return val if val not in (None, '') else None

            conn.execute("""
                INSERT INTO patients (id, nom, prenoms, date_naissance, age, sexe,
                                      statut, quartier, situation_penale,
                                      telephone, adresse, contact_nom, contact_tel,
                                      created_at, updated_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, nom, prenoms, None, to_int(v('age')), p.get('sexe', 'M'),
                statut, '', situation,
                '', '', '', '',
                now, now, 'import ancien TB'
            ))

            conn.execute("""
                INSERT INTO suivi_tb (patient_id, numero_registre, lab_id, date_debut_traitement,
                    forme_clinique, type_cas,
                    poids_m0, poids_m2, poids_m5, poids_m6,
                    ctrl_m2_date, ctrl_m2_fait, ctrl_m2_resultat,
                    ctrl_m5_date, ctrl_m5_fait, ctrl_m5_resultat,
                    ctrl_m6_date, ctrl_m6_fait, ctrl_m6_resultat,
                    decision, date_decision)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, registre, p.get('labId', ''), v('dateDebut'),
                forme, type_cas,
                to_float(v('p0')), to_float(v('p2')), to_float(v('p5')), to_float(v('p6')),
                v('c2date'), 1 if p.get('c2fait') else 0, '',
                v('c5date'), 1 if p.get('c5fait') else 0, '',
                v('c6date'), 1 if p.get('c6fait') else 0, '',
                decision, v('dateDecision')
            ))

            conn.execute("""
                INSERT INTO journal_audit (table_ciblee, id_cible, action, nouveau_contenu, auteur, date)
                VALUES (?, ?, 'create', ?, ?, ?)
            """, (
                'patients', pid,
                json.dumps({'source': 'ancien TB', 'ancien_id': pid}, ensure_ascii=False),
                'import ancien TB', now
            ))

            importes += 1
            print(f"✅ {pid} {nom} {prenoms} → {registre} · {forme} · {type_cas} · {decision or 'en cours'}")

        conn.commit()
        print(f"\n✅ Import terminé : {importes} patient(s) importé(s), {ignores} ignoré(s).")

        if importes:
            print("\n⚠️  Informations absentes de l'ancienne app, laissées vides :")
            print("   - quartier, téléphone, adresse, contact, date_naissance")
            print("   - dateMD (date de mise sous médicaments) : champ absent du nouveau schéma")
            print("   - résultat des contrôles (positif/négatif) : non saisi dans l'ancienne app")

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