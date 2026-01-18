import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF
import base64

# --- Initialisation des Variables (Session State) ---
# On définit les valeurs par défaut seulement si elles n'existent pas encore
if 'cfg_base_salary' not in st.session_state:
    st.session_state.cfg_base_salary = 2374.0
if 'cfg_frais_gestion' not in st.session_state:
    st.session_state.cfg_frais_gestion = 5.0 # En %
if 'cfg_taux_prime' not in st.session_state:
    st.session_state.cfg_taux_prime = 5.0 # En %
if 'cfg_taux_reserve' not in st.session_state:
    st.session_state.cfg_taux_reserve = 10.0 # En %
if 'cfg_taux_cp' not in st.session_state:
    st.session_state.cfg_taux_cp = 10.0 # En %
if 'cfg_taux_pat' not in st.session_state:
    st.session_state.cfg_taux_pat = 46.69 # En %
if 'cfg_taux_sal' not in st.session_state:
    st.session_state.cfg_taux_sal = 23.56 # En %
if 'cfg_ik_rate' not in st.session_state:
    st.session_state.cfg_ik_rate = 1.25 # €/km
if 'cfg_pmss' not in st.session_state:
    st.session_state.cfg_pmss = 3925.0 # PMSS 2025
if 'cfg_mutuelle_taux' not in st.session_state:
    st.session_state.cfg_mutuelle_taux = 1.5 # % du PMSS
if 'cfg_mutuelle_part_pat' not in st.session_state:
    st.session_state.cfg_mutuelle_part_pat = 50.0 # % Prise en charge patronale

# --- Moteur de Calcul ---

def calculate_salary(tjm, days_worked_month, days_worked_week, 
                     ik_amount, other_expenses, use_reserve, use_mutuelle):
    
    # Récupération des variables de configuration depuis le state
    cfg_base = st.session_state.cfg_base_salary
    rate_gestion = st.session_state.cfg_frais_gestion / 100.0
    rate_prime = st.session_state.cfg_taux_prime / 100.0
    rate_reserve = st.session_state.cfg_taux_reserve / 100.0
    rate_cp = st.session_state.cfg_taux_cp / 100.0
    rate_pat = st.session_state.cfg_taux_pat / 100.0
    rate_sal = st.session_state.cfg_taux_sal / 100.0
    
    # Mutuelle
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
    
    # 1. Chiffre d'Affaires & Frais de Gestion
    turnover = tjm * days_worked_month
    management_fees = turnover * rate_gestion
    
    # 2. Enveloppe Globale Disponible
    budget_available = turnover - management_fees
    masse_salariale_budget = budget_available - ik_amount - other_expenses
    
    # 3. Calcul des Éléments Fixes
    # Proratisation temps partiel hebdo (Base 5 jours)
    base_salary = cfg_base * (days_worked_week / 5.0)
    
    prime_apport = base_salary * rate_prime
    
    # Réserve financière
    reserve_amount = (base_salary * rate_reserve) if use_reserve else 0.0
    
    # 4. Résolution du Complément
    # Masse_Dispo - Reserve - Mutuelle_Patronale = Brut_Total * (1 + Pat)
    # Brut_Total = (Base + Prime + Complément) * (1 + Taux_CP)
    
    # On déduit le coût fixe patronal de la mutuelle de l'enveloppe
    target_total_cost = masse_salariale_budget - reserve_amount - mutuelle_part_pat
    
    target_gross_salary = target_total_cost / (1 + rate_pat)
    
    # Base hors CP
    base_prime_complement = target_gross_salary / (1 + rate_cp)
    
    complement_remuneration = base_prime_complement - base_salary - prime_apport
    
    if complement_remuneration < 0:
        complement_remuneration = 0
    
    # 5. Reconstruction
    indemnite_cp = (base_salary + prime_apport + complement_remuneration) * rate_cp
    gross_salary = base_salary + prime_apport + complement_remuneration + indemnite_cp
    
    employer_charges = gross_salary * rate_pat
    employee_charges = gross_salary * rate_sal
    
    # Net avant impôt = Brut - Charges Salariales - Mutuelle Salariale
    net_before_tax = gross_salary - employee_charges - mutuelle_part_sal
    
    net_payable = net_before_tax + ik_amount + other_expenses
    
    return {
        "turnover": turnover,
        "management_fees": management_fees,
        "ik_amount": ik_amount,
        "other_expenses": other_expenses,
        "total_expenses": ik_amount + other_expenses,
        "budget_available": budget_available,
        "masse_salariale_budget": masse_salariale_budget,
        "base_salary": base_salary,
        "prime_apport": prime_apport,
        "complement_remuneration": complement_remuneration,
        "indemnite_cp": indemnite_cp,
        "gross_salary": gross_salary,
        "reserve_amount": reserve_amount,
        "employer_charges": employer_charges,
        "employee_charges": employee_charges,
        "mutuelle_part_pat": mutuelle_part_pat,
        "mutuelle_part_sal": mutuelle_part_sal,
        "net_before_tax": net_before_tax,
        "net_payable": net_payable
    }

