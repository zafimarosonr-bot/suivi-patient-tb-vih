# 📋 Note de Session — Suivi Patient TB & VIH

> **⚠️ INSTRUCTIONS POUR UVELLE SESSION :**
> Cette note est le seul moyen de retrouver le contexte du projet.
> Lis-la entièrement avant de commencer tout travail.
> Elle est mise à jour à chaque grande modification.

---

## 📏 RÈGLES OBLIGATOIRES

> **Ces règles doivent être respectées à chaque session.**

### 1. Langue : Français uniquement
- Toutes les conversations avec l'utilisateur doivent se faire **exclusivement en français**
- Les commentaires dans le code, les noms de variables et les documentation restent en anglais (convention technique)
- Seules les interactions vocales/textuelles avec l'utilisateur sont concernées

### 2. Mise à jour obligatoire de la note de session

> ⚠️ **RÈGLE ABSOLUE — NE JAMAIS OUBLIER DE METTRE À JOUR CETTE NOTE**
>
> Chaque oubli de mise à jour crée un **décalage dangereux** entre la réalité du code et la documentation. Lors de la prochaine session, le développeur (AI ou humain) lit cette note pour reprendre le travail — s'il manque des informations, il risque de doubler, casser ou ignorer des fonctionnalités déjà implémentées.
>
> **PROCÉDURE OBLIGATOIRE :**
> 1. **Avant de commencer** : relire la note pour vérifier qu'elle est à jour
> 2. **À chaque modification** : mettre à jour immédiatement la note (ne pas attendre la fin)
> 3. **À la fin de chaque tâche** : vérifier que la note reflète le dernier état du code
> 4. **Avant de terminer la session** : relire la note une dernière fois pour confirmer la cohérence
>
> Ce qui doit être mis à jour :
> - Les routes ajoutées/modifiées dans le tableau des routes
> - Les fonctionnalités implémentées (cocher ✅ ou ajouter)
> - Les nouvelles fonctions/utilitaires ajoutés dans `app.py`
> - Les modifications de schéma SQL
> - Les changements dans les templates
> - La section « Prochaines étapes » si nécessaire
> - La date de dernière mise à jour en bas de fichier
>
> **Si l'oubli est constaté** : mettre à jour la note **immédiatement** avant de continuer tout autre travail.

> 🔴 **CONSIGNES SPÉCIFIQUES POUR L'AI (Codebuff/Freebuff/Buffy) :**
>
> Tu as une **tendance documentée** à oublier de mettre à jour cette note. Voici des garde-fous :
> - **Après chaque `str_replace` ou `write_file`** sur un fichier du projet, demande-toi : « Est-ce que la note de session doit être mise à jour suite à ce changement ? »
> - **Avant de dire « Done! » ou « Terminé ! »** : relis la note et vérifie que tout est documenté
> - **Ne dis JAMAIS « all done » sans avoir d'abord vérifié et mis à jour la note de session**
> - Si tu modifies `app.py`, `schema.sql`, un template, ou `seed_data.sql`, la note DOIT être mise à jour

---

## 🎯 Objectif du projet

Créer une **application web unifiée de suivi patient** (TB + VIH) pour l'**infirmerie de la Maison Centrale de Mahajanga**, en remplaçant deux fichiers HTML autonomes par une seule application Flask + SQLite.

