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
if 'cfg_taux_pat' not in st.session_state:
    st.session_state.cfg_taux_pat = 46.69
if 'cfg_taux_sal' not in st.session_state:
    st.session_state.cfg_taux_sal = 23.56
if 'cfg_ik_rate' not in st.session_state:
    st.session_state.cfg_ik_rate = 0.636  # Par defaut 5CV, tranche 1
if 'cfg_pmss' not in st.session_state:
    st.session_state.cfg_pmss = 4005.0 # Valeur 2026
if 'cfg_mutuelle_taux' not in st.session_state:
    st.session_state.cfg_mutuelle_taux = 1.5
if 'cfg_mutuelle_part_pat' not in st.session_state:
    st.session_state.cfg_mutuelle_part_pat = 50.0
if 'cfg_smic_mensuel' not in st.session_state:
    st.session_state.cfg_smic_mensuel = 1823.03 # Valeur 2026
if 'cfg_taux_pat_reduit' not in st.session_state:
    st.session_state.cfg_taux_pat_reduit = 41.00
if 'cfg_seuil_reduit_smic' not in st.session_state:
    st.session_state.cfg_seuil_reduit_smic = 2.5
if 'cfg_seuil_maladie_smic' not in st.session_state:
    st.session_state.cfg_seuil_maladie_smic = 2.25
if 'cfg_seuil_af_smic' not in st.session_state:
    st.session_state.cfg_seuil_af_smic = 3.3 