# --- PDF Generation ---
def create_pdf(data, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Simulation de Salaire - {name}", ln=1, align="C")
    pdf.ln(10)
    
    # On récupère les taux pour l'affichage
    t_gest = st.session_state.cfg_frais_gestion
    t_ik = st.session_state.cfg_ik_rate
    
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Activité & Frais", ln=1)
    pdf.set_font("Arial", size=11)
    pdf.cell(140, 8, txt="Chiffre d'affaires (CA)", border=0)
    pdf.cell(50, 8, txt=f"{data['turnover']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt=f"Frais de gestion ({t_gest}%)", border=0)
    pdf.cell(50, 8, txt=f"- {data['management_fees']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt=f"Indemnités Kilométriques (Base {t_ik} EUR/km)", border=0)
    pdf.cell(50, 8, txt=f"- {data['ik_amount']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Autres Frais", border=0)
    pdf.cell(50, 8, txt=f"- {data['other_expenses']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(200, 10, txt="Décomposition du Salaire Brut", ln=1)
    pdf.set_font("Arial", size=11)
    
    pdf.cell(140, 8, txt="Salaire de Base", border=0)
    pdf.cell(50, 8, txt=f"{data['base_salary']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Prime d'apport d'affaires", border=0)
    pdf.cell(50, 8, txt=f"{data['prime_apport']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Complément de rémunération", border=0)
    pdf.cell(50, 8, txt=f"{data['complement_remuneration']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Indemnité Congés Payés", border=0)
    pdf.cell(50, 8, txt=f"{data['indemnite_cp']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.set_font("Arial", 'B', size=11)
    pdf.cell(140, 8, txt="TOTAL BRUT", border='T')
    pdf.cell(50, 8, txt=f"{data['gross_salary']:,.2f} EUR", border='T', align='R', ln=1)
    
    pdf.ln(5)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(140, 8, txt="Réserve Financière (déduite)", border=0)
    pdf.cell(50, 8, txt=f"{data['reserve_amount']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Mutuelle Part Patronale", border=0)
    pdf.cell(50, 8, txt=f"{data['mutuelle_part_pat']:,.2f} EUR", border=0, align='R', ln=1)

    pdf.cell(140, 8, txt="Charges Patronales", border=0)
    pdf.cell(50, 8, txt=f"{data['employer_charges']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Charges Salariales", border=0)
    pdf.cell(50, 8, txt=f"- {data['employee_charges']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.cell(140, 8, txt="Mutuelle Part Salariale", border=0)
    pdf.cell(50, 8, txt=f"- {data['mutuelle_part_sal']:,.2f} EUR", border=0, align='R', ln=1)
    
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', size=14)
    pdf.cell(140, 10, txt="NET À PAYER", border='TB')
    pdf.cell(50, 10, txt=f"{data['net_payable']:,.2f} EUR", border='TB', align='R', ln=1)
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI Streamlit ---

st.set_page_config(page_title="Simulateur Portage Salarial 2025", layout="wide")

# Sidebar : Entrées spécifiques à la simulation (Consultant)
with st.sidebar:
    st.title("👤 Consultant")
    consultant_name = st.text_input("Nom", "Consultant")
    tjm = st.number_input("TJM (€)", min_value=0, value=500, step=10)
    
    st.markdown("---")
    st.subheader("Temps de Travail")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        days_worked_month = st.number_input("Jours / Mois", value=19.0, step=0.5)
    with col_d2:
        days_worked_week = st.number_input("Jours / Sem", value=5.0, max_value=7.0, step=0.5)
        
    st.markdown("---")
    st.subheader("Frais")
    
    # On utilise le taux configuré pour afficher l'info
    ik_rate_display = st.session_state.cfg_ik_rate
    st.markdown(f"**Indemnités Km** ({ik_rate_display} €/km)")
    km_mensuel = st.number_input("Nb Kilomètres", value=0.0, step=10.0)
    ik_total = km_mensuel * ik_rate_display
    st.caption(f"Total IK : {ik_total:,.2f} €")
    
    st.markdown("**Autres Frais Remboursables**")
    frais_teletravail = st.number_input("Forfait Télétravail (€)", value=0.0, step=10.0)
    frais_internet = st.number_input("Internet / Téléphone (€)", value=0.0, step=10.0)
    frais_transport = st.number_input("Transports (Navigo...) (€)", value=0.0, step=10.0)
    frais_repas = st.number_input("Repas / Divers (€)", value=0.0, step=10.0)
    
    expenses_other = frais_teletravail + frais_internet + frais_transport + frais_repas
    st.caption(f"Total Autres Frais : {expenses_other:,.2f} €")
    
    st.markdown("---")
    use_reserve = st.checkbox("Réserve Financière", value=True)
    use_mutuelle = st.checkbox("Mutuelle Santé", value=True)


# Main : Onglets
tab_simu, tab_config = st.tabs(["📊 Résultats Simulation", "⚙️ Configuration Globale"])

with tab_config:
    st.header("Paramètres Globaux de Calcul")
    st.warning("⚠️ Ces modifications impactent tous les calculs. A modifier avec précaution.")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("Salaires & Primes")
        st.session_state.cfg_base_salary = st.number_input(
            "Salaire de Base Temps Plein (€)", 
            value=st.session_state.cfg_base_salary, step=50.0
        )
        st.session_state.cfg_taux_prime = st.number_input(
            "Taux Prime d'Apport (%)", 
            value=st.session_state.cfg_taux_prime, step=0.1
        )
        st.session_state.cfg_taux_cp = st.number_input(
            "Taux Indemnité Congés Payés (%)", 
            value=st.session_state.cfg_taux_cp, step=0.1
        )
        st.session_state.cfg_taux_reserve = st.number_input(
            "Taux Réserve Financière (%)", 
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
        st.session_state.cfg_pmss = st.number_input(
            "Plafond Sécu (PMSS) (€)", 
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
        st.session_state.cfg_ik_rate = st.number_input(
            "Taux Remboursement IK (€/km)", 
            value=st.session_state.cfg_ik_rate, step=0.01, format="%.3f"
        )
        st.divider()
        st.session_state.cfg_mutuelle_part_pat = st.number_input(
            "Part Patronale Mutuelle (%)", 
            value=st.session_state.cfg_mutuelle_part_pat, step=5.0
        )
    
    st.success("Les modifications sont prises en compte automatiquement dans l'onglet 'Résultats'.")

with tab_simu:
    # Calcul avec les valeurs dynamiques
    results = calculate_salary(tjm, days_worked_month, days_worked_week, 
                               ik_total, expenses_other, use_reserve, use_mutuelle)

    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Chiffre d'Affaires", f"{results['turnover']:,.2f} €")
    with kpi2:
        st.metric("Salaire Brut", f"{results['gross_salary']:,.2f} €")
    with kpi3:
        total_charges = results['employer_charges'] + results['employee_charges'] + results['mutuelle_part_pat'] + results['mutuelle_part_sal']
        st.metric("Charges Totales (+Mutuelle)", f"{total_charges:,.2f} €")
    with kpi4:
        st.metric("NET À PAYER", f"{results['net_payable']:,.2f} €", delta="Virement")

    st.divider()

    # Tableau et Graphique
    col_main, col_viz = st.columns([2, 1])

    with col_main:
        st.subheader("Détail du Bulletin")
        
        # Récupération des taux pour affichage dans le tableau
        txt_gest = f"Frais de gestion ({st.session_state.cfg_frais_gestion}%)"
        txt_ik = f"Indemnités Kilométriques ({st.session_state.cfg_ik_rate} €/km)"
        
        data_lines = [
            ("Chiffre d'affaires (CA)", results['turnover'], "Positif"),
            (txt_gest, -results['management_fees'], "Negatif"),
            (txt_ik, -results['ik_amount'], "Neutre"),
            ("Autres Frais", -results['other_expenses'], "Neutre"),
            ("= MASSE SALARIALE DISPONIBLE", results['masse_salariale_budget'], "Total"),
            ("", 0, "Empty"),
            ("Salaire de Base", results['base_salary'], "Detail"),
            ("Prime d'apport d'affaires", results['prime_apport'], "Detail"),
            ("Complément de rémunération", results['complement_remuneration'], "Detail"),
            ("Indemnité Congés Payés", results['indemnite_cp'], "Detail"),
            ("= TOTAL BRUT", results['gross_salary'], "Total"),
            ("", 0, "Empty"),
            ("Réserve Financière", -results['reserve_amount'], "Negatif"),
            ("Mutuelle Part Patronale", -results['mutuelle_part_pat'], "Negatif"),
            ("Charges Patronales", -results['employer_charges'], "Negatif"),
            ("Charges Salariales", -results['employee_charges'], "Negatif"),
            ("Mutuelle Part Salariale", -results['mutuelle_part_sal'], "Negatif"),
            ("= NET AVANT IMPÔT", results['net_before_tax'], "Total"),
            ("", 0, "Empty"),
            ("Remboursement Frais", results['total_expenses'], "Positif"),
            ("= NET À PAYER", results['net_payable'], "Final")
        ]
        
        df_disp = pd.DataFrame(data_lines, columns=["Libellé", "Montant", "Type"])
        
        st.dataframe(
            df_disp[df_disp["Type"] != "Empty"][["Libellé", "Montant"]].style.format({"Montant": "{:,.2f} €"}),
            use_container_width=True,
            hide_index=True,
            height=600
        )

    with col_viz:
        st.subheader("Répartition")
        labels = ['Net Avant Impôt', 'Charges Sociales', 'Mutuelle', 'Frais Gestion', 'Réserve']
        values = [results['net_before_tax'], 
                  results['employee_charges'] + results['employer_charges'],
                  results['mutuelle_part_pat'] + results['mutuelle_part_sal'],
                  results['management_fees'], results['reserve_amount']]
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### Export")
        pdf_bytes = create_pdf(results, consultant_name)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="simulation_{consultant_name}.pdf" style="text-decoration:none;">' \
               f'<button style="width:100%; padding: 10px; background-color: #FF4B4B; color: white; border: none; border-radius: 5px; cursor: pointer;">' \
               f'📄 Télécharger le PDF</button></a>'
        st.markdown(href, unsafe_allow_html=True)