**Contraintes :**
- 100% local (pas d'internet requis)
- Design cohérent avec les fichiers existants (CSS navy + violet)
- Uniquement le suivi patient (pas de gestion médicaments/stocks)
- Architecture technique : Flask + SQLite (même stack que GestionStock Pharma)

---

## 📜 Prompts originaux de l'utilisateur

> Ces prompts définissent les exigences exactes du projet. Les respects lors de chaque étape.

### Prompt initial (contexte général)

```
Nous allons construire une application de suivi patient (TB et VIH) pour
l'infirmerie de la Maison Centrale de Mahajanga, en remplaçant deux
fichiers HTML autonomes existants par une seule application unifiée.

Fichiers de référence à lire d'abord :
- 07-2026_SUIVI_TB.html
- 07-2026_pvvih.html

RÈGLE ABSOLUE SUR LE DESIGN :
Ne réinvente pas le style visuel. Reprends exactement les variables CSS,
les classes (.stat, .badge, .panel, .rappel-row, .toolbar, etc.) et la
palette de couleurs déjà présentes dans ces deux fichiers. Si les deux
fichiers diffèrent (bleu marine TB vs violet PVVIH), garde le bleu
marine comme couleur de base de l'application et utilise le violet
uniquement comme accent pour distinguer le programme VIH.

Contraintes générales de style à respecter partout :
- Pas de dégradés, pas d'ombres lourdes
- Bordures fines (0.5-1px), coins arrondis modérés (8-12px)
- Une seule couleur d'accent dominante par écran
- Espacement généreux, jamais de contenu tassé

Portée du projet : uniquement le suivi patient (identité, statut
d'incarcération, suivi clinique TB/VIH, rapports). Rien sur la gestion
des médicaments ou des stocks.

Architecture technique : Flask + SQLite + Bootstrap 5 (même stack que
GestionStock Pharma), stockage 100% local.

Nous allons procéder par étapes. Ne commence aucun code tant que je ne
te donne pas l'étape 1. Confirme que tu as bien lu et compris les deux
fichiers de référence et résume en 5 lignes le style visuel que tu vas
reprendre.
```

### Étape 1 — Modèle de données

```
Étape 1 : modèle de données uniquement (pas d'interface pour l'instant).

Crée le schéma SQLite avec :

Table patients (dossier unique, commun aux deux programmes) :
- id, nom, prénoms, date de naissance ou âge, sexe
- statut actuel : incarcéré / libéré / transféré / décédé
- quartier/situation pénale
- téléphone, adresse (renseignés surtout à la sortie)
- personne de contact (nom + téléphone)
- date de création, dernière modification, auteur de la modification

Table historique_statut :
- patient_id, ancien statut, nouveau statut, date, motif

Table suivi_tb :
- patient_id, date début traitement, forme clinique, type de cas
- poids à M0/M2/M5/M6
- contrôles bactériologiques M2/M5/M6 : date prévue, date faite, résultat
- décision finale (guéri / traitement terminé / échec / décès /
  perdu de vue / transféré), date de la décision

Table suivi_vih :
- patient_id, date de début de suivi
- rendez-vous : date prévue, date faite, statut (fait/manqué)
- observation

Table journal_audit :
- table concernée, id concerné, action, ancien/nouveau contenu,
  auteur, date

Explique-moi le schéma en langage simple avant d'écrire le code SQL,
je veux valider la logique avant que tu l'implémentes.
```

### Étape 2 — Dashboard et liste des patients

```
Étape 2 : dashboard et liste des patients, en réutilisant strictement
le style CSS des fichiers de référence (variables --navy, --teal,
--border, classes .stat, .badge, .table-wrap, etc.)

Dashboard :
- Cartes de stats : patients actifs, TB en cours, VIH suivis,
  contrôles en retard (calculés dynamiquement, pas saisis à la main)
- Liste des contrôles en retard et RDV manqués (recherche active)

Liste des patients :
- Recherche par nom/ID, filtre par statut (incarcéré/libéré/transféré),
  filtre par programme (TB/VIH/les deux)
- Colonne "prochain contrôle" avec alerte visuelle si retard
- Clic sur une ligne ouvre la fiche patient

Ne me montre le résultat qu'une fois cette étape terminée, je testerai
dans le navigateur avant qu'on continue.
```

---

## 📁 Structure du projet

```
07-2026-07/
├── app.py                    ← Application Flask (routes)
├── schema.sql                ← Schéma SQLite (7 tables + indexes)
├── seed_data.sql             ← Données de démonstration
├── init_db.py                ← Script initialisation DB
├── requirements.txt          ← Flask≥3.0
├── suivi_patients.db         ← Base de données SQLite
├── migrate_registre.py       ← Migration ajout numéros de registre
├── migrate_settings.py       ← Migration ajout table settings
├── migrate_import_ancien.py  ← Import des données de l'ancienne app PVVIH
├── migrate_import_ancien_tb.py ← Import des données de l'ancienne app TB
├── migrate_nettoyage.py      ← Purge données test + renumérotation registres
├── migrate_ctrl_dates_vides.py ← Remplissage auto dates contrôles TB vides (M2/M5/M6)
├── launcher.py               ← Lanceur (double-clic, vérifie port, ouvre navigateur)
├── stop_server.py            ← Arrêt propre du serveur
├── suivi_patient.png         ← Icône de l'application
├── Suivi Patient.desktop     ← Raccourci Bureau Linux (lancement)
├── Arrêter Suivi Patient.desktop ← Raccourci Bureau Linux (arrêt)
├── LISEZ-MOI.txt             ← Instructions simples pour utilisateurs
├── generate_icon.py          ← Génération icône PNG (Pillow)
├── NOTE_DE_SESSION.md        ← CETTE NOTE (à mettre à jour)
│
├── 07-2026_pvvih.html        ← Ancien fichier VIH (référence)
├── 07-2026_SUIVI_TB.html     ← Ancien fichier TB (référence)
├── suivi_pvvih_export.csv    ← Ancien export CSV
├── suivi_pvvih_export.pdf    ← Ancien export PDF
├── suivi_pvvih_sauvegarde.json
├── suivi_tb_sauvegarde.json
│
└── templates/
    ├── base.html             ← Layout + CSS complet
    ├── login.html            ← Page de connexion
    ├── dashboard.html        ← Page d'accueil
    ├── patients.html         ← Liste + modals
    ├── patient_detail.html   ← Fiche patient détaillée
    ├── rapports.html         ← Rapports mensuels
    ├── sauvegarde.html       ← Export/Import données
    ├── patients_print.html   ← Liste patients imprimable (NB formel)
    ├── patient_print.html    ← Fiche patient imprimable (NB formel)
    ├── audit.html            ← Journal d'audit (filtres + pagination)
    ├── aide.html             ← Guide d'utilisation (11 sections accordéon)
    └── parametres.html       ← Paramétrage (org, clinique, users, rapports, données)
```

---

## 🗄️ Base de données SQLite

### Tables

| Table | Rôle | Relations |
|-------|------|-----------|
| `patients` | Dossier unique (identité, statut pénitentiaire, contact) | — |
| `historique_statut` | Journal des changements de statut | → patients |
| `suivi_tb` | Volet tuberculose (poids, contrôles, décision) | → patients (1:1) |
| `suivi_vih` | Volet VIH (date début, observation) | → patients (1:1) |
| `journal_audit` | Piste d'audit | — |
| `users` | Utilisateurs (authentification : admin/user/readonly) | — |
| `settings` | Paramètres de l'application (clé-valeur) | — |

### Schéma `patients` (table centrale)

```sql
id, nom, prenoms, date_naissance, age, sexe,
statut (incarcere/libere/transfere/decede),
quartier, situation_penale,
telephone, adresse, contact_nom, contact_tel,
created_at, updated_at, created_by
```

### Schéma `suivi_tb`

```sql
patient_id, numero_registre (TB-AAAA-NNN), lab_id (N° laboratoire),
date_debut_traitement, forme_clinique (TPB+/TPB-/TEP),
type_cas (Nouveau/Echec/Rechute/Reprise/Transfert entrant),
poids_m0, poids_m2, poids_m5, poids_m6,
ctrl_m2_date, ctrl_m2_fait, ctrl_m2_resultat,
ctrl_m5_date, ctrl_m5_fait, ctrl_m5_resultat,
ctrl_m6_date, ctrl_m6_fait, ctrl_m6_resultat,
decision (Guéri/Terminé/Echec/Perdu de vue/Décédé/Transféré), date_decision
```

### Schéma `suivi_vih`

```sql
patient_id, numero_registre (VIH-AAAA-NNN), code (DDMMYY+3lettresNOM+2lettresPRENOMS, auto-généré),
date_debut_suivi, observation (Nouveau/Transfert/Libéré/Décédé)
```

---

## 🚀 Comment lancer l'application

### Méthode 1 : Double-clic (recommandé)
- **Double-cliquez** sur « Suivi Patient » sur le Bureau
- Le serveur démarre automatiquement, le navigateur s'ouvre
- Pour arrêter : double-cliquez sur « Arrêter Suivi Patient » ou fermez la fenêtre noire
- Un fichier `LISEZ-MOI.txt` est présent sur le Bureau avec les instructions

### Méthode 2 : Terminal
```bash
# Depuis le dossier du projet
cd /home/berthin/Bureau/09_SUIVI_VIH/2026-07

# Initialiser la base (une seule fois)
python3 init_db.py

# Lancer le serveur
python3 app.py

# Ouvrir dans le navigateur
# → http://localhost:5000
```

### Fichiers de lancement
| Fichier | Rôle |
|---------|------|
| `launcher.py` | Démarre le serveur + ouvre le navigateur (vérifie si déjà lancé) |
| `stop_server.py` | Arrête le serveur proprement (SIGTERM → SIGKILL) |
| `Suivi Patient.desktop` | Raccourci Bureau Linux (à copier dans ~/Bureau/) |
| `Arrêter Suivi Patient.desktop` | Raccourci d'arrêt (à copier dans ~/Bureau/) |
| `suivi_patient.png` | Icône de l'application |
| `LISEZ-MOI.txt` | Instructions simples pour les utilisateurs |

---

## 📊 Ce qui est déjà fait (Étape 2)

### Routes Flask

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/` | GET | Dashboard (stats + alertes) | ✅ |
| `/patients` | GET | Liste avec recherche/filtres (dont date) | ✅ |
| `/patients/print` | GET | Liste imprimable (mêmes filtres, noir & blanc, formelle) | ✅ |
| `/patient/<id>` | GET | Détail patient (JSON) | ✅ |
| `/patient/create` | POST | Création patient | ✅ |
| `/rapports` | GET | Page rapports | ✅ |
| `/sauvegarde` | GET | Page sauvegarde | ✅ |
| `/sauvegarde/export-csv` | GET | Export CSV | ✅ |
| `/sauvegarde/export-json` | GET | Export JSON | ✅ |
| `/sauvegarde/import-json` | POST | Import JSON | ✅ |
| `/patient/<id>/edit` | POST | Modifier patient | ✅ |
| `/login` | GET/POST | Connexion | ✅ |
| `/logout` | GET | Déconnexion | ✅ |
| `/patient/<id>/ctrl` | POST | Marquer contrôle TB | ✅ |
| `/patient/<id>/statut` | POST | Changer le statut | ✅ |
| `/patient/<id>/poids` | POST | Modifier les poids TB | ✅ |
| `/patient/<id>/tb/update` | POST | Modifier contrôles TB | ✅ |
| `/patient/<id>/tb/lab` | POST | Modifier N° laboratoire TB | ✅ |
| `/patient/<id>/vih/code` | POST | Modifier code VIH | ✅ |
| `/patient/<id>/delete` | POST | Supprimer un patient | ✅ |
| `/patient/<id>/add-tb` | POST | Ajouter un volet TB à un patient existant | ✅ |
| `/patient/<id>/add-vih` | POST | Ajouter un volet VIH à un patient existant | ✅ |
| `/patient/<id>/print` | GET | Fiche patient imprimable (A4, noir & blanc, formelle) | ✅ |
| `/audit` | GET | Journal d'audit (filtres + pagination) | ✅ |
| `/aide` | GET | Guide d'utilisation (11 sections accordéon) | ✅ |
| `/parametres` | GET/POST | Paramétrage (organisation, clinique, users, rapports, données) | ✅ |

### Fonctionnalités implémentées

**Système de numérotation :**
- ✅ Numéros de registre par programme : `TB-AAAA-NNN` et `VIH-AAAA-NNN`
- ✅ Compteur indépendant par programme, remis à zéro chaque année civile
- ✅ Numéro généré automatiquement à la création du volet
- ✅ `patients.id` reste la clé technique interne (invisible dans l'interface)
- ✅ Affichage des registres dans la liste patients, fiche patient, dashboard
- ✅ Recherche par numéro de registre
- ✅ Export CSV avec numéros de registre
- ✅ Boutons "+ Ajouter un suivi TB/VIH" sur la fiche patient si pas de volet actif
- ✅ Migration script pour les données existantes (`migrate_registre.py`)

**Import des données de l'ancienne application VIH (`migrate_import_ancien.py`) :**
- ✅ Import fusion (INSERT uniquement, aucune suppression) depuis `suivi_pvvih_sauvegarde.json` (14 patients)
- ✅ IDs conservés (`PVVIH-2026-NNN`) pour traçabilité, numéros de registre `VIH-2026-NNN` générés à la suite
- ✅ Codes VIH générés automatiquement (DDMMYY + initiales, année calculée depuis `birthYear`)
- ✅ Nom découpé en nom/prénoms (token le plus long = nom de famille)
- ✅ `observation='Libéré'` → statut `libere`, sinon `incarcere` ; quartiers conservés
- ⚠️ Champs absents de l'ancienne app, laissés vides : `date_debut_suivi` (NULL) et `situation_penale` ('') pour les 14 patients — à compléter (l'UI permet de modifier le code VIH mais pas encore la date de début de suivi)
- ⚠️ `suivi_tb_sauvegarde.json` contient en réalité un export VIH (13 patients, doublon partiel de `suivi_pvvih_sauvegarde.json`) — l'import utilise le fichier complet (14)
- 🛟 Sauvegarde de la base avant import : `suivi_patients.db.bak-avant-import`

**Purge des données de test (`migrate_nettoyage.py`) :**
- ✅ Suppression de TOUTES les données antérieures à la migration (patients PAT-* de démonstration/test, suivis TB/VIH, historiques, audits) — seuls les 14 patients réels importés (PVVIH-*) sont conservés
- ✅ Renumérotation des registres VIH depuis 001 : `VIH-2026-002..015` → `VIH-2026-001..014` (tri par patient)
- ✅ Base actuelle : 14 patients VIH réels, 0 TB
- 🛟 Sauvegarde avant purge : `suivi_patients.db.bak-avant-purge`

**Import des données TB de l'ancienne application (`migrate_import_ancien_tb.py`) :**
- ✅ Import fusion (INSERT uniquement) depuis `suivi_tb_sauvegarde (1).json` — 44 patients TB réels (PAT-2026-001..044, tous TPB+)
- ✅ IDs conservés (PAT-2026-NNN), numéros de registre `TB-2026-001..044` générés à la suite
- ✅ Âge et poids convertis en numérique (le fichier les stockait en texte)
- ✅ Normalisations : `Prévenue` → `Prévenu` (situation pénale), `Non évalué ou transféré` → `Transféré` (décision) ; `Décédé` → statut `decede`
- ⚠️ Champs absents de l'ancienne app laissés vides : quartier, téléphone, adresse, contact, date_naissance, dateMD (absent du schéma), résultat des contrôles
- ⚠️ Le fichier `suivi_tb_sauvegarde.json` (sans « (1) ») est un export VIH — le script refuse ce format et ne peut pas l'importer
- 🛟 Sauvegarde avant import TB : `suivi_patients.db.bak-avant-import-tb`
- ✅ Base actuelle : 58 patients (44 TB + 14 VIH)

**Pagination de la liste patients :**
- ✅ Liste paginée côté serveur (10 patients/page par défaut, paramètre `per_page`, `page`)
- ✅ Navigation numérotée (Précédent / pages / Suivant) avec ellipse, en conservant filtres et tri
- ✅ Colonne « N° » avec numérotation continue des patients sur toutes les pages
- ✅ Compteur « N patient(s) · page X/Y » ; retour page 1 au changement de filtre/tri ; page hors bornes rabattue sur la dernière
- ✅ Impression (`/patients/print`) inchangée : imprime tous les patients filtrés, sans pagination

**Code VIH auto-généré :**
- ✅ Fonction `generate_vih_code()` : format `DDMMYY` + 3 premières lettres NOM + 2 premières lettres PRÉNOMS
- ✅ Génération automatique lors de la création patient (wizard étape 4, programme VIH)
- ✅ Génération automatique lors de l'ajout d'un volet VIH à un patient existant
- ✅ Aperçu en temps réel du code dans le wizard et le modal d'ajout
- ✅ Règles : date naissance renseignée → JJMM-AA ; pas de date → `0101` + année calculée depuis l'âge ; pas de prénoms → `XX`
- ✅ Suppression des accents (é→E, ç→C, etc.)
- ✅ Affichage du code dans la liste patients et la fiche patient
- ✅ Données de démonstration avec codes générés (120490RAKJE, etc.)

**Dates de contrôle TB auto-calculées (M2/M5/M6) :**
- ✅ Règle de calcul : `M2 = date_debut_traitement + 2 mois`, `M5 = +5 mois`, `M6 = +6 mois`
- ✅ Helpers dans `app.py` : `add_months(date, n)` (arithmétique calendrier, gère fins de mois et années bissextiles) et `tb_control_dates(date_debut)` → (M2, M5, M6)
- ✅ Calcul + enregistrement automatiques dans `ctrl_m2_date`/`ctrl_m5_date`/`ctrl_m6_date` à la **création** du volet TB (wizard `create_patient` + `/patient/<id>/add-tb`) — aucune saisie manuelle nécessaire
- ✅ Les dates restent **modifiables manuellement** au cas par cas (modal « Modifier les contrôles » pré-rempli avec les dates calculées)
- ✅ **Pas de recalcul après coup** : le calcul n'a lieu qu'à l'INSERT ; aucune route ne met à jour `date_debut_traitement`, donc la modification ultérieure de la date de début n'écrase jamais les dates de contrôle déjà générées
- ✅ La règle s'applique à **tous les nouveaux cas** (les deux seuls chemins de création du volet TB sont couverts) ; l'import JSON de sauvegarde restaure les données telles quelles (ce n'est pas un nouveau cas)
- ✅ Rétroactivité : `migrate_ctrl_dates_vides.py` a rempli les dates **vides** des cas existants (46 M5 + 49 M6 remplies, 0 restante), sans jamais écraser les dates déjà saisies — 🛟 sauvegarde `suivi_patients.db.bak-avant-ctrl-auto`

**Dashboard :**
- ✅ 4 cartes stats cliquables sur une seule ligne : Patients actifs → `/patients`, TB en cours → `/patients?programme=TB`, VIH suivis → `/patients?programme=VIH`, Contrôles en retard → scroll vers la section des retards (les anciennes alert-cards redondantes ont été supprimées)
- ✅ Lien « Voir le rapport de [mois courant] » dans la barre de titre → `/rapports?mois=…&annee=…` (mois courant pré-sélectionné)
- ✅ Blur des noms VIH dans les listes du dashboard (même règle que `/patients` : flou + bouton œil + mot de passe via `/api/verify-password`, readonly sans bouton) — `compute_overdue_tb` renvoie un flag `has_vih` (EXISTS sur `suivi_vih` actif)
- ✅ Section « Échéances des 7 prochains jours » (contrôles TB à venir) : repliée par défaut derrière le lien « Afficher », triée par date croissante ; les sections urgentes (retards) restent dépliées
- ✅ Alertes contrôles TB en retard (calculé dynamiquement)

**Liste patients :**
- ✅ Recherche par nom/N° registre/prénoms/code VIH/N° labo
- ✅ Filtre par statut (incarcéré/libéré/transféré/décédé)
- ✅ Filtre par programme (TB/VIH/les deux)
- ✅ Filtre par tranche d'âge (<18, 18-35, 35-60, 60+)
- ✅ Filtre par sexe (Tous/M/F)
- ✅ Filtre par quartier (généré dynamiquement depuis la base)
- ✅ Filtre par décision TB (En cours/Guéri/Terminé/Échec/Perdu de vue/Décès/Transféré)
- ✅ Case à cocher "Retards uniquement" (contrôles TB en retard)
- ✅ Filtre par période (date début traitement/suivi)
- ✅ Tous les filtres combinables (ET logique) et persistants dans l'URL
- ✅ Tri cliquable sur colonnes Âge et Prochain contrôle (asc/desc avec flèche)
- ✅ Badges colorés (TB bleu, VIH violet, statuts pastel)
- ✅ Colonne N° registre (TB-AAAA-NNN / VIH-AAAA-NNN)
- ✅ Colonne Code VIH (affiché en violet)
- ✅ Colonne Âge (calculé automatiquement depuis date_naissance)
- ✅ Colonne prochain contrôle avec alerte si retard
- ✅ Noms VIH masqués (flou) + bouton révéler (admin/user, mot de passe requis)
- ✅ Bouton "Imprimer" (impression noir & blanc formelle, mot de passe requis si VIH)

**Fiche patient :**
- ✅ Page détaillée complète (identité, TB, VIH, historique)
- ✅ Numéros de registre TB/VIH affichés dans l'en-tête et topbar
- ✅ Âge calculé automatiquement depuis date_naissance
- ✅ Durée traitement TB calculée automatiquement
- ✅ Timeline visuelle TB (M0/M2/M5/M6)
- ✅ Bouton "Modifier" avec formulaire pré-rempli
- ✅ Bouton "Changer le statut" avec formulaires contextuels
- ✅ Contrôles TB avec boutons "Marquer fait" + résultat
- ✅ Poids modifiables (M0/M2/M5/M6)
- ✅ Bouton "Modifier N° labo" TB
- ✅ Bouton "Modifier le code VIH" (code auto-généré, modifiable manuellement)
- ✅ Bouton "+ Ajouter un suivi TB" si pas de volet actif
- ✅ Bouton "+ Ajouter un suivi VIH" si pas de volet actif

**Création patient :**
- ✅ **Wizard multi-étapes** (5 étapes : Identité → Statut → Contact → Programme → Résumé)
- ✅ Barre de progression visuelle avec points et lignes
- ✅ Validation à chaque étape avant de passer à la suivante
- ✅ Champs conditionnels (contact obligatoire si libéré/transféré, sous-formulaires TB/VIH)
- ✅ Résumé de confirmation avant enregistrement (étape 5)
- ✅ Annulation impossible par accident (bouton Annuler obligatoire)
- ✅ Validation côté client et serveur
- ✅ Audit automatique
- ✅ Génération automatique du numéro de registre (TB-AAAA-NNN ou VIH-AAAA-NNN)

**Champs obligatoires (tous les patients sont des détenus) :**
- ✅ Statut pré-rempli à **« Incarcéré »** par défaut dans le wizard (étape 2)
- ✅ **Situation pénale** (Condamné/Prévenu) désormais obligatoire (wizard + édition + validation serveur)
- ✅ Validation serveur renforcée dans `create_patient` : nom, sexe, âge/date de naissance, situation pénale, téléphone+adresse si libéré/transféré, et champs TB/VIH (date de début, forme clinique, type de cas)
- ✅ Validation serveur dans `edit_patient` : nom + situation pénale obligatoires

### Données de démonstration

- **Chargées** depuis `seed_data.sql` : 8 patients, 5 suivis TB, 3 suivis VIH
- 2 utilisateurs : admin (admin/admin123) + visiteur (readonly)
- Les numéros de registre sont pré-assignés dans le seed (TB-2025-001, VIH-2024-001, etc.)

---

## 📝 Prochaines étapes (à faire)

### Étape 3 — Fiche patient détaillée

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>` | GET | Fiche patient complète (HTML) | ✅ |
| `/patient/<id>/ctrl` | POST | Marquer contrôle TB fait | ✅ |
| `/patient/<id>/statut` | POST | Changer le statut | ✅ |

**Fonctionnalités implémentées :**
- ✅ En-tête identité + badge statut coloré + numéros de registre
- ✅ Timeline visuelle TB (M0/M2/M5/M6) avec code couleur
- ✅ Modal "Enregistrer un contrôle" avec résultat
- ✅ Modal "Changer le statut" avec formulaires spécifiques :
  - Transfert → fiche de transfert médical
  - Libération → fiche de sortie (adresse, tel, contact, structure)
  - Décès → date et cause
- ✅ Historique des changements de statut visible en bas de fiche
- ✅ Patients.html : clic sur ligne → page détaillée (plus de modal)
- ✅ Bouton "+ Ajouter un suivi TB" si pas de volet TB actif
- ✅ Bouton "+ Ajouter un suivi VIH" si pas de volet VIH actif
- ✅ Modals d'ajout TB/VIH avec génération automatique du numéro de registre

### Étape 4 — Rapport mensuel dynamique

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/rapports` | GET | Page rapports avec sélecteur mois/année | ✅ |

**Fonctionnalités implémentées :**
- ✅ Sélecteur mois/année avec defaults (mois/année actuels)
- ✅ Statistiques TB : actifs, nouveaux cas, sorties, décès, transferts
- ✅ **Répartition des issues TB du mois** (guéri/terminé/échec/perdu de vue/décès/transféré)
- ✅ **Taux de réalisation des contrôles bactériologiques** du mois (faits/prévus %)
- ✅ **Répartition par forme clinique** (TPB+/TPB-/TEP) et type de cas (nouveau/rechute/etc.)
- ✅ Statistiques VIH : actifs, nouveaux cas, sorties, décès
- ✅ **Section démographique** : répartition par tranche d'âge, sexe, quartier (barres sobres)
- ✅ **Note de traçabilité** (date + utilisateur éditeur)
- ✅ **Zone de signature** (PDF uniquement) : Chef d'Établissement + Infirmier-Major
- ✅ Export PDF avec en-tête officiel (Maison Centrale, DRAP BOENY, DHDPRS/SSPD)
- ✅ Mécanisme d'impression (fenêtre → save as PDF)
- ✅ Lien "Rapports" ajouté à la topbar

### Étape 5 — Page Sauvegarde

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/sauvegarde` | GET | Page sauvegarde (stats + export/import) | ✅ |
| `/sauvegarde/export-csv` | GET | Export CSV des patients | ✅ |
| `/sauvegarde/export-json` | GET | Export JSON complet (toutes tables) | ✅ |
| `/sauvegarde/import-json` | POST | Import JSON (restauration) | ✅ |

**Fonctionnalités implémentées :**
- ✅ Page `/sauvegarde` avec statistiques de la base (6 compteurs)
- ✅ Export CSV (format `;`, BOM UTF-8, compatible Excel) avec numéros de registre TB/VIH
- ✅ Export JSON complet (toutes les tables, horodaté)
- ✅ Import JSON avec remplacement complet (confirmation obligatoire)
- ✅ Lien "Sauvegarde" ajouté à la topbar
- ✅ Interface avec choix de fichier, feedback visuel, confirmation avant import

### Étape 6 — Édition patient

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>/edit` | POST | Modifier les informations patient | ✅ |

**Fonctionnalités implémentées :**
- ✅ Bouton "✏ Modifier" dans l'en-tête de la fiche patient
- ✅ Modal d'édition avec formulaire pré-rempli (nom, prénoms, DOB, âge, sexe, quartier, situation pénale)
- ✅ Section contact modifiable (téléphone, adresse, contact)
- ✅ Mise à jour automatique du `updated_at`
- ✅ Audit automatique (ancien/nouveau contenu)

### Étape 7 — Gestion des contrôles TB

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>/ctrl` | POST | Marquer contrôle TB fait | ✅ |
| `/patient/<id>/poids` | POST | Modifier les poids | ✅ |
| `/patient/<id>/tb/update` | POST | Modifier dates/résultats contrôles | ✅ |

**Fonctionnalités implémentées :**
- ✅ Boutons "Marquer M2/M5/M6 fait" avec sélecteur de résultat
- ✅ Modal "Modifier les poids" (M0/M2/M5/M6)
- ✅ Modal "Modifier les contrôles" (dates + résultats)
- ✅ Timeline visuelle avec code couleur (vert = fait, gris = en attente)

### ~~Étape 8 — Gestion des RDV VIH~~ (SUPPRIMÉE)

> ❌ **Fonctionnalité entièrement supprimée (05/09/2026)** : les patients VIH n'ont pas de rendez-vous.
> - Table `rendez_vous` supprimée du schéma et de la base
> - Route `/patient/<id>/rdv` supprimée
> - Sections supprimées : agenda RDV (fiche patient), alertes dashboard (RDV manqués / à venir), stats rapports (taux de RDV honorés, recherche active), paramètre « Intervalle RDV VIH », compteurs sauvegarde
> - `seed_data.sql`, `init_db.py`, export/import JSON mis à jour

### Étape 9 — Changement de statut

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>/statut` | POST | Changer le statut | ✅ |

**Fonctionnalités implémentées :**
- ✅ Modal "Changer le statut" avec formulaires contextuels :
  - Libération → fiche de sortie (adresse, tel, contact, structure)
  - Transfert → fiche de transfert médical (destination, motif)
  - Décès → date et cause
- ✅ Enregistrement automatique dans `historique_statut`
- ✅ Audit automatique

### Étape 10 — Authentification & Sessions

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/login` | GET/POST | Page de connexion | ✅ |
| `/logout` | GET | Déconnexion | ✅ |

**Fonctionnalités implémentées :**
- ✅ Page de connexion (`login.html`) avec design cohérent
- ✅ Table `users` ajoutée au schéma (username, password_hash, role)
- ✅ 2 utilisateurs par défaut :
  - `admin` / `admin123` — rôle `admin` (accès complet)
  - `visiteur` / `visiteur123` — rôle `readonly` (lecture seule)
- ✅ Décorateur `login_required` sur toutes les routes
- ✅ Décorateur `role_required('admin', 'user')` sur les routes d'écriture
- ✅ Redirect automatique vers `/login` si non connecté
- ✅ Sessions Flask (cookie-based, secret key aléatoire)
- ✅ Audit mis à jour : auteur = utilisateur connecté (plus de "utilisateur" en dur)
- ✅ Sidebar affiche nom + rôle + bouton déconnexion
- ✅ `current_user()` pour l'auteur des audits
- ✅ Mots de passe hashés avec `werkzeug.security`
- ✅ Templates adaptatifs : boutons d'action masqués pour les readonly
- ✅ Badge "👁 Lecture seule" pour les utilisateurs readonly
- ✅ API retourne 403 "Accès refusé" pour les écritures non autorisées

### Étape 10b — Suppression patient

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>/delete` | POST | Supprimer un patient (admin only) | ✅ |

**Fonctionnalités implémentées :**
- ✅ Bouton "🗑 Supprimer" dans l'en-tête de la fiche patient (admin uniquement)
- ✅ Modal de confirmation avec saisie de l'identité du patient
- ✅ Bouton désactivé tant que la saisie ne correspond pas exactement à l'ID
- ✅ Suppression cascade (TB, VIH, historique, audit)
- ✅ Audit automatique avant suppression
- ✅ Redirection vers la liste après suppression

### Étape 10c — Paramétrage

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/parametres` | GET/POST | Page de paramétrage | ✅ |

**Fonctionnalités implémentées :**
- ✅ **Identité organisation** : nom établissement, DRAP, destinataire, service (utilisé dans les rapports)
- ✅ **Paramètres cliniques** : mois contrôles TB, seuil de retard
- ✅ **Paramètres de rapport** : affichage zone de signature, note d'en-tête
- ✅ **Gestion des données** : rétention audit (mois), archivage patients inactifs
- ✅ **Changement de mot de passe** (utilisateur courant)
- ✅ **Gestion utilisateurs** (admin uniquement) :
  - Liste des utilisateurs avec rôle/statut
  - Création d'utilisateur (nom, rôle, mot de passe)
  - Édition (nom d'utilisateur, nom complet, rôle, actif/inactif)
  - Réinitialisation du mot de passe
  - Suppression d'utilisateur (sauf soi-même)
  - Documentation des droits par rôle (admin/user/readonly)
- ✅ **Confidentialité VIH** :
  - Noms masqués (flou) pour les patients VIH dans la liste
  - Bouton "Œil" pour révéler (admin/user uniquement, requiert mot de passe)
  - Readonly : pas de bouton Œil, pas d'accès API (403)
  - Impression bloquée si patients VIH présents (mot de passe requis)
- ✅ API `/api/verify-password` (POST JSON, bloque readonly)
- ✅ **Âge calculé automatiquement** depuis date_naissance (today - DOB), fallback sur âge manuel si DOB inconnue
- ✅ Lien "Paramètres" visible uniquement pour les admins dans la topbar
- ✅ Table `settings` ajoutée (clé-valeur) avec migration (`migrate_settings.py`)
- ✅ 12 paramètres par défaut pré-remplis

### Étape 11 — Impression fiche patient

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/patient/<id>/print` | GET | Fiche patient imprimable (A4, noir & blanc) | ✅ |

**Fonctionnalités implémentées :**
- ✅ Page imprimable indépendante (`patient_print.html`, n'étendant pas `base.html`)
- ✅ Style noir & blanc formel (A4, `@page { margin: 18mm; }`)
- ✅ En-tête officiel (Maison Centrale, DRAP BOENY, DHDPRS/SSPD)
- ✅ Section Identité complète (nom, sexe, DOB, âge, quartier, situation pénale, statut)
- ✅ Section Contact (téléphone, adresse, personne de contact)
- ✅ Section Suivi TB (registre, labo, forme clinique, type de cas, durée, décision)
- ✅ Timeline TB visuelle (M0/M2/M5/M6) avec code couleur noir & blanc
- ✅ Poids aux différentes étapes
- ✅ Section Suivi VIH (registre, code, date début, observation)
- ✅ Historique des changements de statut (tableau)
- ✅ Zone de signature (Chef d'Établissement + Infirmier-Major)
- ✅ Bouton "Imprimer" ajouté à la fiche patient (`patient_detail.html`)
- ✅ Paramètres organisation injectés (org_name, org_drapp, org_destinator, org_service)

### Étape 12 — Journal d'audit

| Route | Méthode | Description | Statut |
|-------|---------|-------------|--------|
| `/audit` | GET | Journal d'audit (filtres + pagination) | ✅ |

**Fonctionnalités implémentées :**
- ✅ Page `/audit` accessible depuis la topbar (admin uniquement)
- ✅ Tableau complet des entrées : date, action, table cible, ID cible (lien vers fiche patient), auteur
- ✅ Filtres combinables : table (Patients/Suivi TB/Suivi VIH), action (Création/Modification/Suppression), auteur, recherche texte
- ✅ Chips de filtres actifs avec bouton × pour retirer individuellement
- ✅ Pagination côté serveur (20 entrées/page) avec navigation numérotée
- ✅ Détails expandables par entrée (ancien/nouveau contenu en JSON)
- ✅ Badges colorés par action (vert=création, bleu=modification, rouge=suppression)
- ✅ Lien direct vers la fiche patient depuis l'ID cible

### Étape 13 — Finalisation

**Tests effectués (06/09/2026) :**
- ✅ Toutes les routes GET retournent 200 (dashboard, patients, patient detail, print, rapports, sauvegarde, audit, parametres)
- ✅ Toutes les opérations CRUD (création, édition, suppression patient)
- ✅ Workflows TB/VIH (ajout volet, marquer contrôles, modifier poids, modifier labo, modifier code VIH)
- ✅ Changement de statut avec formulaires contextuels
- ✅ Authentification (login/logout, sessions)
- ✅ Accès basé sur les rôles (admin vs readonly)
- ✅ Export CSV et JSON
- ✅ Filtres et pagination patients
- ✅ Page audit avec filtres et pagination
- ✅ Liens topbar (Dashboard, Patients, Rapports, Sauvegarde, Audit, Paramètres)

**Statut final :**
- 58 patients (44 TB + 14 VIH)
- 90+ entrées d'audit
- Application fonctionnelle et prête à l'emploi
- Aucune dépendance internet requise (100% offline)

---

## 🎨 Design — Palette Apple

**Mode clair :**
- Blue (primary) : `#007AFF` (boutons, focus, accents)
- Violet (VIH) : `#AF52DE` (badges VIH)
- Teal : `#30B0C7` (sections)
- Fond : `#F2F2F7`, Surface : `#FFFFFF`, Bordures : `#E5E5EA`

**Mode sombre :**
- Blue : `#0A84FF`, Violet : `#BF5AF2`, Teal : `#40C8E0`
- Fond : `#000000`, Surface : `#1C1C1E`, Bordures : `#38383A`
- Texte : `#F5F5F7`, Secondaire : `#98989D`
- Badges : fond semi-transparent (#0A84FF22), bordure subtile
- Toggle via menu profil (icône lune/soleil), persisté en localStorage
- Basculable instantanément sans rechargement

**Status colors :**
- Vert : `#34C759` (clair) / `#30D158` (sombre)
- Rouge : `#FF3B30` (clair) / `#FF453A` (sombre)
- Orange : `#FF9500` (clair) / `#FF9F0A` (sombre)

**Règles métier :**
- Âge toujours calculé depuis date_naissance (today - DOB), fallback sur champ manuel si DOB inconnue
- Noms patients VIH masqués par défaut (flou), révélation par mot de passe (admin/user uniquement)
- Readonly : aucune visibilité sur les noms VIH

**Texte :**
- Primaire : `#1D1D1F`, Secondaire : `#8E8E93`, Tertiaire : `#AEAEB2`

**Style :**
- Top navigation bar : frosted glass (backdrop-filter blur), 3 liens directs (Dashboard, Patients, Rapports), icône Aide (help-circle), menu profil déroulant (avatar + nom + rôle cliquable) contenant les liens selon le rôle + Déconnexion
- Modals : bottom sheet (slide-up) avec grabber
- Bordures : 0.5px subtils, pas de bordures lourdes
- Ombres : subtiles (0.5px + 3px)
- Animations : cubic-bezier Apple-style
- Coins arrondis : 10-16px
- Font : **Inter** (OFL, embeddée en base64 dans base.html + login.html), fallback SF Pro / system fonts
- 0 dépendance CDN, 100% offline
- Icônes : SVG inline embarquées (sprite dans base.html, fill="currentColor", style outline), 16-24px
- Aucune dépendance CDN, tout fonctionne 100% offline

**Icônes SVG (jeu complet dans base.html) :**
- `icon-chart-bar`, `icon-users`, `icon-report` — Navigation principale
- `icon-settings` — Menu Administration (Sauvegarde, Audit, Paramètres)
- `icon-device-floppy`, `icon-clock-exclamation`, `icon-key` — Sous-menu Administration
- `icon-alert-triangle`, `icon-clock-exclamation` — Alertes contrôles
- `icon-flask`, `icon-circle-check` — Contrôles
- `icon-edit`, `icon-trash`, `icon-logout` — Actions
- `icon-key`, `icon-user`, `icon-eye` — Rôles/auth
- `icon-search`, `icon-filter` — Recherche/filtres
- `icon-download`, `icon-upload`, `icon-folder`, `icon-refresh` — Sauvegarde
- `icon-phone`, `icon-tag`, `icon-scale`, `icon-clipboard` — Fiche patient
- `icon-heart-pulse`, `icon-heart` — Programmes TB/VIH
- `icon-help-circle` — Aide/tutoriel
- `icon-menu`, `icon-x`, `icon-arrow-left`, `icon-printer` — UI

**Filtres /patients (panneau dépliable) :**
- Barre de recherche + bouton "Filtres" (badge numérique si filtres actifs)
- Panneau dépliable avec grille de filtres (statut, programme, âge, sexe, quartier, décision TB, retards)
- Chips sous la recherche listant les filtres actifs (retirables individuellement)
- Click outside pour fermer le panneau

**Classes CSS réutilisées (depuis les fichiers de référence) :**
- `.stat`, `.stat-grid` — Cartes de statistiques
- `.badge.gueri`, `.badge.decede`, `.badge.perdu`, `.badge.encours`
- `.badge.tb`, `.badge.vih`, `.badge.incarcere`, `.badge.libere`
- `.panel`, `.panels` — Panneaux
- `.rappel-section`, `.rappel-row` — Alertes/Rappels
- `.toolbar`, `.filter-group`, `.search-box`, `.filter-panel`, `.filter-chips`, `.filter-chip` — Filtres
- `.table-wrap`, `table`, `.sortable`, `.sort-arrow` — Tableaux avec tri
- `.overlay`, `.modal`, `.modal-head`, `.modal-footer` — Modals
- `.form-grid`, `.field`, `.section-title` — Formulaires
- `.alert-card.danger`, `.alert-card.warning` — Alertes dashboard
- `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-danger` — Boutons
- `.icon`, `.nav-item .dot .icon` — Icônes SVG inline

---

## 🔧 Fichiers de référence (anciens)

| Fichier | Description | Taille |
|---------|-------------|--------|
| `07-2026_pvvih.html` | App VIH autonome (single-file, IndexedDB) | ~900 lignes |
| `07-2026_SUIVI_TB.html` | App TB autonome (single-file, IndexedDB) | ~1200 lignes |

**Ne pas supprimer** — servent de référence pour le design et la logique métier.

---

## 💡 Notes techniques

- **Base :** SQLite via `sqlite3` Python (pas d'ORM)
- **Backend :** Flask vanilla (pas de Blueprints pour l'instant)
- **Frontend :** Jinja2 templates + vanilla JS (pas de framework)
- **Auth :** Sessions Flask + mot de passe hashé (werkzeug.security)
- **Rôles :** admin (complet), user (complet), readonly (lecture seule)
- **Auteur :** Utilisateur connecté (via session)
- **Context processor** `inject_last_backup()` : injecte `derniere_sauvegarde` (date du fichier `suivi_patients_*.json/.csv` le plus récent du dossier projet, format JJ/MM/AAAA HH:MM ; `None` sinon) — affiché en bas de chaque page
- **Constante** `MOIS_FR` (noms des mois en français, pour le lien rapport du dashboard)

---

*Dernière mise à jour : 06/09/2026 — Mode sombre ajouté : toggle dans menu profil (lune/soleil), palette complète dark (#000000 fond, #1C1C1E surface, badges dark-aware), persisté en localStorage, basculable sans rechargement. Couleurs codées en dur dans parametres.html corrigées (→ variables CSS). Launcher ajouté. Réorganisation topbar finale. 58 patients (44 TB + 14 VIH). 100% offline.*
