import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
import base64
import requests
import tempfile
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

# Baremes IGD URSSAF 2026 - Complet avec duree de mission
IGD_BAREME_2026 = {
    "moins_3_mois":  {"repas": 21.40, "nuitee_paris": 76.60, "nuitee_province": 56.80},
    "3_a_24_mois":   {"repas": 18.20, "nuitee_paris": 65.10, "nuitee_province": 48.30},
    "24_a_72_mois":  {"repas": 15.00, "nuitee_paris": 53.60, "nuitee_province": 39.80},
}

# Membres BU Portage Salarial
MEMBRES_BU = [
    "Gwenaelle CHARPENTIER - Directrice du Pole Portage Salarial",
    "Membre BU 2",
    "Membre BU 3",
]

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
if 'cfg_pct_tel_internet' not in st.session_state:
    st.session_state.cfg_pct_tel_internet = 50.0
if 'cfg_pct_transport' not in st.session_state:
    st.session_state.cfg_pct_transport = 50.0


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


# --- API Adresse & Calcul Km ---
@st.cache_data(ttl=3600)
def geocoder_adresse(adresse):
    """Geocode une adresse via api-adresse.data.gouv.fr (gratuit, pas de cle API)"""
    if not adresse or len(adresse.strip()) < 5:
        return None
    try:
        resp = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": adresse, "limit": 5},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("features"):
                results = []
                for f in data["features"]:
                    props = f["properties"]
                    coords = f["geometry"]["coordinates"]  # [lon, lat]
                    results.append({
                        "label": props.get("label", ""),
                        "lon": coords[0],
                        "lat": coords[1],
                        "score": props.get("score", 0),
                    })
                return results
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def calculer_distance_osrm(lat1, lon1, lat2, lon2):
    """Calcule la distance route via OSRM (gratuit, trajet le plus court)"""
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
        resp = requests.get(url, params={"overview": "false"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes"):
                distance_m = data["routes"][0]["distance"]
                duree_s = data["routes"][0]["duration"]
                return {
                    "distance_km": round(distance_m / 1000, 1),
                    "duree_min": round(duree_s / 60, 0),
                }
    except Exception:
        pass
    return None


# --- Moteur de Calcul ---
def calculate_salary(tjm, days_worked_month, days_worked_week,
                     ik_amount, igd_amount, other_expenses, use_reserve, use_mutuelle,
                     nb_titres_restaurant=0, frais_intermediation_pct=0.0,
                     jours_teletravail=0, effectif_sup_50=False,
                     frais_partages_pct=0.0, commission_apporteur=0.0,
                     type_contrat="CDI", provision_cp=False):

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

    # CA et deductions
    turnover = tjm * days_worked_month
    management_fees = turnover * rate_gestion
    frais_intermediation = turnover * (frais_intermediation_pct / 100.0)
    frais_partages = turnover * (frais_partages_pct / 100.0)

    # Montant disponible = CA - Gestion - Intermediation - Partages - Commission
    montant_disponible = turnover - management_fees - frais_intermediation - frais_partages - commission_apporteur

    # Total des frais rembourses
    total_frais_rembourses = ik_amount + igd_amount + forfait_teletravail + other_expenses

    base_salary = cfg_base * (days_worked_week / 5.0)
    prime_apport = base_salary * rate_prime

    # Reserve financiere / Indemnite de precarite (CDD)
    rate_reserve = st.session_state.cfg_taux_reserve / 100.0
    reserve_brute = base_salary * rate_reserve

    budget_salaire = montant_disponible - total_frais_rembourses
    taux_charges_override = st.session_state.cfg_taux_charges_override / 100.0
    reserve_reintegree = not use_reserve

    if taux_charges_override > 0:
        taux_charges = taux_charges_override
    else:
        taux_charges = 0.55
        for _ in range(50):
            pool = budget_salaire / (1 + taux_charges)
            ct_est = max(0, pool - base_salary - prime_apport - reserve_brute)

            if reserve_reintegree:
                # Reserve DANS le brut : ICP sur (base+prime+reserve+complement)
                brut_components = base_salary + prime_apport + reserve_brute + ct_est
                brut_est = brut_components * (1 + rate_cp)
                ta = min(brut_est, pmss)
                tb = max(0, brut_est - pmss)
                pd_ = round(ta * 0.0159, 2)
                ps_ = round(tb * 0.0073, 2) if tb > 0 else 0.0
                pt_ = pd_ + mutuelle_part_pat + ps_
                c_ = calculer_cotisations(brut_est, pmss, atmp_rate, fnal_rate, pt_)
                fs_ = round(pt_ * 0.08, 2)
                icp_ = brut_components * rate_cp
                ch = c_["total_pat"] + mutuelle_part_pat + tr_part_pat + fs_ + icp_
                tn = ch / pool if pool > 0 else 0
            else:
                # Reserve HORS brut : charges marginales sur reserve
                brut_components = base_salary + prime_apport + ct_est
                brut_est = brut_components * (1 + rate_cp)
                ta = min(brut_est, pmss)
                tb = max(0, brut_est - pmss)
                pd_ = round(ta * 0.0159, 2)
                ps_ = round(tb * 0.0073, 2) if tb > 0 else 0.0
                pt_ = pd_ + mutuelle_part_pat + ps_
                c_ = calculer_cotisations(brut_est, pmss, atmp_rate, fnal_rate, pt_)
                fs_ = round(pt_ * 0.08, 2)
                icp_ = brut_components * rate_cp
                ch_brut = c_["total_pat"] + mutuelle_part_pat + tr_part_pat + fs_ + icp_
                reserve_brut_cp = reserve_brute * (1 + rate_cp)
                brut_avec_reserve = brut_est + reserve_brut_cp
                ta2 = min(brut_avec_reserve, pmss)
                tb2 = max(0, brut_avec_reserve - pmss)
                pd2 = round(ta2 * 0.0159, 2)
                ps2 = round(tb2 * 0.0073, 2) if tb2 > 0 else 0.0
                pt2 = pd2 + mutuelle_part_pat + ps2
                c2_ = calculer_cotisations(brut_avec_reserve, pmss, atmp_rate, fnal_rate, pt2)
                fs2 = round(pt2 * 0.08, 2)
                ch_reserve = (c2_["total_pat"] + fs2) - (c_["total_pat"] + fs_) + reserve_brute * rate_cp + mutuelle_part_pat * (reserve_brute / pool if pool > 0 else 0)
                tn = (ch_brut + ch_reserve) / pool if pool > 0 else 0

            if abs(tn - taux_charges) < 0.00001:
                taux_charges = tn
                break
            taux_charges = tn

    # --- Resultats depuis le taux converge ---
    pool = budget_salaire / (1 + taux_charges)
    complement_total = max(0, pool - base_salary - prime_apport - reserve_brute)
    complement_remuneration = complement_total / (1 + rate_prime)
    complement_apport_affaires = complement_total - complement_remuneration

    if reserve_reintegree:
        # Reserve dans le brut, ICP inclut la reserve
        brut_base = base_salary + prime_apport + reserve_brute + complement_total
        indemnite_cp = brut_base * rate_cp
        gross_salary = brut_base + indemnite_cp
    else:
        # Reserve hors brut
        brut_base = base_salary + prime_apport + complement_total
        indemnite_cp = brut_base * rate_cp
        gross_salary = brut_base + indemnite_cp

    # Cotisations reelles sur le brut
    tranche_a = min(gross_salary, pmss)
    tranche_b = max(0, gross_salary - pmss)
    prev_deces_pat = round(tranche_a * 0.0159, 2)
    prev_supp_pat = round(tranche_b * 0.0073, 2) if tranche_b > 0 else 0.0
    prev_pat_total = prev_deces_pat + mutuelle_part_pat + prev_supp_pat
    cotis = calculer_cotisations(gross_salary, pmss, atmp_rate, fnal_rate, prev_pat_total)
    forfait_social = round(prev_pat_total * 0.08, 2)

    # RGDU (toujours appliquee)
    reduction_rgdu = calculer_rgdu(gross_salary, smic, use_fnal_50=effectif_sup_50)

    # Charges patronales totales
    employer_charges_avant_rgdu = cotis["total_pat"] + mutuelle_part_pat + tr_part_pat + forfait_social
    employer_charges = employer_charges_avant_rgdu - reduction_rgdu

    # Charges salariales totales
    employee_charges = cotis["total_sal"] + mutuelle_part_sal + tr_part_sal

    # Provision reserve / indemnite precarite
    if reserve_reintegree:
        provision_reserve_financiere = 0
    else:
        provision_reserve_financiere = max(0, budget_salaire - gross_salary - employer_charges)

    reserve_amount = reserve_brute

    # Cout global = Brut + Charges Pat + Frais
    cout_global = gross_salary + employer_charges + total_frais_rembourses

    # Net
    net_before_tax = gross_salary - employee_charges
    net_payable = net_before_tax + total_frais_rembourses

    # --- Provision Conges Payes ---
    provision_cp_amount = 0
    brut_hors_cp = gross_salary
    employee_charges_hors_cp = employee_charges
    net_hors_cp = net_before_tax

    if provision_cp and indemnite_cp > 0:
        brut_hors_cp = gross_salary - indemnite_cp
        ta_hcp = min(brut_hors_cp, pmss)
        tb_hcp = max(0, brut_hors_cp - pmss)
        pd_hcp = round(ta_hcp * 0.0159, 2)
        ps_hcp = round(tb_hcp * 0.0073, 2) if tb_hcp > 0 else 0.0
        pt_hcp = pd_hcp + mutuelle_part_pat + ps_hcp
        cotis_hcp = calculer_cotisations(brut_hors_cp, pmss, atmp_rate, fnal_rate, pt_hcp)
        fs_hcp = round(pt_hcp * 0.08, 2)
        rgdu_hcp = calculer_rgdu(brut_hors_cp, smic, use_fnal_50=effectif_sup_50)
        employer_charges_hcp = cotis_hcp["total_pat"] + mutuelle_part_pat + tr_part_pat + fs_hcp - rgdu_hcp
        employee_charges_hors_cp = cotis_hcp["total_sal"] + mutuelle_part_sal + tr_part_sal
        cout_global_hcp = brut_hors_cp + employer_charges_hcp + total_frais_rembourses
        provision_cp_amount = cout_global - cout_global_hcp
        net_hors_cp = brut_hors_cp - employee_charges_hors_cp

    # Label selon type de contrat
    label_reserve = "Indemnite de precarite" if type_contrat == "CDD" else "Reserve financiere"

    return {
        "tjm": tjm,
        "days_worked_month": days_worked_month,
        "turnover": turnover,
        "management_fees": management_fees,
        "frais_intermediation": frais_intermediation,
        "frais_partages": frais_partages,
        "commission_apporteur": commission_apporteur,
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
        "reserve_brute": reserve_brute,
        "reserve_amount": reserve_amount,
        "reserve_reintegree": reserve_reintegree,
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
        "cout_global": cout_global,
        "net_before_tax": net_before_tax,
        "net_payable": net_payable,
        "effectif_sup_50": effectif_sup_50,
        "taux_charges": taux_charges,
        "pool_silae": pool,
        "provision_reserve_financiere": provision_reserve_financiere,
        "budget_salaire": budget_salaire,
        "type_contrat": type_contrat,
        "label_reserve": label_reserve,
        "provision_cp": provision_cp,
        "provision_cp_amount": provision_cp_amount,
        "brut_hors_cp": brut_hors_cp,
        "employee_charges_hors_cp": employee_charges_hors_cp,
        "net_hors_cp": net_hors_cp,
    }

# --- Chemin logo ---
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_signe_plus.png")


def _generer_camembert_pdf(data):
    """Genere le camembert en PNG pour insertion dans le PDF (avec titre et legende)"""
    frais_gestion_total = (data['management_fees'] + data['frais_intermediation']
                           + data.get('frais_partages', 0) + data.get('commission_apporteur', 0))
    cotis_sociales = (data['cotis_total_pat'] + data['cotis_total_sal']
                      + data['forfait_social'] - data['reduction_rgdu']
                      + data['mutuelle_part_pat'] + data['mutuelle_part_sal']
                      + data['tr_part_pat'] + data['tr_part_sal'])
    provision_viz = data['provision_reserve_financiere'] if not data.get('reserve_reintegree', False) else 0

    labels = ['Net a payer', 'Frais de gestion', 'Cotisations Sociales\net Patronales', 'Provision Reserve']
    values = [data['net_payable'], frais_gestion_total, cotis_sociales, provision_viz]
    colors = ['#4A90D9', '#757575', '#E91E63', '#F8BBD0']

    # Filtrer les valeurs nulles
    filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not filtered:
        return None
    labels_f, values_f, colors_f = zip(*filtered)

    fig, ax = plt.subplots(figsize=(3.5, 4.2))
    ax.set_title("Ventilation chiffre d'affaires", fontsize=9, fontweight='bold', pad=12, color='#333333')
    wedges, texts, autotexts = ax.pie(
        values_f, colors=colors_f,
        autopct='%1.1f%%', textprops={'fontsize': 7}, pctdistance=0.78,
        startangle=90
    )
    for t in texts:
        t.set_fontsize(0)
    for t in autotexts:
        t.set_fontsize(6.5)
        t.set_color('white')
        t.set_weight('bold')
    centre_circle = plt.Circle((0, 0), 0.40, fc='white')
    ax.add_artist(centre_circle)

    # Legende en dessous du camembert
    legend = ax.legend(wedges, labels_f, loc='upper center', bbox_to_anchor=(0.5, -0.02),
                       ncol=2, fontsize=6.5, frameon=False,
                       handlelength=1.2, handletextpad=0.4, columnspacing=1.0)
    for handle in legend.legend_handles:
        handle.set_width(8)
        handle.set_height(8)

    plt.tight_layout()

    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.savefig(tmp.name, dpi=170, bbox_inches='tight', transparent=True, facecolor='white')
    plt.close()
    return tmp.name


# --- Couleurs S+ ---
ROSE_R, ROSE_G, ROSE_B = 233, 30, 99
ROSE_CLAIR_R, ROSE_CLAIR_G, ROSE_CLAIR_B = 252, 228, 236
ROSE_FOND_R, ROSE_FOND_G, ROSE_FOND_B = 252, 228, 236  # FCE4EC
GRIS_R, GRIS_G, GRIS_B = 245, 245, 245
CHARCOAL_R, CHARCOAL_G, CHARCOAL_B = 50, 50, 50


# --- Chemin police Unicode (bundlees dans le projet) ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(_BASE_DIR, "fonts", "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(_BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
FONT_ITALIC_PATH = os.path.join(_BASE_DIR, "fonts", "DejaVuSans-Oblique.ttf")


def _dotted_line(label, value_str, total_chars=62):
    """Helper : construit une ligne avec pointilles entre label et valeur."""
    space = total_chars - len(label) - len(value_str)
    if space < 2:
        space = 2
    return f"{label} {'.' * space} {value_str}"


# --- PDF Generation (V5 dark bg + white container + dotted leaders) ---
def create_pdf(data, name, membre_bu=""):
    pdf = FPDF()
    pdf.add_page()
    pw = 210  # page width
    ph = 297  # page height

    # Police Unicode pour accents
    pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
    pdf.add_font("DejaVu", "B", FONT_BOLD_PATH, uni=True)
    pdf.add_font("DejaVu", "I", FONT_ITALIC_PATH, uni=True)

    # =============================================
    # FOND GRIS CHARCOAL SUR TOUTE LA PAGE
    # =============================================
    pdf.set_fill_color(CHARCOAL_R, CHARCOAL_G, CHARCOAL_B)
    pdf.rect(0, 0, pw, ph, 'F')

    # =============================================
    # BANDEAU ROSE EN-TETE (full width, dans le gris)
    # =============================================
    banner_h = 28
    pdf.set_fill_color(ROSE_R, ROSE_G, ROSE_B)
    pdf.rect(0, 0, pw, banner_h, 'F')

    # Logo sur fond rose
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=8, y=4, w=45)

    # Parametres dans le bandeau (4 colonnes)
    pdf.set_text_color(255, 255, 255)
    t_gest = st.session_state.cfg_frais_gestion
    nb_tr = data.get('nb_titres_restaurant', 0)
    v_tjm = data.get('tjm', 0)
    v_jours = data.get('days_worked_month', 0)
    col_w = 33
    x_start = 62

    # Labels
    pdf.set_font("DejaVu", 'B', size=6.5)
    pdf.set_xy(x_start, 5)
    pdf.cell(col_w, 4, txt="TJM", align='C')
    pdf.cell(col_w, 4, txt="Nb de jours / mois", align='C')
    pdf.cell(col_w, 4, txt="Frais de gestion", align='C')
    pdf.cell(col_w, 4, txt="Tickets-Restaurants", align='C')

    # Valeurs
    pdf.set_font("DejaVu", 'B', size=12)
    pdf.set_xy(x_start, 12)
    pdf.cell(col_w, 7, txt=f"{v_tjm:.0f}\u20ac", align='C')
    pdf.cell(col_w, 7, txt=f"{v_jours:g}j", align='C')
    pdf.cell(col_w, 7, txt=f"{t_gest}%", align='C')
    pdf.cell(col_w, 7, txt=f"{'Oui' if nb_tr > 0 else 'Non'}", align='C')

    # =============================================
    # CONTENEUR BLANC (rectangle avec coins simules)
    # =============================================
    container_x = 10
    container_y = banner_h + 5
    container_w = pw - 20
    container_bottom = ph - 42  # reserve pour footer gris
    container_h = container_bottom - container_y
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(container_x, container_y, container_w, container_h, 'F')

    # =============================================
    # TITRE SIMULATION
    # =============================================
    margin_left = container_x + 5
    content_w = container_w - 10
    pdf.set_xy(container_x, container_y + 5)
    pdf.set_font("DejaVu", 'B', size=18)
    pdf.set_text_color(ROSE_R, ROSE_G, ROSE_B)
    pdf.cell(container_w, 10, txt="SIMULATION", ln=1, align="C")
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("DejaVu", "", size=10)
    pdf.set_x(container_x)
    pdf.cell(container_w, 6, txt=name, ln=1, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # =============================================
    # DEUX COLONNES : Salaire (gauche) | Camembert (droite)
    # =============================================
    y_cols = pdf.get_y()
    col_left_x = margin_left
    col_left_w = 98  # largeur colonne texte

    # --- Colonne gauche : decomposition salaire avec pointilles ---
    sal_lines = [
        ("Salaire de base", data['base_salary']),
        ("Prime d'apport d'affaires", data['prime_apport']),
        ("Compl\u00e9ment de r\u00e9mun\u00e9ration", data['complement_remuneration']),
    ]
    if data.get('reserve_reintegree', False):
        label_res = data.get('label_reserve', 'R\u00e9serve financi\u00e8re')
        sal_lines.append((label_res.capitalize(), data['reserve_brute']))
    sal_lines.append(("Indemnit\u00e9 Cong\u00e9s Pay\u00e9s", data['indemnite_cp']))

    pdf.set_font("DejaVu", "", size=8.5)
    pdf.set_text_color(60, 60, 60)
    line_h = 5.5
    for (label, val) in sal_lines:
        val_str = f"{val:,.2f} \u20ac"
        dotted = _dotted_line(label, val_str, total_chars=58)
        pdf.set_xy(col_left_x, pdf.get_y())
        pdf.cell(col_left_w, line_h, txt=dotted, ln=1)

    # Ligne Salaire Brut (mise en valeur)
    pdf.ln(1)
    pdf.set_font("DejaVu", 'B', size=10)
    pdf.set_text_color(ROSE_R, ROSE_G, ROSE_B)
    brut_str = f"{data['gross_salary']:,.2f} \u20ac"
    dotted_brut = _dotted_line("Salaire Brut", brut_str, total_chars=52)
    pdf.set_x(col_left_x)
    pdf.cell(col_left_w, 7, txt=dotted_brut, ln=1)
    pdf.set_text_color(60, 60, 60)
    pdf.ln(2)

    # Charges salariales / patronales
    pdf.set_font("DejaVu", "", size=8.5)
    for (label, val) in [("Charges Salariales", data['employee_charges']),
                          ("Charges Patronales", data['employer_charges'])]:
        val_str = f"{val:,.2f} \u20ac"
        dotted = _dotted_line(label, val_str, total_chars=58)
        pdf.set_x(col_left_x)
        pdf.cell(col_left_w, line_h, txt=dotted, ln=1)

    y_after_left = pdf.get_y()

    # --- Colonne droite : camembert ---
    chart_path = _generer_camembert_pdf(data)
    if chart_path:
        chart_x = container_x + content_w - 80
        pdf.image(chart_path, x=chart_x, y=y_cols - 2, w=78)
        try:
            os.unlink(chart_path)
        except Exception:
            pass

    # Repositionner apres les deux colonnes
    pdf.set_y(max(y_after_left, y_cols + 72) + 4)

    # =============================================
    # SECTION VOS FRAIS
    # =============================================
    if data.get('total_frais_rembourses', 0) > 0:
        pdf.set_font("DejaVu", 'B', size=10)
        pdf.set_text_color(50, 50, 50)
        pdf.set_x(margin_left)
        pdf.cell(content_w, 7, txt="VOS FRAIS :", ln=1)
        pdf.set_font("DejaVu", "", size=8.5)
        pdf.set_text_color(60, 60, 60)
        frais_items = []
        if data.get('ik_amount', 0) > 0:
            frais_items.append(("Indemnit\u00e9s Kilom\u00e9triques", data['ik_amount']))
        if data.get('igd_amount', 0) > 0:
            frais_items.append(("Indemnit\u00e9s Grands D\u00e9placements", data['igd_amount']))
        if data.get('forfait_teletravail', 0) > 0:
            frais_items.append((f"Forfait T\u00e9l\u00e9travail ({data['jours_teletravail']}j x 2.70)", data['forfait_teletravail']))
        if data.get('other_expenses', 0) > 0:
            frais_items.append(("Autres Frais", data['other_expenses']))
        for (label, val) in frais_items:
            val_str = f"{val:,.2f} \u20ac"
            dotted = _dotted_line(label, val_str, total_chars=58)
            pdf.set_x(margin_left)
            pdf.cell(content_w, line_h, txt=dotted, ln=1)
        pdf.ln(4)

    # =============================================
    # ENCADRE ROSE CLAIR : BRUT AVEC RESERVE FINANCIERE
    # =============================================
    box_x = margin_left
    box_w = content_w
    if data.get('reserve_reintegree', False):
        pdf.set_fill_color(ROSE_FOND_R, ROSE_FOND_G, ROSE_FOND_B)
        pdf.set_text_color(ROSE_R, ROSE_G, ROSE_B)
        pdf.set_font("DejaVu", 'B', size=11)
        pdf.set_x(box_x)
        pdf.cell(box_w * 0.68, 10, txt="  BRUT AVEC R\u00c9SERVE FINANCI\u00c8RE*", border=0, fill=True)
        pdf.cell(box_w * 0.32, 10, txt=f"{data['gross_salary']:,.2f} \u20ac", border=0, align='R', fill=True, ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # =============================================
    # ENCADRE ROSE FORT : NET A PAYER
    # =============================================
    pdf.set_fill_color(ROSE_R, ROSE_G, ROSE_B)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", 'B', size=13)
    pdf.set_x(box_x)
    pdf.cell(box_w * 0.68, 12, txt="  NET \u00c0 PAYER AVANT IMP\u00d4TS", border=0, fill=True)
    pdf.set_font("DejaVu", 'B', size=15)
    pdf.cell(box_w * 0.32, 12, txt=f"{data['net_payable']:,.2f} \u20ac", border=0, align='R', fill=True, ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # =============================================
    # NOTE RESERVE
    # =============================================
    if data.get('reserve_brute', 0) > 0:
        label_res = data.get('label_reserve', 'R\u00e9serve financi\u00e8re')
        if not data.get('reserve_reintegree', False):
            pdf.set_font("DejaVu", 'B', size=7.5)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(margin_left)
            pdf.cell(content_w, 5, txt=f"*La {label_res} : {data['reserve_brute']:,.2f} \u20ac brut provisionnée tous les mois.", ln=1)
        pdf.set_font("DejaVu", 'I', size=6.5)
        pdf.set_text_color(120, 120, 120)
        pdf.set_x(margin_left)
        pdf.multi_cell(content_w, 3.2, txt=f"{label_res.capitalize()} : \u00e9quivalente \u00e0 10% du salaire de base mensuel, ce montant \u00ab mis en r\u00e9serve \u00bb chaque mois est une obligation l\u00e9gale conventionnelle pr\u00e9vue pour vous permettre lors de vos intermissions de faire face \u00e0 vos \u00e9ventuels frais de prospection voire \u00e0 financer votre indemnit\u00e9 de rupture conventionnelle. Cette r\u00e9serve vous appartient et vous est revers\u00e9e en fin de contrat de travail (solde de tout compte).")
        pdf.set_text_color(0, 0, 0)

    # Mutuelle
    if data.get('mutuelle_part_pat', 0) > 0:
        pdf.ln(1)
        pdf.set_font("DejaVu", 'I', size=7)
        pdf.set_text_color(120, 120, 120)
        pdf.set_x(margin_left)
        pdf.cell(content_w, 4, txt="Mutuelle d'entreprise incluse, prise en charge \u00e0 50 % dans la simulation pr\u00e9sent\u00e9e.", ln=1)
        pdf.set_text_color(0, 0, 0)

    # =============================================
    # FOOTER GRIS
    # =============================================
    footer_y = container_bottom + 3
    footer_h = ph - footer_y
    pdf.set_fill_color(70, 70, 70)
    pdf.rect(0, footer_y, pw, footer_h, 'F')

    # Logo dans le footer
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=12, y=footer_y + 5, w=35)

    # Signature dans le footer
    sig_x = 55
    sig_name = membre_bu if membre_bu else "Gwena\u00eblle CHARPENTIER"
    pdf.set_xy(sig_x, footer_y + 5)
    pdf.set_font("DejaVu", 'I', size=10)
    pdf.set_text_color(ROSE_R, ROSE_G, ROSE_B)
    pdf.cell(90, 6, txt=sig_name, ln=1)
    pdf.set_xy(sig_x, pdf.get_y())
    pdf.set_font("DejaVu", "", size=8)
    pdf.set_text_color(200, 200, 200)
    pdf.cell(90, 5, txt="Directrice du P\u00f4le Portage Salarial", ln=1)
    pdf.set_xy(sig_x, pdf.get_y())
    pdf.cell(90, 5, txt="01 85 53 47 00", ln=1)

    pdf.set_text_color(0, 0, 0)

    out = pdf.output(dest='S')
    return out.encode('latin-1', 'replace') if isinstance(out, str) else out

# --- UI Streamlit ---

st.set_page_config(page_title="Simulateur Portage Salarial 2026", layout="wide")

# Sidebar
with st.sidebar:
    st.title("Consultant")
    consultant_name = st.text_input("Nom", "Consultant")
    tjm = st.number_input("TJM (EUR)", min_value=0, value=500, step=10)
    frais_intermediation_pct = st.number_input("Frais d'intermediation (%)", value=0.0, step=0.5, min_value=0.0)

    st.markdown("---")
    st.subheader("Temps de Travail")
    type_contrat = st.radio("Type de contrat", ["CDI", "CDD"], horizontal=True)
    temps_travail = st.radio("Temps de travail", ["Complet", "Partiel"], horizontal=True)

    col_j1, col_j2 = st.columns(2)
    with col_j1:
        nb_journees = st.number_input("Nb Journees", value=19, step=1, min_value=0)
    with col_j2:
        nb_demi_journees = st.number_input("Nb Demi-journees", value=0, step=1, min_value=0)
    days_worked_month = nb_journees + nb_demi_journees * 0.5
    st.caption(f"Jours produits : **{days_worked_month}**")

    if temps_travail == "Partiel":
        days_worked_week = st.number_input("Jours / Sem", value=2.5, max_value=5.0, step=0.5)
    else:
        days_worked_week = st.number_input("Jours / Sem", value=5.0, max_value=7.0, step=0.5)

    st.markdown("---")
    st.subheader("Indemnites Kilometriques (IK)")

    type_vehicule = st.selectbox("Type de vehicule", ["Voiture Thermique", "Voiture Electrique", "Moto"])

    is_electrique = (type_vehicule == "Voiture Electrique")

    if type_vehicule in ("Voiture Thermique", "Voiture Electrique"):
        cv_options = [3, 4, 5, 6, 7]
        cv_fiscaux = st.selectbox("Chevaux fiscaux (CV)", cv_options, index=2)
        tranche_km = st.selectbox("Tranche kilometrique annuelle",
                                  ["Jusqu'a 5 000 km", "De 5 001 a 20 000 km", "Au-dela de 20 000 km"])
        if tranche_km == "Jusqu'a 5 000 km":
            ik_rate_base = BAREME_IK_VOITURE_2026[cv_fiscaux]["jusqua_5000"]
        elif tranche_km == "De 5 001 a 20 000 km":
            ik_rate_base = BAREME_IK_VOITURE_2026[cv_fiscaux]["de_5001_a_20000"]
        else:
            ik_rate_base = BAREME_IK_VOITURE_2026[cv_fiscaux]["au_dela_20000"]
    else:
        cv_options_moto = [1, 2, 3, 4, 5]
        cv_fiscaux = st.selectbox("Chevaux fiscaux (CV)", cv_options_moto, index=2)
        tranche_km = st.selectbox("Tranche kilometrique annuelle",
                                  ["Jusqu'a 3 000 km", "De 3 001 a 6 000 km", "Au-dela de 6 000 km"])
        if tranche_km == "Jusqu'a 3 000 km":
            ik_rate_base = BAREME_IK_MOTO_2026[cv_fiscaux]["jusqua_3000"]
        elif tranche_km == "De 3 001 a 6 000 km":
            ik_rate_base = BAREME_IK_MOTO_2026[cv_fiscaux]["de_3001_a_6000"]
        else:
            ik_rate_base = BAREME_IK_MOTO_2026[cv_fiscaux]["au_dela_6000"]

    # Majoration 20% vehicule electrique
    ik_rate_display = ik_rate_base
    if is_electrique:
        st.info(f"Bareme standard : {ik_rate_base:.3f} EUR/km | **Majoration electrique +20%**")
    else:
        st.info(f"Taux IK : **{ik_rate_display:.3f} EUR/km**")
    st.session_state.cfg_ik_rate = ik_rate_display

    # --- Calcul km via adresse ---
    with st.expander("Calculer les km par adresse", expanded=False):
        adresse_domicile = st.text_input("Adresse domicile", "", key="ik_domicile",
                                          placeholder="Ex: 12 rue de la Paix, 75002 Paris")
        adresse_mission = st.text_input("Adresse lieu de mission", "", key="ik_mission",
                                         placeholder="Ex: La Defense, 92400 Courbevoie")

        if st.button("Calculer le trajet", key="btn_calc_km"):
            if adresse_domicile and adresse_mission:
                with st.spinner("Recherche des adresses..."):
                    geo_dom = geocoder_adresse(adresse_domicile)
                    geo_mis = geocoder_adresse(adresse_mission)

                if geo_dom and geo_mis:
                    dom = geo_dom[0]
                    mis = geo_mis[0]
                    st.caption(f"Domicile : {dom['label']}")
                    st.caption(f"Mission : {mis['label']}")

                    with st.spinner("Calcul de l'itineraire..."):
                        route = calculer_distance_osrm(dom['lat'], dom['lon'], mis['lat'], mis['lon'])

                    if route:
                        km_aller = route['distance_km']
                        km_ar = round(km_aller * 2, 1)
                        st.success(f"**Trajet : {km_aller} km** (aller) | **{km_ar} km AR** | ~{route['duree_min']:.0f} min")
                        st.session_state['ik_km_calcule'] = km_ar
                    else:
                        st.error("Impossible de calculer l'itineraire. Verifiez les adresses.")
                else:
                    if not geo_dom:
                        st.error("Adresse domicile non trouvee")
                    if not geo_mis:
                        st.error("Adresse mission non trouvee")
            else:
                st.warning("Saisissez les deux adresses")

        if 'ik_km_calcule' in st.session_state and st.session_state['ik_km_calcule'] > 0:
            st.info(f"Km AR calcule : **{st.session_state['ik_km_calcule']} km**")

    # Km mensuel (manuel ou pre-rempli par le calcul)
    default_km = st.session_state.get('ik_km_calcule', 0.0) * days_worked_month if 'ik_km_calcule' in st.session_state else 0.0
    km_mensuel = st.number_input("Nb Kilometres ce mois", value=0.0, step=10.0,
                                  help=f"Km AR/jour x jours = km mensuels" if default_km > 0 else "")
    if default_km > 0 and km_mensuel == 0:
        st.caption(f"Suggestion : {st.session_state['ik_km_calcule']} km/jour x {days_worked_month} jours = **{default_km:.0f} km**")

    if is_electrique:
        ik_total = km_mensuel * ik_rate_base * 1.20
        st.caption(f"Total IK : {km_mensuel:.0f} x {ik_rate_base:.3f} x 1.20 = **{ik_total:,.2f} EUR**")
    else:
        ik_total = km_mensuel * ik_rate_display
        st.caption(f"Total IK : **{ik_total:,.2f} EUR**")

    st.markdown("---")
    st.subheader("Indemnites Grand Deplacement (IGD)")

    duree_mission = st.selectbox("Duree de la mission",
                                 ["Moins de 3 mois", "De 3 a 24 mois", "Au-dela de 24 mois"])
    if duree_mission == "Moins de 3 mois":
        igd_bareme = IGD_BAREME_2026["moins_3_mois"]
    elif duree_mission == "De 3 a 24 mois":
        igd_bareme = IGD_BAREME_2026["3_a_24_mois"]
    else:
        igd_bareme = IGD_BAREME_2026["24_a_72_mois"]

    zone_igd = st.selectbox("Zone IGD", ["Province", "Paris/IDF"])
    nb_repas_igd = st.number_input("Nb repas IGD", value=0, step=1, min_value=0)
    nb_nuitees_igd = st.number_input("Nb nuitees IGD", value=0, step=1, min_value=0)

    igd_repas_rate = igd_bareme["repas"]
    igd_nuitee_rate = igd_bareme["nuitee_paris"] if zone_igd == "Paris/IDF" else igd_bareme["nuitee_province"]
    igd_total = (nb_repas_igd * igd_repas_rate) + (nb_nuitees_igd * igd_nuitee_rate)

    if nb_repas_igd > 0 or nb_nuitees_igd > 0:
        st.caption(f"Repas: {nb_repas_igd} x {igd_repas_rate:.2f} = {nb_repas_igd * igd_repas_rate:.2f} EUR")
        st.caption(f"Nuitees: {nb_nuitees_igd} x {igd_nuitee_rate:.2f} = {nb_nuitees_igd * igd_nuitee_rate:.2f} EUR")
        st.caption(f"**Total IGD : {igd_total:,.2f} EUR**")

    st.markdown("---")
    st.subheader("Invitation Dejeuner")
    nb_invitation_dejeuner = st.number_input("Nb invitations dejeuner", value=0, step=1, min_value=0,
                                              help="Repas pris en charge (pas de TR ce jour)")

    st.markdown("---")
    st.subheader("Titres Restaurant")
    mode_tr = st.radio("Mode TR", ["Automatique", "Manuel"], horizontal=True)
    if mode_tr == "Automatique":
        nb_tr_auto = max(0, int(days_worked_month - nb_repas_igd - nb_invitation_dejeuner - nb_demi_journees))
        st.info(f"TR auto = {days_worked_month:.0f}j - {nb_repas_igd} IGD - {nb_invitation_dejeuner} invit. - {nb_demi_journees} demi-j = **{nb_tr_auto}**")
        nb_titres_restaurant = nb_tr_auto
    else:
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
    montant_facture_tel = st.number_input("Facture Tel/Internet (EUR)", value=0.0, step=10.0,
                                           help=f"Prise en charge a {st.session_state.cfg_pct_tel_internet:.0f}% (config)")
    frais_internet = round(montant_facture_tel * (st.session_state.cfg_pct_tel_internet / 100.0), 2)
    if montant_facture_tel > 0:
        st.caption(f"Pris en charge : {st.session_state.cfg_pct_tel_internet:.0f}% de {montant_facture_tel:.2f} = **{frais_internet:.2f} EUR**")

    montant_abonnement_transport = st.number_input("Abonnement Transport (EUR)", value=0.0, step=10.0,
                                                     help=f"Prise en charge a {st.session_state.cfg_pct_transport:.0f}% (config)")
    frais_transport = round(montant_abonnement_transport * (st.session_state.cfg_pct_transport / 100.0), 2)
    if montant_abonnement_transport > 0:
        st.caption(f"Pris en charge : {st.session_state.cfg_pct_transport:.0f}% de {montant_abonnement_transport:.2f} = **{frais_transport:.2f} EUR**")

    frais_divers = st.number_input("Autres Frais (EUR)", value=0.0, step=10.0)
    expenses_other = frais_internet + frais_transport + frais_divers
    st.caption(f"Total Autres Frais : **{expenses_other:,.2f} EUR**")

    st.markdown("---")
    st.subheader("Frais Partages & Commission")
    frais_partages_pct = st.number_input("Frais partages (%)", value=0.0, step=0.5, min_value=0.0,
                                          help="Frais de gestion partages avec le client")
    commission_mode = st.radio("Commission apporteur", ["Aucune", "Pourcentage", "Montant fixe"], horizontal=True)
    _ca_preview = tjm * days_worked_month
    if commission_mode == "Pourcentage":
        commission_pct = st.number_input("Commission (%)", value=0.0, step=0.5, min_value=0.0)
        commission_apporteur = round(_ca_preview * commission_pct / 100.0, 2)
        if commission_pct > 0:
            st.caption(f"Commission : {commission_pct}% de {_ca_preview:,.0f} = **{commission_apporteur:,.2f} EUR**")
    elif commission_mode == "Montant fixe":
        commission_apporteur = st.number_input("Commission (EUR)", value=0.0, step=50.0, min_value=0.0)
    else:
        commission_apporteur = 0.0

    st.markdown("---")
    st.subheader("Options")

    label_reserve_opt = "Indemnite de precarite reintegree" if type_contrat == "CDD" else "Reserve Financiere reintegree"
    reserve_reintegree = st.checkbox(label_reserve_opt, value=False,
                                     help="Cochez pour reintegrer dans le brut. Decochez pour provisionner.")
    use_reserve = not reserve_reintegree

    provision_cp = st.checkbox("Provisions Conges Payes", value=False,
                                help="Si coche, les ICP sont retirees du brut et provisionnees.")
    use_mutuelle = st.checkbox("Mutuelle Sante", value=True)
    effectif_sup_50 = st.checkbox("Entreprise >= 50 salaries", value=False,
                                   help="FNAL 0.50% si >= 50 sal. / 0.10% si < 50 sal.")

    st.markdown("---")
    st.subheader("Commercial")
    membre_bu = st.selectbox("Membre BU", MEMBRES_BU)

# --- CALCUL AVANT AFFICHAGE ---
results = calculate_salary(tjm, days_worked_month, days_worked_week,
                           ik_total, igd_total, expenses_other, use_reserve, use_mutuelle,
                           nb_titres_restaurant, frais_intermediation_pct, jours_teletravail,
                           effectif_sup_50, frais_partages_pct, commission_apporteur,
                           type_contrat, provision_cp)

# Main : Onglets
tab_simu, tab_config, tab_comm = st.tabs(["Resultats Simulation", "Configuration Globale", "Email & Explications"])

with tab_simu:
    st.title("Simulateur de Portage Salarial 2026")

    # --- KPIs principaux ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Chiffre d'Affaires", f"{results['turnover']:,.2f} EUR")
    with kpi2:
        st.metric("Salaire Brut", f"{results['gross_salary']:,.2f} EUR")
    with kpi3:
        st.metric("Cout Global", f"{results['cout_global']:,.2f} EUR")
    with kpi4:
        st.metric("Net a payer avant impot", f"{results['net_payable']:,.2f} EUR")

    # --- Sous-metriques ---
    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
    with sm1:
        st.caption(f"Montant Disponible : **{results['montant_disponible']:,.2f}**")
    with sm2:
        st.caption(f"Charges Patronales : **{results['employer_charges']:,.2f}**")
    with sm3:
        st.caption(f"Charges Salariales : **{results['employee_charges']:,.2f}**")
    with sm4:
        if results['provision_reserve_financiere'] > 0:
            st.caption(f"Prov. {results['label_reserve']} : **{results['provision_reserve_financiere']:,.2f}**")
        else:
            st.caption(f"{results['label_reserve']} (dans brut) : **{results['reserve_brute']:,.2f}**")
    with sm5:
        if results['nb_titres_restaurant'] > 0:
            st.caption(f"Titres Restaurant : **{results['nb_titres_restaurant']}**")

    st.divider()

    col_main, col_viz = st.columns([2, 1])

    with col_main:
        st.subheader("Detail du Bulletin")

        # --- Construction du bulletin restructure (V4) ---
        data_lines = []

        # Decomposition du brut
        data_lines.append(("Salaire de base", results['base_salary'], "Detail"))
        data_lines.append(("Prime d'apport d'affaires", results['prime_apport'], "Detail"))

        # Reserve dans le brut si reintegree
        if results['reserve_reintegree']:
            data_lines.append((results['label_reserve'].capitalize(), results['reserve_brute'], "Detail"))

        data_lines.append(("Complement de remuneration", results['complement_remuneration'], "Detail"))
        data_lines.append(("Complement d'apport d'affaires", results['complement_apport_affaires'], "Detail"))

        if results['provision_cp']:
            data_lines.append(("Indemnite conges payes (provisionnee)", results['indemnite_cp'], "Detail"))
        else:
            data_lines.append(("Indemnite conges payes", results['indemnite_cp'], "Detail"))

        data_lines.append(("SALAIRE BRUT", results['gross_salary'], "Total"))
        data_lines.append(("", 0, "Empty"))

        # Charges (totaux uniquement)
        data_lines.append(("Charges Salariales", -results['employee_charges'], "Negatif"))
        data_lines.append(("Charges Patronales", results['employer_charges'], "Detail"))
        data_lines.append(("", 0, "Empty"))

        # Frais
        has_frais = results['total_frais_rembourses'] > 0
        if has_frais:
            if results['ik_amount'] > 0:
                data_lines.append(("Indemnites Kilometriques", results['ik_amount'], "Detail"))
            if results['igd_amount'] > 0:
                data_lines.append(("Indemnites Grands Deplacements", results['igd_amount'], "Detail"))
            if results.get('forfait_teletravail', 0) > 0:
                data_lines.append((f"Forfait Teletravail ({results['jours_teletravail']}j x 2.70)", results['forfait_teletravail'], "Detail"))
            if results['other_expenses'] > 0:
                data_lines.append(("Autres Frais", results['other_expenses'], "Detail"))
            data_lines.append(("", 0, "Empty"))

        # Provision CP si activee
        if results['provision_cp'] and results['provision_cp_amount'] > 0:
            data_lines.append(("Provision Conges Payes", results['provision_cp_amount'], "Detail"))

        # Provision reserve si provisionnee
        if not results['reserve_reintegree'] and results['provision_reserve_financiere'] > 0:
            label_prov = f"Provision {results['label_reserve']}"
            data_lines.append((label_prov, results['provision_reserve_financiere'], "Detail"))

        data_lines.append(("", 0, "Empty"))
        data_lines.append(("Net a payer avant impot", results['net_payable'], "Final"))

        df_disp = pd.DataFrame(data_lines, columns=["Libelle", "Montant", "Type"])

        st.dataframe(
            df_disp[df_disp["Type"] != "Empty"][["Libelle", "Montant"]]
            .style.format({"Montant": "{:,.2f} EUR"}),
            use_container_width=True,
            hide_index=True,
            height=500
        )

        # --- Expander : Detail Cotisations Patronales ---
        with st.expander("Detail Cotisations Patronales (ligne par ligne)"):
            effectif_label = "< 50 salaries" if not results.get('effectif_sup_50', False) else ">= 50 salaries"
            fnal_rate_txt = "0.10%" if not results.get('effectif_sup_50', False) else "0.50%"

            taux_source = "configure" if st.session_state.cfg_taux_charges_override > 0 else "calcule"
            st.info(f"**Effectif : {effectif_label}** | FNAL {fnal_rate_txt} | AT/MP {st.session_state.cfg_taux_atmp:.2f}% | Taux de charges patronales : {results['taux_charges']*100:.2f}% ({taux_source})")

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

**NET A PAYER AVANT IMPOT**
```
= NET AVANT IMPOT + FRAIS REMBOURSES
= {results['net_before_tax']:,.2f} + {results['total_frais_rembourses']:,.2f}
= {results['net_payable']:,.2f} EUR
```

**COUT GLOBAL**
```
= BRUT + CHARGES PATRONALES + TOTAL FRAIS
= {results['gross_salary']:,.2f} + {results['employer_charges']:,.2f} + {results['total_frais_rembourses']:,.2f}
= {results['cout_global']:,.2f} EUR
```
            """)
            if not results['reserve_reintegree'] and results['provision_reserve_financiere'] > 0:
                charges_futures = results['provision_reserve_financiere'] - results['reserve_amount']
                st.markdown(f"""
**PROVISION {results['label_reserve'].upper()}**
```
= MONTANT DISPO - (BRUT + CHARGES PAT)
= {results['budget_salaire']:,.2f} - ({results['gross_salary']:,.2f} + {results['employer_charges']:,.2f})
= {results['provision_reserve_financiere']:,.2f} EUR
```
*(dont {results['label_reserve']} brute {results['reserve_amount']:,.2f} EUR + charges futures {charges_futures:,.2f} EUR)*
                """)

    with col_viz:
        st.subheader("Repartition")

        # Taux reel CA -> Net
        taux_ca_net = (results['net_payable'] / results['turnover'] * 100) if results['turnover'] > 0 else 0
        st.info(f"**Taux CA → Net : {taux_ca_net:.1f}%**")

        # Calcul des parts pour le camembert
        frais_gestion_total = results['management_fees'] + results['frais_intermediation'] + results.get('frais_partages', 0) + results.get('commission_apporteur', 0)
        cotis_sociales = (results['cotis_total_pat'] + results['cotis_total_sal']
                          + results['forfait_social'] - results['reduction_rgdu']
                          + results['mutuelle_part_pat'] + results['mutuelle_part_sal']
                          + results['tr_part_pat'] + results['tr_part_sal'])
        provision_viz = results['provision_reserve_financiere'] if not results['reserve_reintegree'] else 0

        labels = ['Net a payer', 'Frais de gestion', 'Cotisations Sociales & Patronales', 'Provision Reserve']
        values = [results['net_payable'], frais_gestion_total, cotis_sociales, provision_viz]
        colors = ['#E91E63', '#757575', '#F48FB1', '#F8BBD0']

        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='outside'
        )])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Export")
        pdf_bytes = create_pdf(results, consultant_name, membre_bu)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = (
            f'<a href="data:application/octet-stream;base64,{b64}" download="simulation_{consultant_name}.pdf" style="text-decoration:none;">'
            f'<button style="width:100%; padding: 10px; background-color: #E91E63; color: white; border: none; border-radius: 5px; cursor: pointer;">'
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
            "TAUX DE CHARGES PATRONALES Silae (%)", min_value=0.0,
            value=st.session_state.cfg_taux_charges_override, format="%.4f", step=0.0001,
            help="0 = auto-calcul. Saisir le taux Silae (patronal) pour matcher le complement de remuneration exactement."
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

        st.divider()
        st.subheader("% Prise en charge")
        st.session_state.cfg_pct_tel_internet = st.number_input(
            "% Abonnement Tel/Internet",
            value=st.session_state.cfg_pct_tel_internet, step=5.0, min_value=0.0, max_value=100.0,
            help="Pourcentage de la facture pris en charge"
        )
        st.session_state.cfg_pct_transport = st.number_input(
            "% Abonnement Transport",
            value=st.session_state.cfg_pct_transport, step=5.0, min_value=0.0, max_value=100.0,
            help="Pourcentage de l'abonnement pris en charge"
        )

        st.divider()
        st.markdown("**Taux IK** (defini automatiquement selon bareme URSSAF)")
        st.caption(f"Taux actuel : {st.session_state.cfg_ik_rate:.3f} EUR/km")

        st.divider()
        st.markdown("#### Baremes IGD URSSAF 2026")
        for duree, vals in IGD_BAREME_2026.items():
            label = duree.replace("_", " ").capitalize()
            st.caption(f"**{label}** : Repas {vals['repas']:.2f} | Province {vals['nuitee_province']:.2f} | Paris {vals['nuitee_paris']:.2f}")

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
        if not results['reserve_reintegree'] and results.get('provision_reserve_financiere', 0) > 0:
            txt_brut += f"\n\n*Provision {results['label_reserve']} : {results['provision_reserve_financiere']:,.2f} EUR (reserve + charges futures, hors brut)*"
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
        st.markdown("### 6. Le Cout Global")
        st.markdown(f"""
**COUT GLOBAL = BRUT + CHARGES PATRONALES + TOTAL FRAIS**

= {results['gross_salary']:,.2f} + {results['employer_charges']:,.2f} + {results['total_frais_rembourses']:,.2f} = **{results['cout_global']:,.2f} EUR**
        """)

        # Section 7 - Reserve
        if not results['reserve_reintegree'] and results.get('provision_reserve_financiere', 0) > 0:
            label_res = results['label_reserve']
            charges_futures = results['provision_reserve_financiere'] - results['reserve_amount']
            st.markdown(f"### 7. La Provision {label_res.capitalize()}")
            st.markdown(f"""
**PROVISION {label_res.upper()} = MONTANT DISPO - (BRUT + CHARGES PAT)**

= {results['budget_salaire']:,.2f} - ({results['gross_salary']:,.2f} + {results['employer_charges']:,.2f})
= **{results['provision_reserve_financiere']:,.2f} EUR**

*Dont {label_res} brute : {results['reserve_amount']:,.2f} EUR (base x {st.session_state.cfg_taux_reserve}%)*
*Dont charges futures sur {label_res} : {charges_futures:,.2f} EUR*

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

        # Texte temps de travail
        txt_temps = "Mission temps plein" if days_worked_week >= 5 else f"Mission temps partiel ({days_worked_week}j/sem)"

        # Frais de gestion + partages
        txt_gestion = f"Nos frais de gestion de {st.session_state.cfg_frais_gestion}%"
        if frais_partages_pct > 0:
            txt_gestion += f" + frais partages de {frais_partages_pct}%"

        # CP
        txt_cp = "Versement de l'indemnite conges payes tous les mois"
        if provision_cp:
            txt_cp = "Provisionnement de l'indemnite conges payes"

        # TR
        txt_tr_mail = ""
        if results['nb_titres_restaurant'] > 0:
            txt_tr_mail = f"\n- Avec les Tickets restaurants ({results['nb_titres_restaurant']} titres)"

        # Frais
        txt_frais_mail = ""
        if results['total_frais_rembourses'] > 0:
            details = []
            if results['ik_amount'] > 0:
                details.append(f"IK : {results['ik_amount']:,.2f} EUR")
            if results['igd_amount'] > 0:
                details.append(f"IGD : {results['igd_amount']:,.2f} EUR")
            if results.get('forfait_teletravail', 0) > 0:
                details.append(f"Teletravail : {results['forfait_teletravail']:,.2f} EUR")
            if results['other_expenses'] > 0:
                details.append(f"Autres : {results['other_expenses']:,.2f} EUR")
            txt_frais_mail = f"\n- J'ai integre {results['total_frais_rembourses']:,.2f} EUR de frais mensuels ({', '.join(details)})"

        # Reserve
        txt_reserve_mail = ""
        label_res = results['label_reserve']
        if not results['reserve_reintegree'] and results['reserve_brute'] > 0:
            txt_reserve_mail = f"\n\nA noter que la {label_res}* de {results['reserve_brute']:,.2f} EUR brut, sera provisionnee tous les mois.\n\n(*) {label_res.capitalize()} : equivalente a 10% du salaire de base mensuel, ce montant mis en reserve chaque mois est une obligation legale conventionnelle prevue pour vous permettre lors de vos intermissions de faire face a vos eventuels frais de prospection voire a financer votre indemnite de rupture conventionnelle. Dans tous les cas, cette reserve vous appartient : son solde vous est communiquee par Compte d'Activite etabli par nos soins, et vous est reverse en fin de contrat de travail (solde de tout compte)."

        # Mutuelle
        txt_mutuelle_mail = ""
        if use_mutuelle:
            txt_mutuelle_mail = "\nVous trouverez egalement en piece jointe le dossier relatif a la mutuelle proposee, prise en charge a 50% dans la simulation presentee."

        email_content = f"""Objet : Votre simulation de revenus avec Signe+ portage salarial

Bonjour {consultant_name},

Je vous remercie pour la qualite de nos echanges et pour le temps que vous m'avez accorde.

Comme convenu, vous trouverez ci-dessous la simulation de revenus etablie sur la base des elements que nous avons valides ensemble :

- {txt_temps}, soit une moyenne de {days_worked_month} jours produits/factures/mois
- Votre TJM de {tjm} EUR HT
- {txt_gestion}
- {txt_cp}{txt_tr_mail}{txt_frais_mail}

Votre salaire net avant impot s'eleve a : {results['net_payable']:,.2f} EUR

Detail du calcul :
- Salaire de base : {results['base_salary']:,.2f} EUR
- Prime d'apport d'affaires : {results['prime_apport']:,.2f} EUR
- Complement de remuneration : {results['complement_remuneration']:,.2f} EUR
- Complement apport d'affaires : {results['complement_apport_affaires']:,.2f} EUR
- Indemnite conges payes : {results['indemnite_cp']:,.2f} EUR
= Salaire brut total : {results['gross_salary']:,.2f} EUR

- Charges salariales : {results['employee_charges']:,.2f} EUR
- Charges patronales : {results['employer_charges']:,.2f} EUR
= Net avant impot : {results['net_before_tax']:,.2f} EUR
{txt_reserve_mail}{txt_mutuelle_mail}

Je reste naturellement a votre disposition pour affiner certains parametres ou repondre a toute question complementaire.

Au plaisir de poursuivre nos echanges,

Bien cordialement,

{membre_bu}"""

        st.text_area("Sujet & Corps du message", email_content, height=600)
