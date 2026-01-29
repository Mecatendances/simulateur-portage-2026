import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
import base64

# --- Baremes URSSAF 2026 ---
BAREME_IK_VOITURE_2026 = {
    3: {"jusqua_5000": 0.529, "de_5001_a_20000": 0.316, "au_dela_20000": 0.370},
    4: {"jusqua_5000": 0.606, "de_5001_a_20000": 0.340, "au_dela_20000": 0.407},
    5: {"jusqua_5000": 0.636, "de_5001_a_20000": 0.357, "au_dela_20000": 0.427},
    6: {"jusqua_5000": 0.665, "de_5001_a_20000": 0.374, "au_dela_20000": 0.447},
    7: {"jusqua_5000": 0.697, "de_5001_a_20000": 0.394, "au_dela_20000": 0.470},
}

BAREME_IK_MOTO_2026 = {
    1: {"jusqua_3000": 0.395, "de_3001_a_6000": 0.099, "au_dela_6000": 0.248},
    2: {"jusqua_3000": 0.468, "de_3001_a_6000": 0.082, "au_dela_6000": 0.275},
    3: {"jusqua_3000": 0.606, "de_3001_a_6000": 0.071, "au_dela_6000": 0.308},
    4: {"jusqua_3000": 0.695, "de_3001_a_6000": 0.044, "au_dela_6000": 0.352},
    5: {"jusqua_3000": 0.792, "de_3001_a_6000": 0.078, "au_dela_6000": 0.455},
}

# Baremes IGD URSSAF 2026
IGD_REPAS = 21.60
IGD_NUITEE_PROVINCE = 57.80
IGD_NUITEE_PARIS = 76.70

# Valeur faciale TR standard
TR_VALEUR_FACIALE = 14.36
TR_PART_PATRONALE_MAX = 7.18

# --- Constantes Forfait Teletravail ---
TELETRAVAIL_TAUX_JOUR = 2.70  # EUR par jour
TELETRAVAIL_MAX_JOURS = 22    # Maximum 22 jours

# --- Parametres RGDU 2026 ---
RGDU_TMIN = 0.02  # Seuil minimal d'exoneration
RGDU_TDELTA_FNAL_50 = 0.3821  # FNAL 0.50% (>=50 salaries)
RGDU_TDELTA_FNAL_10 = 0.3781  # FNAL 0.10% (<50 salaries)
RGDU_EXPOSANT = 1.75
RGDU_SEUIL_SMIC = 3.0  # Jusqu'a 3 SMIC

# --- Taux FNAL selon effectif ---
FNAL_TAUX_SUP_50 = 0.0050  # 0.50% pour >= 50 salaries
FNAL_TAUX_INF_50 = 0.0010  # 0.10% pour < 50 salaries

# --- COTISATIONS 2026 (ligne par ligne comme Silae) ---
COTISATIONS_2026 = {
    # PATRONALES SUR TOTALITE
    "maladie":       {"pat": 0.0700, "sal": 0.0,    "base": "TOTALITE"},
    "maladie_compl": {"pat": 0.0600, "sal": 0.0,    "base": "TOTALITE"},
    "csa":           {"pat": 0.0030, "sal": 0.0,    "base": "TOTALITE"},
    "vieillesse_dep":{"pat": 0.0211, "sal": 0.0040, "base": "TOTALITE"},
    "af":            {"pat": 0.0345, "sal": 0.0,    "base": "TOTALITE"},
    "af_compl":      {"pat": 0.0180, "sal": 0.0,    "base": "TOTALITE"},
    "atmp":          {"pat": 0.0064, "sal": 0.0,    "base": "TOTALITE"},
    "chomage":       {"pat": 0.0400, "sal": 0.0,    "base": "TOTALITE"},
    "ags":           {"pat": 0.0025, "sal": 0.0,    "base": "TOTALITE"},
    "formation":     {"pat": 0.0100, "sal": 0.0,    "base": "TOTALITE"},
    "taxe_appr":     {"pat": 0.0059, "sal": 0.0,    "base": "TOTALITE"},
    "taxe_appr_lib": {"pat": 0.0009, "sal": 0.0,    "base": "TOTALITE"},
    "dialogue_soc":  {"pat": 0.0001, "sal": 0.0,    "base": "TOTALITE"},

    # SUR TRANCHE A (PMSS)
    "vieillesse_pl": {"pat": 0.0855, "sal": 0.0690, "base": "TRANCHE_A"},
    "fnal":          {"pat": 0.0010, "sal": 0.0,    "base": "TRANCHE_A"},
    "retraite_t1":   {"pat": 0.0472, "sal": 0.0315, "base": "TRANCHE_A"},
    "ceg_t1":        {"pat": 0.0129, "sal": 0.0086, "base": "TRANCHE_A"},
    "cet_t1":        {"pat": 0.0021, "sal": 0.0014, "base": "TRANCHE_A"},
    "apec_t1":       {"pat": 0.00036,"sal": 0.00024,"base": "TRANCHE_A"},
    "prevoyance_deces":{"pat": 0.0159, "sal": 0.0, "base": "TRANCHE_A"},

    # SUR TRANCHE B (Brut - PMSS, si brut > PMSS)
    "retraite_t2":   {"pat": 0.1295, "sal": 0.0864, "base": "TRANCHE_B"},
    "ceg_t2":        {"pat": 0.0162, "sal": 0.0108, "base": "TRANCHE_B"},
    "cet_t2":        {"pat": 0.0021, "sal": 0.0014, "base": "TRANCHE_B"},
    "apec_t2":       {"pat": 0.00036,"sal": 0.00024,"base": "TRANCHE_B"},
    "prevoyance_supp":{"pat": 0.0073, "sal": 0.0073,"base": "TRANCHE_B"},

    # CSG / CRDS (base = 98.25% du brut + contributions pat prevoyance)
    "csg_deductible":{"pat": 0.0, "sal": 0.0680, "base": "CSG"},
    "csg_crds":      {"pat": 0.0, "sal": 0.0290, "base": "CSG"},
}

COTISATIONS_LABELS = {
    "maladie": "Maladie",
    "maladie_compl": "Maladie complementaire",
    "csa": "Contrib. Solidarite Autonomie",
    "vieillesse_dep": "Vieillesse deplafonnee",
    "af": "Allocations Familiales",
    "af_compl": "Alloc. Familiales compl.",
    "atmp": "AT/MP",
    "chomage": "Chomage",
    "ags": "AGS",
    "formation": "Formation professionnelle",
    "taxe_appr": "Taxe d'apprentissage",
    "taxe_appr_lib": "Taxe appr. (liberatoire)",
    "dialogue_soc": "Dialogue social",
    "vieillesse_pl": "Vieillesse plafonnee",
    "fnal": "FNAL",
    "retraite_t1": "Retraite AGIRC-ARRCO T1",
    "ceg_t1": "CEG T1",
    "cet_t1": "CET T1",
    "apec_t1": "APEC T1",
    "prevoyance_deces": "Prevoyance deces cadre",
    "retraite_t2": "Retraite AGIRC-ARRCO T2",
    "ceg_t2": "CEG T2",
    "cet_t2": "CET T2",
    "apec_t2": "APEC T2",
    "prevoyance_supp": "Prevoyance supp. cadre T2",
    "csg_deductible": "CSG deductible",
    "csg_crds": "CSG/CRDS non deductible",
}

# --- Initialisation des Variables (Session State) ---
if 'cfg_base_salary' not in st.session_state:
    st.session_state.cfg_base_salary = 2374.0
if 'cfg_frais_gestion' not in st.session_state:
    st.session_state.cfg_frais_gestion = 5.0
if 'cfg_frais_intermediation' not in st.session_state:
    st.session_state.cfg_frais_intermediation = 0.0
if 'cfg_taux_prime' not in st.session_state:
    st.session_state.cfg_taux_prime = 5.0
if 'cfg_taux_reserve' not in st.session_state:
    st.session_state.cfg_taux_reserve = 10.0
if 'cfg_taux_cp' not in st.session_state:
    st.session_state.cfg_taux_cp = 10.0
if 'cfg_ik_rate' not in st.session_state:
    st.session_state.cfg_ik_rate = 0.636
if 'cfg_pmss' not in st.session_state:
    st.session_state.cfg_pmss = 4005.0
if 'cfg_mutuelle_taux' not in st.session_state:
    st.session_state.cfg_mutuelle_taux = 1.5
