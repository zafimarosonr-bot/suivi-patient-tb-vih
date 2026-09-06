-- ============================================================
-- Données de démonstration
-- ============================================================

-- Patients
INSERT INTO patients (id, nom, prenoms, date_naissance, age, sexe, statut, quartier, situation_penale, telephone, adresse, contact_nom, contact_tel) VALUES
('PAT-2026-001', 'Rakoto', 'Jean', '1990-04-12', NULL, 'M', 'incarcere', 'CAI', 'Condamné', '034 12 345 67', 'Lot 12B, Analakely', 'Rasoa Hélène', '033 11 222 33'),
('PAT-2026-002', 'Rasoa', 'Marie', NULL, 29, 'F', 'incarcere', 'FM', 'Prévenu', '033 98 765 43', 'Rue 5, Fiadanana', 'Andry Paul', '034 55 666 77'),
('PAT-2026-003', 'Andry', 'Paul', '1978-09-30', NULL, 'M', 'incarcere', 'SP', 'Condamné', '', 'Av. de l''Indépendance', 'Rakoto Jean', '034 12 345 67'),
('PAT-2026-004', 'Voahangy', 'Lala', '1995-03-20', NULL, 'F', 'incarcere', 'CAII', 'Prévenu', '034 77 888 99', 'Quartier Ambohidratrimo', 'Rasoa Marie', '033 98 765 43'),
('PAT-2026-005', 'Rabe', 'Hery', NULL, 44, 'M', 'libere', 'CND', 'Condamné', '032 11 223 34', '', '', ''),
('PAT-2026-006', 'Rafanomezantsoa', 'Aina', '1988-11-05', NULL, 'F', 'incarcere', 'EXFM', 'Condamné', '034 44 556 67', 'Fianarantsoa', 'Rabe Hery', '032 11 223 34'),
('PAT-2026-007', 'Ratsimbazafy', 'Hajo', '1975-06-18', NULL, 'M', 'incarcere', 'FM', 'Condamné', '', '', 'Rakoto Jean', '034 12 345 67'),
('PAT-2026-008', 'Ramanantsoa', 'Fara', '1992-01-30', NULL, 'F', 'transfere', 'CAI', 'Prévenu', '033 22 334 45', '', '', '');

-- Historique statut
INSERT INTO historique_statut (patient_id, ancien_statut, nouveau_statut, date, motif) VALUES
('PAT-2026-005', 'incarcere', 'libere', '2026-04-15', 'Fin de peine'),
('PAT-2026-008', 'incarcere', 'transfere', '2026-06-20', 'Transfert vers Antananarivo');

-- Suivi TB
INSERT INTO suivi_tb (patient_id, numero_registre, lab_id, date_debut_traitement, forme_clinique, type_cas, poids_m0, poids_m2, poids_m5, poids_m6, ctrl_m2_date, ctrl_m2_fait, ctrl_m2_resultat, ctrl_m5_date, ctrl_m5_fait, ctrl_m5_resultat, ctrl_m6_date, ctrl_m6_fait, ctrl_m6_resultat, decision, date_decision) VALUES
('PAT-2026-001', 'TB-2026-001', '552/26', '2026-01-22', 'TPB+', 'Nouveau', 58, 61, 64, NULL, '2026-03-22', 0, '', '2026-06-22', 0, '', '2026-07-22', 0, '', '', NULL),
('PAT-2026-002', 'TB-2025-001', '553/26', '2025-11-18', 'TEP', 'Nouveau', 49, 50, 52, 53, '2025-12-18', 1, 'Négatif', '2026-04-18', 1, 'Négatif', '2026-05-18', 1, 'Négatif', 'Guéri', '2026-05-20'),
('PAT-2026-003', 'TB-2025-002', '497/25', '2025-09-15', 'TPB-', 'Rechute', 60, 59, NULL, NULL, '2025-10-15', 1, 'Positif', '2026-01-15', 0, '', '2026-02-15', 0, '', 'Perdu de vue', '2026-02-01'),
('PAT-2026-004', 'TB-2026-002', '601/26', '2026-05-10', 'TPB+', 'Nouveau', 52, NULL, NULL, NULL, '2026-06-10', 0, '', '2026-10-10', 0, '', '2026-11-10', 0, '', '', NULL),
('PAT-2026-007', 'TB-2026-003', '610/26', '2026-03-01', 'TPB+', 'Nouveau', 65, 67, NULL, NULL, '2026-05-01', 1, 'Négatif', '2026-08-01', 0, '', '2026-09-01', 0, '', '', NULL);

-- Suivi VIH
-- Codes auto-générés : DDMMYY + 3 lettres NOM + 2 lettres PRÉNOMS
-- PAT-2026-001: Rakoto Jean, né 1990-04-12 → 120490RAKJE
-- PAT-2026-005: Rabe Hery, âge 44 (née ~1982) → 010182RABHE
-- PAT-2026-006: Rafanomezantsoa Aina, né 1988-11-05 → 051188RAFAN
INSERT INTO suivi_vih (patient_id, numero_registre, code, date_debut_suivi, observation) VALUES
('PAT-2026-001', 'VIH-2024-001', '120490RAKJE', '2024-03-15', 'Nouveau'),
('PAT-2026-005', 'VIH-2021-001', '010182RABHE', '2021-08-01', 'Libéré'),
('PAT-2026-006', 'VIH-2023-001', '051188RAFAN', '2023-06-10', 'Nouveau');