# --- Moteur de Calcul ---
def calculate_salary(tjm, days_worked_month, days_worked_week,
                     ik_amount, igd_amount, other_expenses, use_reserve, use_mutuelle,
                     nb_titres_restaurant=0, frais_intermediation_pct=0.0):

    cfg_base = st.session_state.cfg_base_salary
    rate_gestion = st.session_state.cfg_frais_gestion / 100.0
    rate_prime = st.session_state.cfg_taux_prime / 100.0
    rate_reserve = st.session_state.cfg_taux_reserve / 100.0
    rate_cp = st.session_state.cfg_taux_cp / 100.0

    base_rate_pat = st.session_state.cfg_taux_pat / 100.0
    reduced_rate_pat = st.session_state.cfg_taux_pat_reduit / 100.0
    rate_sal = st.session_state.cfg_taux_sal / 100.0

    smic = st.session_state.cfg_smic_mensuel
    threshold_reduced = st.session_state.cfg_seuil_reduit_smic * smic
    threshold_maladie = st.session_state.cfg_seuil_maladie_smic * smic  # Seuil complement maladie 2.25 SMIC
    threshold_af = st.session_state.cfg_seuil_af_smic * smic  # Seuil allocations familiales 3.3 SMIC

    pmss = st.session_state.cfg_pmss
    mutuelle_total_cost = 0.0
    mutuelle_part_pat = 0.0
    mutuelle_part_sal = 0.0

    if use_mutuelle:
        mutuelle_rate = st.session_state.cfg_mutuelle_taux / 100.0
        split_pat = st.session_state.cfg_mutuelle_part_pat / 100.0
        mutuelle_total_cost = pmss * mutuelle_rate
        mutuelle_part_pat = mutuelle_total_cost * split_pat
        mutuelle_part_sal = mutuelle_total_cost * (1 - split_pat)

    # Titres Restaurant
    tr_part_sal = nb_titres_restaurant * TR_PART_PATRONALE_MAX  # 7.18 EUR
    tr_part_pat = nb_titres_restaurant * TR_PART_PATRONALE_MAX  # 7.18 EUR

    turnover = tjm * days_worked_month
    management_fees = turnover * rate_gestion
    frais_intermediation = turnover * (frais_intermediation_pct / 100.0)

    # Montant disponible (apres frais de gestion et intermediation)
    montant_disponible = turnover - management_fees - frais_intermediation

    # Total des frais rembourses
    total_frais_rembourses = ik_amount + igd_amount + other_expenses

    # Budget masse salariale
    masse_salariale_budget = montant_disponible - total_frais_rembourses

    base_salary = cfg_base * (days_worked_week / 5.0)
    prime_apport = base_salary * rate_prime
    reserve_amount = (base_salary * rate_reserve) if use_reserve else 0.0

    # Cout mutuelle et TR a integrer
    target_total_cost = masse_salariale_budget - reserve_amount - mutuelle_part_pat - tr_part_pat

    def solve_gross(cost, pat_rate):
        return cost / (1 + pat_rate)

    rate_scenario = "Standard"
    final_rate_pat = base_rate_pat

    gross_candidate = solve_gross(target_total_cost, reduced_rate_pat)

    if gross_candidate <= threshold_reduced:
        final_rate_pat = reduced_rate_pat
        rate_scenario = "Réduit"
    else:
        gross_candidate = solve_gross(target_total_cost, base_rate_pat)
        final_rate_pat = base_rate_pat
        rate_scenario = "Standard"

    # Calcul du complement de remuneration avec separation 5%
    base_prime_complement = gross_candidate / (1 + rate_cp)
    complement_total = base_prime_complement - base_salary - prime_apport

    if complement_total < 0:
        complement_total = 0

    # Separation complement remuneration / complement apport affaires (regle 1/1.05)
    complement_remuneration = complement_total / 1.05
    complement_apport_affaires = complement_total - complement_remuneration

    indemnite_cp = (base_salary + prime_apport + complement_remuneration + complement_apport_affaires) * rate_cp
    gross_salary = base_salary + prime_apport + complement_remuneration + complement_apport_affaires + indemnite_cp

    # Calcul charges patronales de base (cotisations sociales)
    base_employer_charges = gross_salary * final_rate_pat

    # Cotisation paritarisme (0.016% du brut)
    cotisation_paritarisme = gross_salary * 0.00016

    # Total charges patronales = cotisations sociales + mutuelle pat + TR pat + paritarisme
    employer_charges = base_employer_charges + mutuelle_part_pat + tr_part_pat + cotisation_paritarisme

    # Charges salariales (incluant retenue TR)
    employee_charges_base = gross_salary * rate_sal
    employee_charges = employee_charges_base + tr_part_sal

    # Cout global sans reserve
    cout_global_sans_reserve = gross_salary + employer_charges + mutuelle_part_pat + tr_part_pat + total_frais_rembourses

    net_before_tax = gross_salary - employee_charges_base - mutuelle_part_sal
    net_payable = net_before_tax + total_frais_rembourses - tr_part_sal

    return {
        "turnover": turnover,
        "management_fees": management_fees,
        "frais_intermediation": frais_intermediation,
        "montant_disponible": montant_disponible,
        "ik_amount": ik_amount,
        "igd_amount": igd_amount,
        "other_expenses": other_expenses,
        "total_frais_rembourses": total_frais_rembourses,
        "masse_salariale_budget": masse_salariale_budget,
        "base_salary": base_salary,
        "prime_apport": prime_apport,
        "complement_remuneration": complement_remuneration,
        "complement_apport_affaires": complement_apport_affaires,
        "indemnite_cp": indemnite_cp,
        "gross_salary": gross_salary,
        "reserve_amount": reserve_amount,
        "employer_charges": employer_charges,
        "base_employer_charges": base_employer_charges,
        "cotisation_paritarisme": cotisation_paritarisme,
        "employee_charges": employee_charges,
        "employee_charges_base": employee_charges_base,
        "mutuelle_part_pat": mutuelle_part_pat,
        "mutuelle_part_sal": mutuelle_part_sal,
        "tr_part_sal": tr_part_sal,
        "tr_part_pat": tr_part_pat,
        "nb_titres_restaurant": nb_titres_restaurant,
        "cout_global_sans_reserve": cout_global_sans_reserve,
        "net_before_tax": net_before_tax,
        "net_payable": net_payable,
        "rate_scenario": rate_scenario,
        "rate_pat_applied": final_rate_pat,
        "threshold_maladie": threshold_maladie,
        "threshold_af": threshold_af
    }