if 'cfg_mutuelle_part_pat' not in st.session_state:
    st.session_state.cfg_mutuelle_part_pat = 50.0
if 'cfg_smic_mensuel' not in st.session_state:
    st.session_state.cfg_smic_mensuel = 1823.03
if 'cfg_taux_atmp' not in st.session_state:
    st.session_state.cfg_taux_atmp = 0.64
if 'cfg_taux_charges_override' not in st.session_state:
    st.session_state.cfg_taux_charges_override = 0.0  # 0 = auto-calcul


# --- Fonction RGDU ---
def calculer_rgdu(brut_mensuel, smic_mensuel, use_fnal_50=True):
    """
    Calcule la Reduction Generale Degressive Unique (RGDU) 2026
    Retourne le montant de la reduction des charges patronales
    """
    smic_annuel = smic_mensuel * 12
    brut_annuel = brut_mensuel * 12

    # Pas de reduction au-dela de 3 SMIC
    if brut_annuel >= RGDU_SEUIL_SMIC * smic_annuel:
        return 0.0

    # Choix du Tdelta selon FNAL
    tdelta = RGDU_TDELTA_FNAL_50 if use_fnal_50 else RGDU_TDELTA_FNAL_10

    # Formule RGDU 2026
    ratio = (RGDU_SEUIL_SMIC * smic_annuel / brut_annuel) - 1
    if ratio <= 0:
        return 0.0

    base = 0.5 * ratio
    coefficient = RGDU_TMIN + (tdelta * (base ** RGDU_EXPOSANT))

    # Plafonner le coefficient a Tmin + Tdelta
    coefficient = min(coefficient, RGDU_TMIN + tdelta)

    # Arrondir a 4 decimales
    coefficient = round(coefficient, 4)

    # Reduction mensuelle
    reduction = brut_mensuel * coefficient

    return reduction


# --- Calcul cotisations ligne par ligne ---
def calculer_cotisations(brut, pmss, atmp_rate, fnal_rate, prev_pat_contributions):
    """
    Calcule chaque cotisation individuellement (comme Silae).
    Retourne un dict avec le detail ligne par ligne + totaux.
    """
    tranche_a = min(brut, pmss)
    tranche_b = max(0, brut - pmss)

    # Base CSG = 98.25% du brut + contributions pat prevoyance/mutuelle
    base_csg = brut * 0.9825 + prev_pat_contributions

    details = []
    total_pat = 0
    total_sal = 0

    for nom, cotis in COTISATIONS_2026.items():
        # Determiner la base
        if cotis["base"] == "TOTALITE":
            base = brut
        elif cotis["base"] == "TRANCHE_A":
            base = tranche_a
        elif cotis["base"] == "TRANCHE_B":
            base = tranche_b
            if tranche_b == 0:
                continue  # pas de T2 si brut <= PMSS
        elif cotis["base"] == "CSG":
            base = base_csg
        else:
            continue

        # Appliquer taux AT/MP et FNAL configurables
        taux_pat = cotis["pat"]
        taux_sal = cotis["sal"]
        if nom == "atmp":
            taux_pat = atmp_rate
        if nom == "fnal":
            taux_pat = fnal_rate

        montant_pat = round(base * taux_pat, 2)
        montant_sal = round(base * taux_sal, 2)

        total_pat += montant_pat
        total_sal += montant_sal

        details.append({
            "nom": nom, "base": round(base, 2),
            "taux_pat": taux_pat, "montant_pat": montant_pat,
            "taux_sal": taux_sal, "montant_sal": montant_sal
        })

    return {
        "details": details,
        "total_pat": total_pat,
        "total_sal": total_sal,
        "tranche_a": tranche_a,
        "tranche_b": tranche_b,
        "base_csg": round(base_csg, 2),
    }


