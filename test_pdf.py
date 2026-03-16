"""Test de génération du PDF Signe+ - à lancer avec le venv du projet."""
import os, sys

# S'assurer qu'on est dans le bon dossier
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

# Charger les fonctions PDF depuis app.py
code = open('app.py').read()

# Extraire les constantes et fonctions PDF
idx_logo = code.index('# --- Chemin logo ---')
idx_ui = code.index('# --- UI Streamlit ---')
pdf_code = code[idx_logo:idx_ui]

# Mock streamlit
class _SS:
    cfg_frais_gestion = 5.0
    cfg_taux_reserve = 10.0
class _St:
    session_state = _SS()
st = _St()

# Exécuter le code PDF
g = dict(globals())
g['st'] = st
exec(pdf_code, g)

create_pdf = g['create_pdf']

# ============================================================
# CAS DE TEST
# ============================================================

def test_reserve_reintegree():
    """Test PDF avec réserve réintégrée dans le brut."""
    data = {
        'tjm': 500, 'days_worked_month': 20,
        'turnover': 10000, 'management_fees': 500,
        'frais_intermediation': 0, 'frais_partages': 0, 'commission_apporteur': 0,
        'montant_disponible': 9500, 'base_salary': 2374, 'prime_apport': 118.70,
        'reserve_brute': 237.40, 'reserve_reintegree': True,
        'complement_remuneration': 2824.94, 'complement_apport_affaires': 141.25,
        'indemnite_cp': 569.63, 'gross_salary': 6265.92,
        'employee_charges': 1350, 'employer_charges': 2759,
        'cotis_total_pat': 2600, 'cotis_total_sal': 1300,
        'forfait_social': 9.5, 'reduction_rgdu': 50,
        'mutuelle_part_pat': 30.04, 'mutuelle_part_sal': 30.04,
        'tr_part_pat': 107.70, 'tr_part_sal': 107.70,
        'nb_titres_restaurant': 15, 'net_before_tax': 4916,
        'net_payable': 3898.59, 'provision_reserve_financiere': 0,
        'ik_amount': 63.60, 'igd_amount': 158.80,
        'forfait_teletravail': 5.40, 'jours_teletravail': 2,
        'other_expenses': 50, 'total_frais_rembourses': 277.80,
        'label_reserve': 'Réserve financière', 'effectif_sup_50': False,
        'cout_global': 9025, 'budget_salaire': 8747.20,
    }
    pdf = create_pdf(data, "Jean DUPONT", "Gwenaëlle CHARPENTIER")
    out = "test_pdf_reintegree.pdf"
    with open(out, 'wb') as f:
        f.write(pdf)
    print(f"[OK] {out} ({len(pdf)} bytes) - Réserve réintégrée, avec frais")
    return out


def test_reserve_provisionnee():
    """Test PDF avec réserve provisionnée (hors brut)."""
    data = {
        'tjm': 710, 'days_worked_month': 19,
        'turnover': 13490, 'management_fees': 1079.20,
        'frais_intermediation': 0, 'frais_partages': 0, 'commission_apporteur': 0,
        'montant_disponible': 12410.80, 'base_salary': 2374, 'prime_apport': 118.70,
        'reserve_brute': 237.40, 'reserve_reintegree': False,
        'complement_remuneration': 3800.22, 'complement_apport_affaires': 190.01,
        'indemnite_cp': 648.29, 'gross_salary': 7131.22,
        'employee_charges': 1524.83, 'employer_charges': 3129.72,
        'cotis_total_pat': 3000, 'cotis_total_sal': 1450,
        'forfait_social': 12, 'reduction_rgdu': 0,
        'mutuelle_part_pat': 30.04, 'mutuelle_part_sal': 30.04,
        'tr_part_pat': 0, 'tr_part_sal': 0,
        'nb_titres_restaurant': 0, 'net_before_tax': 5606.39,
        'net_payable': 6034.19, 'provision_reserve_financiere': 374.10,
        'ik_amount': 127.20, 'igd_amount': 0,
        'forfait_teletravail': 0, 'jours_teletravail': 0,
        'other_expenses': 300.60, 'total_frais_rembourses': 427.80,
        'label_reserve': 'Réserve financière', 'effectif_sup_50': False,
        'cout_global': 10688.74, 'budget_salaire': 11983,
    }
    pdf = create_pdf(data, "Marie MARTIN", "Gwenaëlle CHARPENTIER")
    out = "test_pdf_provisionnee.pdf"
    with open(out, 'wb') as f:
        f.write(pdf)
    print(f"[OK] {out} ({len(pdf)} bytes) - Réserve provisionnée, TJM 710")
    return out


def test_cdd_sans_frais():
    """Test PDF CDD sans frais remboursés."""
    data = {
        'tjm': 400, 'days_worked_month': 15,
        'turnover': 6000, 'management_fees': 300,
        'frais_intermediation': 120, 'frais_partages': 60, 'commission_apporteur': 0,
        'montant_disponible': 5520, 'base_salary': 2374, 'prime_apport': 118.70,
        'reserve_brute': 237.40, 'reserve_reintegree': True,
        'complement_remuneration': 800.50, 'complement_apport_affaires': 40.03,
        'indemnite_cp': 357.06, 'gross_salary': 3927.69,
        'employee_charges': 840, 'employer_charges': 1630,
        'cotis_total_pat': 1500, 'cotis_total_sal': 800,
        'forfait_social': 6, 'reduction_rgdu': 120,
        'mutuelle_part_pat': 30.04, 'mutuelle_part_sal': 30.04,
        'tr_part_pat': 0, 'tr_part_sal': 0,
        'nb_titres_restaurant': 0, 'net_before_tax': 3087.69,
        'net_payable': 3087.69, 'provision_reserve_financiere': 0,
        'ik_amount': 0, 'igd_amount': 0,
        'forfait_teletravail': 0, 'jours_teletravail': 0,
        'other_expenses': 0, 'total_frais_rembourses': 0,
        'label_reserve': 'Indemnité de précarité', 'effectif_sup_50': False,
        'cout_global': 5557.69, 'budget_salaire': 5520,
    }
    pdf = create_pdf(data, "Paul DURAND (CDD)", "Membre BU 2")
    out = "test_pdf_cdd.pdf"
    with open(out, 'wb') as f:
        f.write(pdf)
    print(f"[OK] {out} ({len(pdf)} bytes) - CDD, pas de frais, indemnité précarité")
    return out


if __name__ == "__main__":
    print("=" * 50)
    print("Tests génération PDF Signe+")
    print("=" * 50)
    files = []
    files.append(test_reserve_reintegree())
    files.append(test_reserve_provisionnee())
    files.append(test_cdd_sans_frais())
    print("=" * 50)
    print(f"Tous les tests OK - {len(files)} PDFs générés")
    for f in files:
        print(f"  → {f}")