# --- PDF Generation ---
def create_pdf(data, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"Simulation de Salaire - {name}", ln=1, align="C")
    pdf.ln(10)

    t_gest = st.session_state.cfg_frais_gestion
    t_ik = st.session_state.cfg_ik_rate

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

    pdf.set_font("Arial", size=11)
    pdf.cell(140, 8, txt="Reserve Financiere Provisionnee", border=0)
    pdf.cell(50, 8, txt=f"{data['reserve_amount']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.cell(140, 8, txt="Mutuelle Part Patronale", border=0)
    pdf.cell(50, 8, txt=f"{data['mutuelle_part_pat']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('tr_part_pat', 0) > 0:
        pdf.cell(140, 8, txt="Titres Restaurant Part Patronale", border=0)
        pdf.cell(50, 8, txt=f"{data['tr_part_pat']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.cell(140, 8, txt="Charges Patronales", border=0)
    pdf.cell(50, 8, txt=f"{data['employer_charges']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= COUT GLOBAL SANS RESERVE", border='T')
    pdf.cell(50, 8, txt=f"{data['cout_global_sans_reserve']:,.2f} EUR", border='T', align='R', ln=1)

    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    pdf.cell(140, 8, txt="Charges Salariales", border=0)
    pdf.cell(50, 8, txt=f"- {data['employee_charges_base']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.cell(140, 8, txt="Mutuelle Part Salariale", border=0)
    pdf.cell(50, 8, txt=f"- {data['mutuelle_part_sal']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('tr_part_sal', 0) > 0:
        pdf.cell(140, 8, txt="Titres Restaurant Part Salariale", border=0)
        pdf.cell(50, 8, txt=f"- {data['tr_part_sal']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="= NET AVANT IMPOT", border='T')
    pdf.cell(50, 8, txt=f"{data['net_before_tax']:,.2f} EUR", border='T', align='R', ln=1)

    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    if data.get('ik_amount', 0) > 0:
        pdf.cell(140, 8, txt=f"Indemnites Kilometriques ({t_ik} EUR/km)", border=0)
        pdf.cell(50, 8, txt=f"+ {data['ik_amount']:,.2f} EUR", border=0, align='R', ln=1)

    if data.get('igd_amount', 0) > 0:
        pdf.cell(140, 8, txt="Indemnites Grand Deplacement", border=0)
        pdf.cell(50, 8, txt=f"+ {data['igd_amount']:,.2f} EUR", border=0, align='R', ln=1)

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
    st.subheader("Autres Frais")
    frais_teletravail = st.number_input("Forfait Teletravail (EUR)", value=0.0, step=10.0)
    frais_internet = st.number_input("Internet / Telephone (EUR)", value=0.0, step=10.0)
    frais_transport = st.number_input("Transports (Navigo...) (EUR)", value=0.0, step=10.0)
    frais_divers = st.number_input("Autres Frais (EUR)", value=0.0, step=10.0)

    expenses_other = frais_teletravail + frais_internet + frais_transport + frais_divers
    st.caption(f"Total Autres Frais : {expenses_other:,.2f} EUR")

    st.markdown("---")
    # Inverser la logique : coche = reserve reintegree (donc use_reserve = False pour provisionnement)
    reserve_reintegree = st.checkbox("Reserve Financiere reintegree", value=False,
                                     help="Cochez pour reintegrer la reserve (positif). Decochez pour provisionner (negatif).")
    use_reserve = not reserve_reintegree  # Si coche = reintegree, on ne provisionne pas

    use_mutuelle = st.checkbox("Mutuelle Sante", value=True)

# --- CALCUL AVANT AFFICHAGE ---
results = calculate_salary(tjm, days_worked_month, days_worked_week,
                           ik_total, igd_total, expenses_other, use_reserve, use_mutuelle,
                           nb_titres_restaurant, frais_intermediation_pct)

# Main : Onglets
tab_simu, tab_config, tab_comm = st.tabs(["📊 Résultats Simulation", "⚙️ Configuration Globale", "📧 Email & Explications"])

with tab_simu:
    st.title("Simulateur de Portage Salarial 2026")
    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Chiffre d'Affaires", f"{results['turnover']:,.2f} EUR")
    with kpi2:
        st.metric("Salaire Brut", f"{results['gross_salary']:,.2f} EUR")
    with kpi3:
        total_charges = results['employer_charges'] + results['employee_charges_base'] + results['mutuelle_part_pat'] + results['mutuelle_part_sal']
        st.metric("Charges Totales", f"{total_charges:,.2f} EUR")
    with kpi4:
        st.metric("NET A PAYER", f"{results['net_payable']:,.2f} EUR", delta="Virement")

    st.divider()

    col_main, col_viz = st.columns([2, 1])

    with col_main:
        st.subheader("Detail du Bulletin")

        txt_gest = f"Frais de gestion ({st.session_state.cfg_frais_gestion}%)"

        rate_pat_txt = f"{results['rate_pat_applied']*100:.2f}%"
        scenario = results.get('rate_scenario', 'Standard')

        if scenario == "Reduit":
            rate_pat_txt += " (Reduit - Bas salaire)"

        # Construction des lignes de detail charges patronales
        txt_pat_base = f"Charges Patronales base ({rate_pat_txt})"

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

        # Reserve financiere
        reserve_display = -results['reserve_amount'] if use_reserve else results['reserve_amount']
        reserve_label = "Reserve Financiere Provisionnee chargee" if use_reserve else "Reserve Financiere reintegree"
        data_lines.append((reserve_label, reserve_display, "Negatif" if use_reserve else "Positif"))

        data_lines.append(("Mutuelle Part Patronale", results['mutuelle_part_pat'], "Detail"))

        if results['tr_part_pat'] > 0:
            data_lines.append(("Titres Restaurant Part Patronale", results['tr_part_pat'], "Detail"))

        # Charges patronales avec detail
        data_lines.append((txt_pat_base, results['base_employer_charges'], "Detail"))
        data_lines.append((f"+ Cotisation Paritarisme (0.016%)", results['cotisation_paritarisme'], "Detail"))
        data_lines.append(("= Total Charges Patronales", results['employer_charges'], "Total"))
        data_lines.append(("", 0, "Empty"))

        data_lines.append(("= COUT GLOBAL SANS RESERVE", results['cout_global_sans_reserve'], "Total"))
        data_lines.append(("", 0, "Empty"))

        data_lines.append((f"Charges Salariales ({st.session_state.cfg_taux_sal}%)", -results['employee_charges_base'], "Negatif"))
        data_lines.append(("Mutuelle Part Salariale", -results['mutuelle_part_sal'], "Negatif"))

        if results['tr_part_sal'] > 0:
            data_lines.append(("Titres Restaurant Part Salariale", -results['tr_part_sal'], "Negatif"))

        data_lines.append(("= NET AVANT IMPOT", results['net_before_tax'], "Total"))
        data_lines.append(("", 0, "Empty"))

        # Frais rembourses
        if results['ik_amount'] > 0:
            data_lines.append((f"Indemnites Km ({st.session_state.cfg_ik_rate:.3f} EUR/km)", results['ik_amount'], "Positif"))

        if results['igd_amount'] > 0:
            data_lines.append(("Indemnites Grand Deplacement (IGD)", results['igd_amount'], "Positif"))

        if results['other_expenses'] > 0:
            data_lines.append(("Autres Frais", results['other_expenses'], "Positif"))

        if results['total_frais_rembourses'] > 0:
            data_lines.append(("= Total Frais Rembourses", results['total_frais_rembourses'], "Total"))

        data_lines.append(("", 0, "Empty"))
        data_lines.append(("= NET A PAYER", results['net_payable'], "Final"))

        df_disp = pd.DataFrame(data_lines, columns=["Libelle", "Montant", "Type"])

        st.dataframe(
            df_disp[df_disp["Type"] != "Empty"][["Libelle", "Montant"]]
            .style.format({"Montant": "{:,.2f} EUR"}),
            use_container_width=True,
            hide_index=True,
            height=700
        )

    with col_viz:
        st.subheader("Repartition")
        labels = ['Net Avant Impot', 'Charges Sociales', 'Mutuelle', 'Frais Gestion', 'Reserve']
        values = [results['net_before_tax'],
                  results['employee_charges_base'] + results['employer_charges'],
                  results['mutuelle_part_pat'] + results['mutuelle_part_sal'],
                  results['management_fees'] + results['frais_intermediation'],
                  results['reserve_amount']]

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
        st.subheader("Charges & Mutuelle")
        st.session_state.cfg_taux_pat = st.number_input(
            "Taux Charges Patronales (%)",
            value=st.session_state.cfg_taux_pat, format="%.2f", step=0.05
        )
        st.session_state.cfg_taux_sal = st.number_input(
            "Taux Charges Salariales (%)",
            value=st.session_state.cfg_taux_sal, format="%.2f", step=0.05
        )
        st.divider()
        st.markdown("#### Seuils & Bascule")
        st.session_state.cfg_smic_mensuel = st.number_input(
            "SMIC Mensuel Brut (EUR)",
            value=st.session_state.cfg_smic_mensuel, step=10.0
        )
        st.session_state.cfg_taux_pat_reduit = st.number_input(
            "Taux Patronal Reduit (%)",
            value=st.session_state.cfg_taux_pat_reduit, step=0.5
        )
        st.session_state.cfg_seuil_reduit_smic = st.number_input(
            "Seuil Taux Reduit (x SMIC)",
            value=st.session_state.cfg_seuil_reduit_smic, step=0.1
        )

        st.divider()
        st.markdown("#### Seuils Complements Patronaux")
        st.session_state.cfg_seuil_maladie_smic = st.number_input(
            "Seuil Complement Maladie (x SMIC)",
            value=st.session_state.cfg_seuil_maladie_smic, step=0.05,
            help="Au-dela de ce seuil, +6% de complement maladie"
        )
        st.session_state.cfg_seuil_af_smic = st.number_input(
            "Seuil Complement AF (x SMIC)",
            value=st.session_state.cfg_seuil_af_smic, step=0.1,
            help="Au-dela de ce seuil, +1.8% de complement allocations familiales"
        )

        limit_reduit = st.session_state.cfg_smic_mensuel * st.session_state.cfg_seuil_reduit_smic
        limit_maladie = st.session_state.cfg_smic_mensuel * st.session_state.cfg_seuil_maladie_smic
        limit_af = st.session_state.cfg_smic_mensuel * st.session_state.cfg_seuil_af_smic

        st.info(f"""
        **Paliers actuels :**
        < {limit_reduit:,.0f} EUR : Taux Reduit ({st.session_state.cfg_taux_pat_reduit}%)
        >= {limit_reduit:,.0f} EUR : Standard ({st.session_state.cfg_taux_pat}%)

        **Complements si brut depasse :**
        > {limit_maladie:,.0f} EUR : +6% Maladie
        > {limit_af:,.0f} EUR : +1.8% AF
        """)

        st.divider()
        st.session_state.cfg_pmss = st.number_input(
            "Plafond Secu (PMSS) (EUR)",
            value=st.session_state.cfg_pmss, step=100.0
        )
        st.session_state.cfg_mutuelle_taux = st.number_input(
            "Taux Mutuelle (% du PMSS)",
            value=st.session_state.cfg_mutuelle_taux, step=0.1
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
        st.session_state.cfg_mutuelle_part_pat = st.number_input(
            "Part Patronale Mutuelle (%)",
            value=st.session_state.cfg_mutuelle_part_pat, step=5.0
        )

        st.divider()
        st.markdown("#### Baremes IGD URSSAF 2026")
        st.caption(f"Repas : {IGD_REPAS:.2f} EUR")
        st.caption(f"Nuitee Province : {IGD_NUITEE_PROVINCE:.2f} EUR")
        st.caption(f"Nuitee Paris/IDF : {IGD_NUITEE_PARIS:.2f} EUR")

        st.divider()
        st.markdown("#### Titres Restaurant")
        st.caption(f"Valeur faciale : {TR_VALEUR_FACIALE:.2f} EUR")
        st.caption(f"Part patronale max : {TR_PART_PATRONALE_MAX:.2f} EUR")

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
        st.markdown(f"""
- Salaire de Base (fixe) : **{results['base_salary']:,.2f} EUR**
- Prime Apport d'Affaires (5% du base) : **{results['prime_apport']:,.2f} EUR**
- Complement de Remuneration (variable) : **{results['complement_remuneration']:,.2f} EUR**
- Complement Apport d'Affaires (5% du complement) : **{results['complement_apport_affaires']:,.2f} EUR**
- Indemnite Conges Payes (10%) : **{results['indemnite_cp']:,.2f} EUR**

= **Salaire Brut Total : {results['gross_salary']:,.2f} EUR**
        """)

        # Section 4 - Charges patronales
        st.markdown("### 4. Les Charges Patronales (detail)")
        scenario = results.get('rate_scenario', 'Standard')
        txt_charges_pat = f"- Cotisations sociales ({scenario} {results['rate_pat_applied']*100:.2f}%) : **{results['base_employer_charges']:,.2f} EUR**"
        txt_charges_pat += f"\n- + Mutuelle part patronale : **{results['mutuelle_part_pat']:,.2f} EUR**"
        if results['tr_part_pat'] > 0:
            txt_charges_pat += f"\n- + Titres Restaurant part patronale : **{results['tr_part_pat']:,.2f} EUR**"
        txt_charges_pat += f"\n- + Cotisation Paritarisme (0.016%) : **{results['cotisation_paritarisme']:,.2f} EUR**"
        txt_charges_pat += f"\n\n= **Total Charges Patronales : {results['employer_charges']:,.2f} EUR**"
        st.markdown(txt_charges_pat)

        # Section 5 - Reserve
        if use_reserve and results['reserve_amount'] > 0:
            st.markdown("### 5. La Reserve Financiere")
            st.markdown(f"""
Montant provisionne (epargne securite) : **{results['reserve_amount']:,.2f} EUR** (10% du salaire de base)

*Cet argent reste a vous ! Il sert a financer vos periodes d'intercontrat ou est verse en fin de contrat.*
            """)

        # Section 6 - Cout global
        st.markdown("### 6. Le Cout Global Sans Reserve")
        st.markdown(f"= Brut + Charges Patronales + Frais = **{results['cout_global_sans_reserve']:,.2f} EUR**")

        # Section 7 - Charges salariales
        st.markdown("### 7. Les Charges Salariales")
        txt_charges_sal = f"- Taux {st.session_state.cfg_taux_sal}% sur le brut : **{results['employee_charges_base']:,.2f} EUR**"
        if results['tr_part_sal'] > 0:
            txt_charges_sal += f"\n- Titres Restaurant (retenue part salariale) : **{results['tr_part_sal']:,.2f} EUR**"
        st.markdown(txt_charges_sal)

        # Section 8 - Frais rembourses
        if results['total_frais_rembourses'] > 0:
            st.markdown("### 8. Les Frais Rembourses (non imposables)")
            txt_frais = ""
            if results['ik_amount'] > 0:
                txt_frais += f"- IK selon bareme URSSAF ({st.session_state.cfg_ik_rate:.3f} EUR/km) : **{results['ik_amount']:,.2f} EUR**\n"
            if results['igd_amount'] > 0:
                txt_frais += f"- IGD (repas + nuitees) : **{results['igd_amount']:,.2f} EUR**\n"
            if results['other_expenses'] > 0:
                txt_frais += f"- Autres frais : **{results['other_expenses']:,.2f} EUR**\n"
            txt_frais += f"\n= **Total Frais Rembourses : {results['total_frais_rembourses']:,.2f} EUR**"
            st.markdown(txt_frais)

        # Section 9 - Net final
        st.markdown("### 9. Le Net Final")
        st.success(f"""
**Net Avant Impot** = Brut - Charges Salariales = **{results['net_before_tax']:,.2f} EUR**

**Net a Payer** = Net Avant Impot + Frais Rembourses = **{results['net_payable']:,.2f} EUR**
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

        # Optimisation charges
        txt_opti = ""
        if results.get('rate_scenario') == 'Reduit':
            txt_opti = "\n- Optimisation : Cette simulation integre les allegements de charges sociales en vigueur pour maximiser votre net."

        # Info charges patronales
        txt_complements = ""

        email_content = f"""Objet : Votre simulation de revenus - TJM {tjm} EUR

Bonjour {consultant_name},

Suite a nos echanges, j'ai le plaisir de vous transmettre votre simulation de salaire personnalisee, basee sur un TJM de {tjm} EUR et {days_worked_month} jours d'activite.
{txt_intermediation}
Voici la synthese de votre projection pour ce mois :

VOTRE NET A PAYER ESTIME : {results['net_payable']:,.2f} EUR
(Montant vire sur votre compte bancaire)

Ce montant comprend :
*   Votre Salaire Net (apres deduction de toutes les charges sociales).{txt_frais}

Les points cles de cette simulation :{txt_mutuelle}{txt_reserve_mail}{txt_tr}{txt_opti}
- Securite : Cotisations completes (Chomage, Retraite Cadre, Securite Sociale).
- Transparence : Tout est detaille dans le PDF ci-joint (Baremes 2026).
{txt_complements}

Detail du calcul :
- Salaire Brut : {results['gross_salary']:,.2f} EUR
- Charges Salariales : {results['employee_charges_base']:,.2f} EUR
- Charges Patronales : {results['employer_charges']:,.2f} EUR
- Net Avant Impot : {results['net_before_tax']:,.2f} EUR

Je reste a votre disposition pour affiner ces chiffres ou pour preparer votre contrat.

Bien cordialement,

L'equipe Portage"""

        st.text_area("Sujet & Corps du message", email_content, height=550)