# --- Moteur de Calcul ---
def calculate_salary(tjm, days_worked_month, days_worked_week,
                     ik_amount, igd_amount, other_expenses, use_reserve, use_mutuelle,
                     nb_titres_restaurant=0, frais_intermediation_pct=0.0,
                     jours_teletravail=0, use_rgdu=False, effectif_sup_50=False):

    cfg_base = st.session_state.cfg_base_salary
    rate_gestion = st.session_state.cfg_frais_gestion / 100.0
    rate_prime = st.session_state.cfg_taux_prime / 100.0
    rate_cp = st.session_state.cfg_taux_cp / 100.0

    pmss = st.session_state.cfg_pmss
    smic = st.session_state.cfg_smic_mensuel
    atmp_rate = st.session_state.cfg_taux_atmp / 100.0
    fnal_rate = FNAL_TAUX_SUP_50 if effectif_sup_50 else FNAL_TAUX_INF_50

    # Mutuelle
    mutuelle_total_cost = 0.0
    mutuelle_part_pat = 0.0
    mutuelle_part_sal = 0.0

    if use_mutuelle:
        mutuelle_rate = st.session_state.cfg_mutuelle_taux / 100.0
        split_pat = st.session_state.cfg_mutuelle_part_pat / 100.0
        mutuelle_total_cost = pmss * mutuelle_rate
        mutuelle_part_pat = round(mutuelle_total_cost * split_pat, 2)
        mutuelle_part_sal = round(mutuelle_total_cost * (1 - split_pat), 2)

    # Titres Restaurant
    tr_part_sal = nb_titres_restaurant * TR_PART_PATRONALE_MAX
    tr_part_pat = nb_titres_restaurant * TR_PART_PATRONALE_MAX

    # Forfait teletravail
    jours_teletravail_effectifs = min(jours_teletravail, TELETRAVAIL_MAX_JOURS)
    forfait_teletravail = jours_teletravail_effectifs * TELETRAVAIL_TAUX_JOUR

    turnover = tjm * days_worked_month
    management_fees = turnover * rate_gestion
    frais_intermediation = turnover * (frais_intermediation_pct / 100.0)

    # Montant disponible (apres frais de gestion et intermediation)
    montant_disponible = turnover - management_fees - frais_intermediation

    # Total des frais rembourses
    total_frais_rembourses = ik_amount + igd_amount + forfait_teletravail + other_expenses

    base_salary = cfg_base * (days_worked_week / 5.0)
    prime_apport = base_salary * rate_prime

    # Reserve financiere
    rate_reserve = st.session_state.cfg_taux_reserve / 100.0
    reserve_brute = cfg_base * (days_worked_week / 5.0) * rate_reserve

    # --- Taux de charges -> complement + brut (methode Silae) ---
    # COMPLEMENT = ((MONTANT_DISPO / (1 + TAUX)) - BASE - PRIME - RESERVE) / (1 + taux_prime)
    budget_salaire = montant_disponible - total_frais_rembourses
    taux_charges_override = st.session_state.cfg_taux_charges_override / 100.0

    if taux_charges_override > 0:
        taux_charges = taux_charges_override
    else:
        # Auto-calcul du taux (incluant charges marginales sur reserve)
        taux_charges = 0.55
        for _ in range(50):
            pool = budget_salaire / (1 + taux_charges)
            ct_est = max(0, pool - base_salary - prime_apport - reserve_brute)
            brut_est = (base_salary + prime_apport + ct_est) * (1 + rate_cp)
            ta = min(brut_est, pmss)
            tb = max(0, brut_est - pmss)
            pd_ = round(ta * 0.0159, 2)
            ps_ = round(tb * 0.0073, 2) if tb > 0 else 0.0
            pt_ = pd_ + mutuelle_part_pat + ps_
            c_ = calculer_cotisations(brut_est, pmss, atmp_rate, fnal_rate, pt_)
            fs_ = round(pt_ * 0.08, 2)
            icp_ = brut_est - (base_salary + prime_apport + ct_est)
            ch_brut = c_["total_pat"] + mutuelle_part_pat + tr_part_pat + fs_ + icp_
            # Charges marginales sur reserve: cotisations reelles sur brut+reserve vs brut seul
            reserve_brut = reserve_brute * (1 + rate_cp)
            brut_avec_reserve = brut_est + reserve_brut
            ta2 = min(brut_avec_reserve, pmss)
            tb2 = max(0, brut_avec_reserve - pmss)
            pd2 = round(ta2 * 0.0159, 2)
            ps2 = round(tb2 * 0.0073, 2) if tb2 > 0 else 0.0
            pt2 = pd2 + mutuelle_part_pat + ps2
            c2_ = calculer_cotisations(brut_avec_reserve, pmss, atmp_rate, fnal_rate, pt2)
            fs2 = round(pt2 * 0.08, 2)
            ch_reserve = (c2_["total_pat"] + fs2) - (c_["total_pat"] + fs_) + reserve_brute * rate_cp + mutuelle_part_pat * (reserve_brute / pool)
            tn = (ch_brut + ch_reserve) / pool if pool > 0 else 0
            if abs(tn - taux_charges) < 0.00001:
                taux_charges = tn
                break
            taux_charges = tn

    # Complement depuis le taux
    pool = budget_salaire / (1 + taux_charges)
    complement_total = max(0, pool - base_salary - prime_apport - reserve_brute)
    complement_remuneration = complement_total / (1 + rate_prime)
    complement_apport_affaires = complement_total - complement_remuneration

    # Brut = base + prime + complement + ICP (sans provision)
    indemnite_cp = (base_salary + prime_apport + complement_total) * rate_cp
    gross_salary = base_salary + prime_apport + complement_total + indemnite_cp

    # Cotisations reelles sur le brut
    tranche_a = min(gross_salary, pmss)
    tranche_b = max(0, gross_salary - pmss)

    prev_deces_pat = round(tranche_a * 0.0159, 2)
    prev_supp_pat = round(tranche_b * 0.0073, 2) if tranche_b > 0 else 0.0
    prev_pat_total = prev_deces_pat + mutuelle_part_pat + prev_supp_pat

    cotis = calculer_cotisations(gross_salary, pmss, atmp_rate, fnal_rate, prev_pat_total)
    forfait_social = round(prev_pat_total * 0.08, 2)

    # RGDU
    reduction_rgdu = 0.0
    if use_rgdu:
        reduction_rgdu = calculer_rgdu(gross_salary, smic, use_fnal_50=effectif_sup_50)

    # Charges patronales totales
    employer_charges_avant_rgdu = cotis["total_pat"] + mutuelle_part_pat + tr_part_pat + forfait_social
    employer_charges = employer_charges_avant_rgdu - reduction_rgdu

    # Charges salariales totales
    employee_charges = cotis["total_sal"] + mutuelle_part_sal + tr_part_sal

    # Provision reserve financiere = MONTANT DISPO - (brut + charges pat)
    # Inclut la reserve brute + les charges futures sur la reserve
    provision_reserve_financiere = max(0, budget_salaire - gross_salary - employer_charges)

    # Cout global
    cout_global_sans_reserve = gross_salary + employer_charges + total_frais_rembourses

    reserve_amount = reserve_brute if use_reserve else 0

    # Net
    net_before_tax = gross_salary - employee_charges
    net_payable = net_before_tax + total_frais_rembourses

    return {
        "turnover": turnover,
        "management_fees": management_fees,
        "frais_intermediation": frais_intermediation,
        "montant_disponible": montant_disponible,
        "ik_amount": ik_amount,
        "igd_amount": igd_amount,
        "forfait_teletravail": forfait_teletravail,
        "jours_teletravail": jours_teletravail_effectifs,
        "other_expenses": other_expenses,
        "total_frais_rembourses": total_frais_rembourses,
        "base_salary": base_salary,
        "prime_apport": prime_apport,
        "complement_remuneration": complement_remuneration,
        "complement_apport_affaires": complement_apport_affaires,
        "indemnite_cp": indemnite_cp,
        "gross_salary": gross_salary,
        "reserve_amount": reserve_amount,
        "employer_charges": employer_charges,
        "employer_charges_avant_rgdu": employer_charges_avant_rgdu,
        "cotis_total_pat": cotis["total_pat"],
        "cotis_total_sal": cotis["total_sal"],
        "cotis_details": cotis["details"],
        "forfait_social": forfait_social,
        "prev_pat_total": prev_pat_total,
        "tranche_a": cotis["tranche_a"],
        "tranche_b": cotis["tranche_b"],
        "base_csg": cotis["base_csg"],
        "reduction_rgdu": reduction_rgdu,
        "employee_charges": employee_charges,
        "mutuelle_part_pat": mutuelle_part_pat,
        "mutuelle_part_sal": mutuelle_part_sal,
        "tr_part_sal": tr_part_sal,
        "tr_part_pat": tr_part_pat,
        "nb_titres_restaurant": nb_titres_restaurant,
        "cout_global_sans_reserve": cout_global_sans_reserve,
        "net_before_tax": net_before_tax,
        "net_payable": net_payable,
        "effectif_sup_50": effectif_sup_50,
        "taux_charges": taux_charges,
        "pool_silae": pool,
        "provision_reserve_financiere": provision_reserve_financiere,
        "budget_salaire": budget_salaire,
    }

# --- PDF Generation ---
def create_pdf(data, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"Simulation de Salaire - {name}", ln=1, align="C")
    pdf.ln(5)

    # Parametres utilises
    effectif_txt = "< 50 salaries" if not data.get('effectif_sup_50', False) else ">= 50 salaries"
    fnal_txt = "0.10%" if not data.get('effectif_sup_50', False) else "0.50%"
    pdf.set_font("Arial", 'I', size=9)
    pdf.cell(200, 6, txt=f"Parametres: Effectif {effectif_txt} | FNAL {fnal_txt} | AT/MP {st.session_state.cfg_taux_atmp:.2f}%", ln=1, align="C")
    pdf.ln(5)

    t_gest = st.session_state.cfg_frais_gestion
    t_ik = st.session_state.cfg_ik_rate

    # --- Activite & Frais ---
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Activite & Frais", ln=1)
    pdf.set_font("Arial", size=11)
    pdf.cell(140, 8, txt="Chiffre d'affaires (CA)", border=0)
    pdf.cell(50, 8, txt=f"{data['turnover']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.cell(140, 8, txt=f"Frais de gestion ({t_gest}%)", border=0)
    pdf.cell(50, 8, txt=f"- {data['management_fees']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('frais_intermediation', 0) > 0:
        pdf.cell(140, 8, txt="Frais d'intermediation", border=0)
        pdf.cell(50, 8, txt=f"- {data['frais_intermediation']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= MONTANT DISPONIBLE", border='T')
    pdf.cell(50, 8, txt=f"{data['montant_disponible']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(5)

    # --- Decomposition Brut ---
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Decomposition du Salaire Brut", ln=1)
    pdf.set_font("Arial", size=11)

    pdf.cell(140, 8, txt="Salaire de Base", border=0)
    pdf.cell(50, 8, txt=f"{data['base_salary']:,.2f} EUR", border=0, align='R', ln=1)
    pdf.cell(140, 8, txt="Prime d'apport d'affaires", border=0)
    pdf.cell(50, 8, txt=f"{data['prime_apport']:,.2f} EUR", border=0, align='R', ln=1)
    pdf.cell(140, 8, txt="Complement de remuneration", border=0)
    pdf.cell(50, 8, txt=f"{data['complement_remuneration']:,.2f} EUR", border=0, align='R', ln=1)
    pdf.cell(140, 8, txt="Complement Apport d'Affaires", border=0)
    pdf.cell(50, 8, txt=f"{data['complement_apport_affaires']:,.2f} EUR", border=0, align='R', ln=1)
    pdf.cell(140, 8, txt="Indemnite Conges Payes", border=0)
    pdf.cell(50, 8, txt=f"{data['indemnite_cp']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= TOTAL BRUT", border='T')
    pdf.cell(50, 8, txt=f"{data['gross_salary']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(5)

    # --- Charges Patronales (detail cotisations) ---
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Charges Patronales (detail)", ln=1)

    # En-tete du tableau
    pdf.set_font("Arial", 'B', size=8)
    pdf.cell(70, 6, txt="Cotisation", border='B')
    pdf.cell(30, 6, txt="Base", border='B', align='R')
    pdf.cell(20, 6, txt="Taux", border='B', align='R')
    pdf.cell(30, 6, txt="Montant", border='B', align='R', ln=1)

    pdf.set_font("Arial", size=8)
    for d in data['cotis_details']:
        if d['montant_pat'] > 0:
            label = COTISATIONS_LABELS.get(d['nom'], d['nom'])
            pdf.cell(70, 5, txt=label, border=0)
            pdf.cell(30, 5, txt=f"{d['base']:,.2f}", border=0, align='R')
            pdf.cell(20, 5, txt=f"{d['taux_pat']*100:.2f}%", border=0, align='R')
            pdf.cell(30, 5, txt=f"{d['montant_pat']:,.2f}", border=0, align='R', ln=1)

    pdf.set_font("Arial", size=9)
    pdf.cell(120, 6, txt="+ Mutuelle Part Patronale", border=0)
    pdf.cell(30, 6, txt=f"{data['mutuelle_part_pat']:,.2f}", border=0, align='R', ln=1)

    if data.get('tr_part_pat', 0) > 0:
        pdf.cell(120, 6, txt="+ Titres Restaurant Part Patronale", border=0)
        pdf.cell(30, 6, txt=f"{data['tr_part_pat']:,.2f}", border=0, align='R', ln=1)

    pdf.cell(120, 6, txt="+ Forfait Social Prevoyance (8%)", border=0)
    pdf.cell(30, 6, txt=f"{data['forfait_social']:,.2f}", border=0, align='R', ln=1)

    if data.get('reduction_rgdu', 0) > 0:
        pdf.cell(120, 6, txt="- Reduction RGDU 2026", border=0)
        pdf.cell(30, 6, txt=f"-{data['reduction_rgdu']:,.2f}", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(120, 8, txt="= TOTAL CHARGES PATRONALES", border='T')
    pdf.cell(30, 8, txt=f"{data['employer_charges']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(3)

    # --- Provision Reserve Financiere ---
    pdf.set_font("Arial", size=11)
    if data.get('provision_reserve_financiere', 0) > 0:
        pdf.cell(140, 8, txt="Provision Reserve Financiere", border=0)
        pdf.cell(50, 8, txt=f"{data['provision_reserve_financiere']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= COUT GLOBAL SANS RESERVE", border='T')
    pdf.cell(50, 8, txt=f"{data['cout_global_sans_reserve']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(3)

    # --- Charges Salariales (detail) ---
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Charges Salariales (detail)", ln=1)

    pdf.set_font("Arial", 'B', size=8)
    pdf.cell(70, 6, txt="Cotisation", border='B')
    pdf.cell(30, 6, txt="Base", border='B', align='R')
    pdf.cell(20, 6, txt="Taux", border='B', align='R')
    pdf.cell(30, 6, txt="Montant", border='B', align='R', ln=1)

    pdf.set_font("Arial", size=8)
    for d in data['cotis_details']:
        if d['montant_sal'] > 0:
            label = COTISATIONS_LABELS.get(d['nom'], d['nom'])
            pdf.cell(70, 5, txt=label, border=0)
            pdf.cell(30, 5, txt=f"{d['base']:,.2f}", border=0, align='R')
            pdf.cell(20, 5, txt=f"{d['taux_sal']*100:.2f}%", border=0, align='R')
            pdf.cell(30, 5, txt=f"{d['montant_sal']:,.2f}", border=0, align='R', ln=1)

    pdf.set_font("Arial", size=9)
    pdf.cell(120, 6, txt="+ Mutuelle Part Salariale", border=0)
    pdf.cell(30, 6, txt=f"{data['mutuelle_part_sal']:,.2f}", border=0, align='R', ln=1)

    if data.get('tr_part_sal', 0) > 0:
        pdf.cell(120, 6, txt="+ Titres Restaurant Part Salariale", border=0)
        pdf.cell(30, 6, txt=f"{data['tr_part_sal']:,.2f}", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=10)
    pdf.cell(120, 8, txt="= TOTAL CHARGES SALARIALES", border='T')
    pdf.cell(30, 8, txt=f"{data['employee_charges']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(3)

    # --- Net ---
    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= NET AVANT IMPOT", border='T')
    pdf.cell(50, 8, txt=f"{data['net_before_tax']:,.2f} EUR", border='T', align='R', ln=1)
    pdf.ln(5)

    # --- Frais rembourses ---
    pdf.set_font("Arial", size=11)
    if data.get('ik_amount', 0) > 0:
        pdf.cell(140, 8, txt=f"Indemnites Kilometriques ({t_ik} EUR/km)", border=0)
        pdf.cell(50, 8, txt=f"+ {data['ik_amount']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('igd_amount', 0) > 0:
        pdf.cell(140, 8, txt="Indemnites Grand Deplacement", border=0)
        pdf.cell(50, 8, txt=f"+ {data['igd_amount']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('forfait_teletravail', 0) > 0:
        pdf.cell(140, 8, txt=f"Forfait Teletravail ({data['jours_teletravail']}j x 2.70)", border=0)
        pdf.cell(50, 8, txt=f"+ {data['forfait_teletravail']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('other_expenses', 0) > 0:
        pdf.cell(140, 8, txt="Autres Frais", border=0)
        pdf.cell(50, 8, txt=f"+ {data['other_expenses']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.ln(10)

    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(140, 10, txt="= NET A PAYER", border='TB')
    pdf.cell(50, 10, txt=f"{data['net_payable']:,.2f} EUR", border='TB', align='R', ln=1)

    return pdf.output(dest='S').encode('latin-1')

# --- UI Streamlit ---

st.set_page_config(page_title="Simulateur Portage Salarial 2026", layout="wide")

# Sidebar
with st.sidebar:
    st.title("Consultant")
    consultant_name = st.text_input("Nom", "Consultant")
    tjm = st.number_input("TJM (EUR)", min_value=0, value=500, step=10)

    st.markdown("---")
    st.subheader("Temps de Travail")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        days_worked_month = st.number_input("Jours / Mois", value=19.0, step=0.5)
    with col_d2:
        days_worked_week = st.number_input("Jours / Sem", value=5.0, max_value=7.0, step=0.5)

    st.markdown("---")
    st.subheader("Intermediation")
    frais_intermediation_pct = st.number_input("Frais d'intermediation (%)", value=0.0, step=0.5, min_value=0.0)

    st.markdown("---")
    st.subheader("Indemnites Kilometriques (IK)")

    type_vehicule = st.selectbox("Type de vehicule", ["Voiture", "Moto"])

    if type_vehicule == "Voiture":
        cv_options = [3, 4, 5, 6, 7]
        cv_fiscaux = st.selectbox("Chevaux fiscaux (CV)", cv_options, index=2)
        tranche_km = st.selectbox("Tranche kilometrique annuelle",
                                  ["Jusqu'a 5 000 km", "De 5 001 a 20 000 km", "Au-dela de 20 000 km"])

        if tranche_km == "Jusqu'a 5 000 km":
            ik_rate_display = BAREME_IK_VOITURE_2026[cv_fiscaux]["jusqua_5000"]
        elif tranche_km == "De 5 001 a 20 000 km":
            ik_rate_display = BAREME_IK_VOITURE_2026[cv_fiscaux]["de_5001_a_20000"]
        else:
            ik_rate_display = BAREME_IK_VOITURE_2026[cv_fiscaux]["au_dela_20000"]
    else:
        cv_options_moto = [1, 2, 3, 4, 5]
        cv_fiscaux = st.selectbox("Chevaux fiscaux (CV)", cv_options_moto, index=2)
        tranche_km = st.selectbox("Tranche kilometrique annuelle",
                                  ["Jusqu'a 3 000 km", "De 3 001 a 6 000 km", "Au-dela de 6 000 km"])

        if tranche_km == "Jusqu'a 3 000 km":
            ik_rate_display = BAREME_IK_MOTO_2026[cv_fiscaux]["jusqua_3000"]
        elif tranche_km == "De 3 001 a 6 000 km":
            ik_rate_display = BAREME_IK_MOTO_2026[cv_fiscaux]["de_3001_a_6000"]
        else:
            ik_rate_display = BAREME_IK_MOTO_2026[cv_fiscaux]["au_dela_6000"]

    st.session_state.cfg_ik_rate = ik_rate_display
    st.info(f"Taux IK applique : **{ik_rate_display:.3f} EUR/km**")

    km_mensuel = st.number_input("Nb Kilometres ce mois", value=0.0, step=10.0)
    ik_total = km_mensuel * ik_rate_display
    st.caption(f"Total IK : {ik_total:,.2f} EUR")

    st.markdown("---")
    st.subheader("Indemnites Grand Deplacement (IGD)")

    nb_repas_igd = st.number_input("Nb repas IGD", value=0, step=1, min_value=0)
    nb_nuitees_igd = st.number_input("Nb nuitees IGD", value=0, step=1, min_value=0)
    zone_igd = st.selectbox("Zone IGD", ["Province", "Paris/IDF"])

    igd_nuitee_rate = IGD_NUITEE_PARIS if zone_igd == "Paris/IDF" else IGD_NUITEE_PROVINCE
    igd_total = (nb_repas_igd * IGD_REPAS) + (nb_nuitees_igd * igd_nuitee_rate)

    if nb_repas_igd > 0 or nb_nuitees_igd > 0:
        st.caption(f"Repas: {nb_repas_igd} x {IGD_REPAS:.2f} EUR = {nb_repas_igd * IGD_REPAS:.2f} EUR")
        st.caption(f"Nuitees: {nb_nuitees_igd} x {igd_nuitee_rate:.2f} EUR = {nb_nuitees_igd * igd_nuitee_rate:.2f} EUR")
        st.caption(f"**Total IGD : {igd_total:,.2f} EUR**")

    st.markdown("---")
    st.subheader("Titres Restaurant")
    nb_titres_restaurant = st.number_input("Nb Titres Restaurant", value=0, step=1, min_value=0)
    if nb_titres_restaurant > 0:
        st.caption(f"Part salariale : {nb_titres_restaurant} x {TR_PART_PATRONALE_MAX:.2f} = {nb_titres_restaurant * TR_PART_PATRONALE_MAX:.2f} EUR")
        st.caption(f"Part patronale : {nb_titres_restaurant} x {TR_PART_PATRONALE_MAX:.2f} = {nb_titres_restaurant * TR_PART_PATRONALE_MAX:.2f} EUR")

    st.markdown("---")
    st.subheader("Forfait Teletravail")
    jours_teletravail = st.number_input("Nb jours teletravail", value=0, step=1, min_value=0, max_value=22,
                                        help="2.70 EUR/jour, max 22 jours")
    if jours_teletravail > 0:
        st.caption(f"Forfait : {jours_teletravail} x 2.70 = {jours_teletravail * 2.70:.2f} EUR")

    st.markdown("---")
    st.subheader("Autres Frais")
    frais_internet = st.number_input("Internet / Telephone (EUR)", value=0.0, step=10.0)
    frais_transport = st.number_input("Transports (Navigo...) (EUR)", value=0.0, step=10.0)
    frais_divers = st.number_input("Autres Frais (EUR)", value=0.0, step=10.0)

    expenses_other = frais_internet + frais_transport + frais_divers
    st.caption(f"Total Autres Frais : {expenses_other:,.2f} EUR")

    st.markdown("---")
    st.subheader("Options")

    reserve_reintegree = st.checkbox("Reserve Financiere reintegree", value=False,
                                     help="Cochez pour reintegrer la reserve (positif). Decochez pour provisionner (negatif).")
    use_reserve = not reserve_reintegree

    use_mutuelle = st.checkbox("Mutuelle Sante", value=True)

    # RGDU appliquee automatiquement (obligatoire)
    use_rgdu = True

    # Effectif entreprise (impacte FNAL et RGDU)
    effectif_sup_50 = st.checkbox("Entreprise >= 50 salaries", value=False,
                                   help="FNAL 0.50% si >= 50 sal. / 0.10% si < 50 sal.")

# --- CALCUL AVANT AFFICHAGE ---
results = calculate_salary(tjm, days_worked_month, days_worked_week,
                           ik_total, igd_total, expenses_other, use_reserve, use_mutuelle,
                           nb_titres_restaurant, frais_intermediation_pct, jours_teletravail, use_rgdu, effectif_sup_50)

# Main : Onglets
tab_simu, tab_config, tab_comm = st.tabs(["Resultats Simulation", "Configuration Globale", "Email & Explications"])

with tab_simu:
    st.title("Simulateur de Portage Salarial 2026")
    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Chiffre d'Affaires", f"{results['turnover']:,.2f} EUR")
    with kpi2:
        st.metric("Salaire Brut", f"{results['gross_salary']:,.2f} EUR")
    with kpi3:
        total_charges = results['employer_charges'] + results['employee_charges']
        st.metric("Charges Totales", f"{total_charges:,.2f} EUR")
    with kpi4:
        st.metric("NET A PAYER", f"{results['net_payable']:,.2f} EUR", delta="Virement")

    st.divider()

    col_main, col_viz = st.columns([2, 1])

    with col_main:
        st.subheader("Detail du Bulletin")

        txt_gest = f"Frais de gestion ({st.session_state.cfg_frais_gestion}%)"
        effectif_txt = "< 50 sal." if not results.get('effectif_sup_50', False) else ">= 50 sal."

        # Construction dynamique des lignes
        data_lines = [
            ("Chiffre d'affaires (CA)", results['turnover'], "Positif"),
            (txt_gest, -results['management_fees'], "Negatif"),
        ]

        if results['frais_intermediation'] > 0:
            data_lines.append((f"Frais d'intermediation ({frais_intermediation_pct}%)", -results['frais_intermediation'], "Negatif"))

        data_lines.append(("= MONTANT DISPONIBLE", results['montant_disponible'], "Total"))
        data_lines.append(("", 0, "Empty"))

        data_lines.extend([
            ("Salaire de Base", results['base_salary'], "Detail"),
            ("Prime d'apport d'affaires", results['prime_apport'], "Detail"),
            ("Complement de remuneration", results['complement_remuneration'], "Detail"),
            ("Complement Apport d'Affaires", results['complement_apport_affaires'], "Detail"),
            ("Indemnite Conges Payes", results['indemnite_cp'], "Detail"),
            ("= TOTAL BRUT", results['gross_salary'], "Total"),
            ("", 0, "Empty"),
        ])

        # Provision reserve financiere (Silae: MONTANT DISPO - brut - charges pat)
        if use_reserve and results.get('provision_reserve_financiere', 0) > 0:
            data_lines.append(("Provision Reserve Financiere", -results['provision_reserve_financiere'], "Negatif"))

        data_lines.append(("Mutuelle Part Patronale", results['mutuelle_part_pat'], "Detail"))

        if results['tr_part_pat'] > 0:
            data_lines.append(("Titres Restaurant Part Patronale", results['tr_part_pat'], "Detail"))

        # Charges patronales
        data_lines.append((f"Cotisations Patronales [{effectif_txt}]", results['cotis_total_pat'], "Detail"))
        data_lines.append(("Forfait Social Prevoyance (8%)", results['forfait_social'], "Detail"))

        if results.get('reduction_rgdu', 0) > 0:
            data_lines.append(("- Reduction RGDU 2026", -results['reduction_rgdu'], "Positif"))

        data_lines.append(("= Total Charges Patronales", results['employer_charges'], "Total"))
        data_lines.append(("", 0, "Empty"))

        # Frais rembourses (detail)
        data_lines.append(("--- Frais Rembourses ---", 0, "Empty"))
        if results['ik_amount'] > 0:
            data_lines.append((f"Indemnites Km ({st.session_state.cfg_ik_rate:.3f} EUR/km)", results['ik_amount'], "Detail"))
        if results['igd_amount'] > 0:
            data_lines.append(("Indemnites Grand Deplacement (IGD)", results['igd_amount'], "Detail"))
        if results.get('forfait_teletravail', 0) > 0:
            data_lines.append((f"Forfait Teletravail ({results['jours_teletravail']}j x 2.70)", results['forfait_teletravail'], "Detail"))
        if results['other_expenses'] > 0:
            data_lines.append(("Autres Frais", results['other_expenses'], "Detail"))
        data_lines.append(("= Total Frais Rembourses", results['total_frais_rembourses'], "Total"))
        data_lines.append(("", 0, "Empty"))

        data_lines.append(("= COUT GLOBAL SANS RESERVE", results['cout_global_sans_reserve'], "Total"))
        data_lines.append(("", 0, "Empty"))

        # Charges salariales
        data_lines.append(("Cotisations Salariales", -results['cotis_total_sal'], "Negatif"))
        data_lines.append(("Mutuelle Part Salariale", -results['mutuelle_part_sal'], "Negatif"))
        if results['tr_part_sal'] > 0:
            data_lines.append(("Titres Restaurant Part Salariale", -results['tr_part_sal'], "Negatif"))
        data_lines.append(("= Total Charges Salariales", -results['employee_charges'], "Total"))
        data_lines.append(("", 0, "Empty"))

        # NET AVANT IMPOT = BRUT - CHARGES SAL
        data_lines.append(("= NET AVANT IMPOT", results['net_before_tax'], "Total"))
        data_lines.append(("", 0, "Empty"))
        data_lines.append(("= NET A PAYER (Net + Frais)", results['net_payable'], "Final"))

        df_disp = pd.DataFrame(data_lines, columns=["Libelle", "Montant", "Type"])

        st.dataframe(
            df_disp[df_disp["Type"] != "Empty"][["Libelle", "Montant"]]
            .style.format({"Montant": "{:,.2f} EUR"}),
            use_container_width=True,
            hide_index=True,
            height=600
        )

        # --- Expander : Detail Cotisations Patronales ---
        with st.expander("Detail Cotisations Patronales (ligne par ligne)"):
            effectif_label = "< 50 salaries" if not results.get('effectif_sup_50', False) else ">= 50 salaries"
            fnal_rate_txt = "0.10%" if not results.get('effectif_sup_50', False) else "0.50%"

            taux_source = "configure" if st.session_state.cfg_taux_charges_override > 0 else "calcule"
            st.info(f"**Effectif : {effectif_label}** | FNAL {fnal_rate_txt} | AT/MP {st.session_state.cfg_taux_atmp:.2f}% | Taux de charges : {results['taux_charges']*100:.2f}% ({taux_source})")

            pat_lines = [d for d in results['cotis_details'] if d['montant_pat'] > 0]
            df_pat = pd.DataFrame([{
                "Cotisation": COTISATIONS_LABELS.get(d['nom'], d['nom']),
                "Base": d['base'],
                "Taux": f"{d['taux_pat']*100:.3f}%",
                "Montant": d['montant_pat']
            } for d in pat_lines])

            st.dataframe(
                df_pat.style.format({"Base": "{:,.2f}", "Montant": "{:,.2f}"}),
                use_container_width=True, hide_index=True
            )

            st.markdown(f"""
**Sous-total cotisations** : **{results['cotis_total_pat']:,.2f} EUR**

**+ Mutuelle Part Patronale** : {results['mutuelle_part_pat']:,.2f} EUR
**+ Titres Restaurant Part Patronale** : {results['tr_part_pat']:,.2f} EUR
**+ Forfait Social Prevoyance** (8% de {results['prev_pat_total']:,.2f}) : {results['forfait_social']:,.2f} EUR
**- Reduction RGDU 2026** : {results.get('reduction_rgdu', 0):,.2f} EUR

---
**TOTAL CHARGES PATRONALES = {results['employer_charges']:,.2f} EUR**
            """)

        # --- Expander : Detail Cotisations Salariales ---
        with st.expander("Detail Cotisations Salariales (ligne par ligne)"):
            sal_lines = [d for d in results['cotis_details'] if d['montant_sal'] > 0]
            df_sal = pd.DataFrame([{
                "Cotisation": COTISATIONS_LABELS.get(d['nom'], d['nom']),
                "Base": d['base'],
                "Taux": f"{d['taux_sal']*100:.3f}%",
                "Montant": d['montant_sal']
            } for d in sal_lines])

            st.dataframe(
                df_sal.style.format({"Base": "{:,.2f}", "Montant": "{:,.2f}"}),
                use_container_width=True, hide_index=True
            )

            st.markdown(f"""
**Sous-total cotisations** : **{results['cotis_total_sal']:,.2f} EUR**

**+ Mutuelle Part Salariale** : {results['mutuelle_part_sal']:,.2f} EUR
**+ Titres Restaurant Part Salariale** : {results['tr_part_sal']:,.2f} EUR

---
**TOTAL CHARGES SALARIALES = {results['employee_charges']:,.2f} EUR**
            """)

        # --- Expander : Formules de Calcul ---
        with st.expander("Formules de Calcul"):
            st.markdown(f"""
**Tranches :**
- Tranche A (PMSS) = min(Brut, {st.session_state.cfg_pmss:,.2f}) = **{results['tranche_a']:,.2f} EUR**
- Tranche B = max(0, Brut - PMSS) = **{results['tranche_b']:,.2f} EUR**
- Base CSG = 98.25% x Brut + Contrib. prevoyance pat = **{results['base_csg']:,.2f} EUR**

**NET AVANT IMPOT**
```
= BRUT - CHARGES SALARIALES
= {results['gross_salary']:,.2f} - {results['employee_charges']:,.2f}
= {results['net_before_tax']:,.2f} EUR
```

**NET A PAYER**
```
= NET AVANT IMPOT + FRAIS REMBOURSES
= {results['net_before_tax']:,.2f} + {results['total_frais_rembourses']:,.2f}
= {results['net_payable']:,.2f} EUR
```

**COUT GLOBAL SANS RESERVE**
```
= BRUT + CHARGES PATRONALES + TOTAL FRAIS
= {results['gross_salary']:,.2f} + {results['employer_charges']:,.2f} + {results['total_frais_rembourses']:,.2f}
= {results['cout_global_sans_reserve']:,.2f} EUR
```

**PROVISION RESERVE FINANCIERE**
```
= MONTANT DISPO - (BRUT + CHARGES PAT)
= {results['budget_salaire']:,.2f} - ({results['gross_salary']:,.2f} + {results['employer_charges']:,.2f})
= {results['provision_reserve_financiere']:,.2f} EUR
```
*(dont reserve brute {results['reserve_amount']:,.2f} EUR + charges futures {results['provision_reserve_financiere'] - results['reserve_amount']:,.2f} EUR)*
            """)

    with col_viz:
        st.subheader("Repartition")
        charges_cotis = (results['cotis_total_pat'] + results['cotis_total_sal']
                         + results['forfait_social'] - results['reduction_rgdu'])
        charges_mutuelle_tr = (results['mutuelle_part_pat'] + results['mutuelle_part_sal']
                               + results['tr_part_pat'] + results['tr_part_sal'])
        labels = ['Net Avant Impot', 'Cotisations Sociales', 'Mutuelle & TR', 'Frais Gestion', 'Provision Reserve']
        values = [results['net_before_tax'],
                  charges_cotis,
                  charges_mutuelle_tr,
                  results['management_fees'] + results['frais_intermediation'],
                  results.get('provision_reserve_financiere', 0)]

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Export")
        pdf_bytes = create_pdf(results, consultant_name)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = (
            f'<a href="data:application/octet-stream;base64,{b64}" download="simulation_{consultant_name}.pdf" style="text-decoration:none;">'
            f'<button style="width:100%; padding: 10px; background-color: #FF4B4B; color: white; border: none; border-radius: 5px; cursor: pointer;">'
            f'Telecharger le PDF</button></a>'
        )
        st.markdown(href, unsafe_allow_html=True)

with tab_config:
    st.header("Parametres Globaux de Calcul")
    st.warning("Ces modifications impactent tous les calculs. A modifier avec precaution.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("Salaires & Primes")
        st.session_state.cfg_base_salary = st.number_input(
            "Salaire de Base Temps Plein (EUR)",
            value=st.session_state.cfg_base_salary, step=50.0
        )
        st.session_state.cfg_taux_prime = st.number_input(
            "Taux Prime d'Apport (%)",
            value=st.session_state.cfg_taux_prime, step=0.1
        )
        st.session_state.cfg_taux_cp = st.number_input(
            "Taux Indemnite Conges Payes (%)",
            value=st.session_state.cfg_taux_cp, step=0.1
        )
        st.session_state.cfg_taux_reserve = st.number_input(
            "Taux Reserve Financiere (%)",
            value=st.session_state.cfg_taux_reserve, step=0.1
        )

    with c2:
        st.subheader("Cotisations & References")
        st.session_state.cfg_taux_charges_override = st.number_input(
            "TAUX DE CHARGES Silae (%)", min_value=0.0,
            value=st.session_state.cfg_taux_charges_override, format="%.4f", step=0.0001,
            help="0 = auto-calcul. Saisir le taux Silae pour matcher le complement de remuneration exactement."
        )
        st.session_state.cfg_taux_atmp = st.number_input(
            "Taux AT/MP (%)",
            value=st.session_state.cfg_taux_atmp, format="%.2f", step=0.01,
            help="Accident du Travail / Maladie Professionnelle. Seul taux patronal modifiable."
        )

        fnal_effectif = "0.10% (< 50 sal.)" if not effectif_sup_50 else "0.50% (>= 50 sal.)"
        st.info(f"**FNAL** : {fnal_effectif} (automatique selon effectif)")

        st.divider()
        st.session_state.cfg_pmss = st.number_input(
            "Plafond Secu (PMSS) (EUR)",
            value=st.session_state.cfg_pmss, step=100.0
        )
        st.session_state.cfg_smic_mensuel = st.number_input(
            "SMIC Mensuel Brut (EUR)",
            value=st.session_state.cfg_smic_mensuel, step=10.0
        )

        st.divider()
        st.subheader("Mutuelle")
        st.session_state.cfg_mutuelle_taux = st.number_input(
            "Taux Mutuelle (% du PMSS)",
            value=st.session_state.cfg_mutuelle_taux, step=0.1
        )
        st.session_state.cfg_mutuelle_part_pat = st.number_input(
            "Part Patronale Mutuelle (%)",
            value=st.session_state.cfg_mutuelle_part_pat, step=5.0
        )

    with c3:
        st.subheader("Frais & Divers")
        st.session_state.cfg_frais_gestion = st.number_input(
            "Frais de Gestion (%)",
            value=st.session_state.cfg_frais_gestion, step=0.5
        )

        st.markdown("**Taux IK** (defini automatiquement selon bareme URSSAF)")
        st.caption(f"Taux actuel : {st.session_state.cfg_ik_rate:.3f} EUR/km")

        st.divider()
        st.markdown("#### Baremes IGD URSSAF 2026")
        st.caption(f"Repas : {IGD_REPAS:.2f} EUR")
        st.caption(f"Nuitee Province : {IGD_NUITEE_PROVINCE:.2f} EUR")
        st.caption(f"Nuitee Paris/IDF : {IGD_NUITEE_PARIS:.2f} EUR")

        st.divider()
        st.markdown("#### Titres Restaurant")
        st.caption(f"Valeur faciale : {TR_VALEUR_FACIALE:.2f} EUR")
        st.caption(f"Part patronale max : {TR_PART_PATRONALE_MAX:.2f} EUR")

    # Tableau des taux fixes 2026 (lecture seule)
    st.divider()
    with st.expander("Taux de cotisations 2026 (lecture seule)"):
        taux_data = []
        for nom, cotis in COTISATIONS_2026.items():
            label = COTISATIONS_LABELS.get(nom, nom)
            base_label = {"TOTALITE": "Totalite", "TRANCHE_A": "Tranche A (PMSS)", "TRANCHE_B": "Tranche B", "CSG": "Base CSG"}.get(cotis["base"], cotis["base"])
            taux_data.append({
                "Cotisation": label,
                "Taux Patron": f"{cotis['pat']*100:.3f}%",
                "Taux Salarie": f"{cotis['sal']*100:.3f}%",
                "Base": base_label,
            })
        df_taux = pd.DataFrame(taux_data)
        st.dataframe(df_taux, use_container_width=True, hide_index=True, height=600)

    st.success("Les modifications sont prises en compte automatiquement dans l'onglet 'Resultats'.")

with tab_comm:
    c_expl, c_mail = st.columns(2)

    with c_expl:
        st.header("Comprendre le calcul")
        st.markdown("Voici l'explication detaillee etape par etape pour cette simulation precise (Bareme 2026) :")

        # Section 1 - Point de depart
        st.markdown("### 1. Le Point de Depart (CA)")
        st.markdown(f"Chiffre d'affaires = TJM x Jours = **{results['turnover']:,.2f} EUR**")

        # Section 2 - Deductions initiales
        st.markdown("### 2. Les Deductions Initiales")
        txt_deductions = f"- Frais de gestion ({st.session_state.cfg_frais_gestion}%) : **{results['management_fees']:,.2f} EUR**"
        if results['frais_intermediation'] > 0:
            txt_deductions += f"\n- Frais d'intermediation ({frais_intermediation_pct}%) : **{results['frais_intermediation']:,.2f} EUR**"
        txt_deductions += f"\n\n= **Montant Disponible : {results['montant_disponible']:,.2f} EUR**"
        st.markdown(txt_deductions)

        # Section 3 - Construction du brut
        st.markdown("### 3. La Construction du Brut")
        txt_brut = f"""- Salaire de Base (fixe) : **{results['base_salary']:,.2f} EUR**
- Prime Apport d'Affaires (5% du base) : **{results['prime_apport']:,.2f} EUR**
- Complement de Remuneration (variable) : **{results['complement_remuneration']:,.2f} EUR**
- Complement Apport d'Affaires (5% du complement) : **{results['complement_apport_affaires']:,.2f} EUR**
- Indemnite Conges Payes (10%) : **{results['indemnite_cp']:,.2f} EUR**

= **Salaire Brut Total : {results['gross_salary']:,.2f} EUR**

*Tranches : A = {results['tranche_a']:,.2f} EUR (PMSS) | B = {results['tranche_b']:,.2f} EUR*"""
        if results.get('provision_reserve_financiere', 0) > 0:
            txt_brut += f"\n\n*Provision Reserve Financiere : {results['provision_reserve_financiere']:,.2f} EUR (reserve + charges futures, hors brut)*"
        st.markdown(txt_brut)

        # Section 4 - Charges patronales (ligne par ligne)
        st.markdown("### 4. Les Charges Patronales (ligne par ligne)")
        effectif_expl = "< 50 salaries" if not results.get('effectif_sup_50', False) else ">= 50 salaries"
        fnal_expl = "0.10%" if not results.get('effectif_sup_50', False) else "0.50%"

        st.markdown(f"""
**Parametres :**
- Effectif entreprise : **{effectif_expl}**
- FNAL : **{fnal_expl}**
- AT/MP : **{st.session_state.cfg_taux_atmp:.2f}%**

**Cotisations patronales calculees ligne par ligne** (comme Silae)
- Total cotisations : **{results['cotis_total_pat']:,.2f} EUR** (detail dans l'onglet Resultats)
        """)

        st.markdown(f"""
**Elements supplementaires :**
- Mutuelle part patronale : **{results['mutuelle_part_pat']:,.2f} EUR**
- Titres Restaurant part patronale ({results['nb_titres_restaurant']} x {TR_PART_PATRONALE_MAX:.2f}) : **{results['tr_part_pat']:,.2f} EUR**
- Forfait Social Prevoyance (8% de {results['prev_pat_total']:,.2f}) : **{results['forfait_social']:,.2f} EUR**
        """)

        if results.get('reduction_rgdu', 0) > 0:
            st.markdown(f"""
**Reduction RGDU 2026 (obligatoire)** - Allegement charges patronales
- Seuil : Brut < 3 SMIC ({3 * st.session_state.cfg_smic_mensuel:,.2f} EUR)
- Votre brut : {results['gross_salary']:,.2f} EUR (eligible)
- Reduction calculee : **-{results['reduction_rgdu']:,.2f} EUR**
            """)

        st.success(f"""
**TOTAL CHARGES PATRONALES**
= Cotisations ({results['cotis_total_pat']:,.2f}) + Mutuelle ({results['mutuelle_part_pat']:,.2f}) + TR ({results['tr_part_pat']:,.2f}) + Forfait Social ({results['forfait_social']:,.2f}) - RGDU ({results.get('reduction_rgdu', 0):,.2f})
= **{results['employer_charges']:,.2f} EUR**
        """)

        # Expander tableau cotisations patronales
        with st.expander("Tableau cotisations patronales 2026"):
            pat_lines = [d for d in results['cotis_details'] if d['montant_pat'] > 0]
            df_pat_expl = pd.DataFrame([{
                "Cotisation": COTISATIONS_LABELS.get(d['nom'], d['nom']),
                "Base": d['base'],
                "Taux": f"{d['taux_pat']*100:.3f}%",
                "Montant": d['montant_pat']
            } for d in pat_lines])
            st.dataframe(
                df_pat_expl.style.format({"Base": "{:,.2f}", "Montant": "{:,.2f}"}),
                use_container_width=True, hide_index=True
            )

        # Section 5 - Frais rembourses
        st.markdown("### 5. Les Frais Rembourses (non imposables)")
        txt_frais = ""
        if results['ik_amount'] > 0:
            txt_frais += f"- IK selon bareme URSSAF ({st.session_state.cfg_ik_rate:.3f} EUR/km) : **{results['ik_amount']:,.2f} EUR**\n"
        if results['igd_amount'] > 0:
            txt_frais += f"- IGD (repas + nuitees) : **{results['igd_amount']:,.2f} EUR**\n"
        if results.get('forfait_teletravail', 0) > 0:
            txt_frais += f"- Forfait Teletravail ({results['jours_teletravail']}j x 2.70) : **{results['forfait_teletravail']:,.2f} EUR**\n"
        if results['other_expenses'] > 0:
            txt_frais += f"- Autres frais : **{results['other_expenses']:,.2f} EUR**\n"
        txt_frais += f"\n= **Total Frais Rembourses : {results['total_frais_rembourses']:,.2f} EUR**"
        st.markdown(txt_frais)

        # Section 6 - Cout global
        st.markdown("### 6. Le Cout Global Sans Reserve")
        st.markdown(f"""
**COUT GLOBAL SANS RESERVE = BRUT + CHARGES PATRONALES + TOTAL FRAIS**

= {results['gross_salary']:,.2f} + {results['employer_charges']:,.2f} + {results['total_frais_rembourses']:,.2f} = **{results['cout_global_sans_reserve']:,.2f} EUR**
        """)

        # Section 7 - Reserve
        if use_reserve and results.get('provision_reserve_financiere', 0) > 0:
            st.markdown("### 7. La Provision Reserve Financiere")
            st.markdown(f"""
**PROVISION RESERVE FINANCIERE = MONTANT DISPO - (BRUT + CHARGES PAT)**

= {results['budget_salaire']:,.2f} - ({results['gross_salary']:,.2f} + {results['employer_charges']:,.2f})
= **{results['provision_reserve_financiere']:,.2f} EUR**

*Dont reserve brute : {results['reserve_amount']:,.2f} EUR (base x {st.session_state.cfg_taux_reserve}%)*
*Dont charges futures sur reserve : {results['provision_reserve_financiere'] - results['reserve_amount']:,.2f} EUR*

*Cet argent reste a vous ! Il sert a financer vos periodes d'intercontrat ou est verse en fin de contrat.*
            """)

        # Section 8 - Charges salariales (ligne par ligne)
        st.markdown("### 8. Les Charges Salariales (ligne par ligne)")

        st.markdown(f"""
**Cotisations salariales calculees ligne par ligne** (comme Silae)
- Total cotisations : **{results['cotis_total_sal']:,.2f} EUR** (detail dans l'onglet Resultats)

**Elements supplementaires :**
- Mutuelle part salariale : **{results['mutuelle_part_sal']:,.2f} EUR**
- Titres Restaurant part salariale ({results['nb_titres_restaurant']} x {TR_PART_PATRONALE_MAX:.2f}) : **{results['tr_part_sal']:,.2f} EUR**
        """)

        st.success(f"""
**TOTAL CHARGES SALARIALES**
= Cotisations ({results['cotis_total_sal']:,.2f}) + Mutuelle ({results['mutuelle_part_sal']:,.2f}) + TR ({results['tr_part_sal']:,.2f})
= **{results['employee_charges']:,.2f} EUR**
        """)

        # Expander tableau cotisations salariales
        with st.expander("Tableau cotisations salariales 2026"):
            sal_lines = [d for d in results['cotis_details'] if d['montant_sal'] > 0]
            df_sal_expl = pd.DataFrame([{
                "Cotisation": COTISATIONS_LABELS.get(d['nom'], d['nom']),
                "Base": d['base'],
                "Taux": f"{d['taux_sal']*100:.3f}%",
                "Montant": d['montant_sal']
            } for d in sal_lines])
            st.dataframe(
                df_sal_expl.style.format({"Base": "{:,.2f}", "Montant": "{:,.2f}"}),
                use_container_width=True, hide_index=True
            )

        # Section 9 - Net final
        st.markdown("### 9. Le Net Final")
        st.markdown(f"""
**NET AVANT IMPOT = BRUT - CHARGES SALARIALES**

= {results['gross_salary']:,.2f} - {results['employee_charges']:,.2f} = **{results['net_before_tax']:,.2f} EUR**
        """)

        st.success(f"""
**NET A PAYER = NET AVANT IMPOT + FRAIS REMBOURSES**

= {results['net_before_tax']:,.2f} + {results['total_frais_rembourses']:,.2f} = **{results['net_payable']:,.2f} EUR**
        """)

    with c_mail:
        st.header("Email type pour le consultant")
        st.markdown("Copiez ce texte pour accompagner l'envoi du PDF (Donnees 2026).")

        # Frais rembourses
        txt_frais = ""
        if results['total_frais_rembourses'] > 0:
            txt_frais = f"\n*   Le remboursement de vos frais professionnels pour **{results['total_frais_rembourses']:,.2f} EUR** (non imposables)."

            # Detail des frais
            details_frais = []
            if results['ik_amount'] > 0:
                details_frais.append(f"IK ({st.session_state.cfg_ik_rate:.3f} EUR/km) : {results['ik_amount']:,.2f} EUR")
            if results['igd_amount'] > 0:
                details_frais.append(f"IGD : {results['igd_amount']:,.2f} EUR")
            if results.get('forfait_teletravail', 0) > 0:
                details_frais.append(f"Teletravail ({results['jours_teletravail']}j) : {results['forfait_teletravail']:,.2f} EUR")
            if results['other_expenses'] > 0:
                details_frais.append(f"Autres frais : {results['other_expenses']:,.2f} EUR")

            if details_frais:
                txt_frais += "\n    (" + ", ".join(details_frais) + ")"

        # Frais intermediation
        txt_intermediation = ""
        if results['frais_intermediation'] > 0:
            txt_intermediation = f"\nNote : Des frais d'intermediation de {results['frais_intermediation']:,.2f} EUR ({frais_intermediation_pct}%) ont ete deduits du CA."

        # Mutuelle
        txt_mutuelle = ""
        if use_mutuelle:
            txt_mutuelle = "\n- Sante : Mutuelle d'entreprise incluse (prise en charge a 50%)."

        # Reserve
        txt_reserve_mail = ""
        if use_reserve and results['reserve_amount'] > 0:
            txt_reserve_mail = f"\n- Epargne : Une reserve financiere de **{results['reserve_amount']:,.2f} EUR** est constituee ce mois-ci (disponible en fin de contrat)."

        # Titres restaurant
        txt_tr = ""
        if results['nb_titres_restaurant'] > 0:
            txt_tr = f"\n- Titres Restaurant : {results['nb_titres_restaurant']} titres (part patronale {results['tr_part_pat']:,.2f} EUR)."

        # RGDU
        txt_rgdu = ""
        if results.get('reduction_rgdu', 0) > 0:
            txt_rgdu = f"\n- RGDU 2026 : Reduction des charges patronales de {results['reduction_rgdu']:,.2f} EUR (allegement automatique)."

        email_content = f"""Objet : Votre simulation de revenus - TJM {tjm} EUR

Bonjour {consultant_name},

Suite a nos echanges, j'ai le plaisir de vous transmettre votre simulation de salaire personnalisee, basee sur un TJM de {tjm} EUR et {days_worked_month} jours d'activite.
{txt_intermediation}
Voici la synthese de votre projection pour ce mois :

VOTRE NET A PAYER ESTIME : {results['net_payable']:,.2f} EUR
(Montant vire sur votre compte bancaire)

Ce montant comprend :
*   Votre Salaire Net (apres deduction de toutes les charges sociales).{txt_frais}

Les points cles de cette simulation :{txt_mutuelle}{txt_reserve_mail}{txt_tr}{txt_rgdu}
- Securite : Cotisations completes (Chomage, Retraite Cadre, Securite Sociale).
- Transparence : Tout est detaille dans le PDF ci-joint (Baremes 2026).

Detail du calcul :
- Salaire de Base : {results['base_salary']:,.2f} EUR
- Prime d'apport d'affaires : {results['prime_apport']:,.2f} EUR
- Complement de remuneration : {results['complement_remuneration']:,.2f} EUR
- Complement Apport d'Affaires : {results['complement_apport_affaires']:,.2f} EUR
- Indemnite Conges Payes : {results['indemnite_cp']:,.2f} EUR
= Salaire Brut Total : {results['gross_salary']:,.2f} EUR
- Charges Salariales : {results['employee_charges']:,.2f} EUR
- Charges Patronales : {results['employer_charges']:,.2f} EUR
- Net Avant Impot : {results['net_before_tax']:,.2f} EUR

Je reste a votre disposition pour affiner ces chiffres ou pour preparer votre contrat.

Bien cordialement,

L'equipe Portage"""

        st.text_area("Sujet & Corps du message", email_content, height=550)
