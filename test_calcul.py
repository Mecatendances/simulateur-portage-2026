"""Garde-fous logique d'argent. Lancer : python test_calcul.py (sans Streamlit)."""
import os, types
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class _SS(dict):  # st.session_state : acces attribut + cle
    __getattr__ = dict.__getitem__
    def __setattr__(self, k, v): self[k] = v

st = types.SimpleNamespace(session_state=_SS(), cache_data=lambda **k: (lambda f: f))
src = open("app.py", encoding="utf-8").read()
# Constantes + init session_state + fonctions de calcul, sans imports ni UI
g = {"st": st, "requests": None}
exec(src[src.index("\n", src.index("from weasyprint")):src.index("# --- Chemin logo ---")], g)
calc, cotis = g["calculate_salary"], g["calculer_cotisations"]

def run(tjm, **kw):
    a = dict(days_worked_month=20, days_worked_week=5, ik_amount=0, igd_amount=0, other_expenses=0,
             use_reserve=True, use_mutuelle=True, nb_titres_restaurant=0, frais_intermediation_pct=0,
             jours_teletravail=0, effectif_sup_50=False)
    a.update(kw)
    return calc(tjm, **a)

noms = lambda c: {d["nom"] for d in c["details"]}

# CET : nulle si brut <= PMSS, sinon due sur T1 ET T2
assert not {"cet_t1", "cet_t2"} & noms(cotis(4005.0, 4005.0, 0.0064, 0.001, 0))
assert {"cet_t1", "cet_t2"} <= noms(cotis(4005.01, 4005.0, 0.0064, 0.001, 0))

# Charges S+PS = taux x CA, retirees 1:1 du montant disponible
r0, r1 = run(500), run(500, taux_charges_sps=2.5)
assert abs(r1["charges_sps"] - 250.0) < 1e-9
assert abs((r0["montant_disponible"] - r1["montant_disponible"]) - 250.0) < 1e-9
assert r1["net_payable"] < r0["net_payable"]
assert run(0, days_worked_month=0, taux_charges_sps=5)["charges_sps"] == 0  # CA=0 : pas de crash

# Reserve provisionnee : tout le budget est reparti (brut + charges pat + provision), CDI et CDD
for tc in ("CDI", "CDD"):
    for tjm in (400, 700, 1200):
        r = run(tjm, taux_charges_sps=3, type_contrat=tc)
        ecart = r["montant_disponible"] - r["gross_salary"] - r["employer_charges"] - r["provision_reserve_financiere"]
        assert abs(ecart) < 0.01, (tc, tjm, ecart)

# RGDU (ticket 717) : reduit les charges, revient au salaire, ne gonfle pas la provision CDI
for tjm, j in ((300, 20), (400, 20), (450, 18), (450, 15)):
    r = run(tjm, days_worked_month=j, nb_journees=j, nb_jours_ouvres=j)
    assert r["reduction_rgdu"] > 0 and r["provision_reserve_financiere"] < 395, (tjm, j, r["provision_reserve_financiere"])
    r = run(tjm, days_worked_month=j, nb_journees=j, nb_jours_ouvres=j, use_reserve=False)
    assert abs(r["budget_salaire"] - r["gross_salary"] - r["employer_charges"]) < 0.05, (tjm, j)  # tout distribue

# CDD : l'ICP est dans la cascade 1.2705, pas recomptee en charge -> budget reparti, provision = reserve chargee
for tc in ("CDI", "CDD"):
    for tjm in (300, 450, 600):
        r = run(tjm, type_contrat=tc, use_reserve=False)
        assert abs(r["budget_salaire"] - r["gross_salary"] - r["employer_charges"]) < 0.05, (tc, tjm)
        p = run(tjm, type_contrat=tc)
        assert 1.5 < p["provision_reserve_financiere"] / p["reserve_brute"] < 1.65, (tc, tjm)

# Signataire : fiche Entra si dispo, sinon nom SSO (Graph indisponible ici -> repli)
g["fiche_entra"] = lambda e: {"displayName": "Benoit BRETECHE", "jobTitle": "BM", "mobilePhone": "06"} if e.startswith("benoit") else {}
c = g["contact_signataire"]("Benoit.Breteche@signeplus.com")
assert (c["name"], c["title"], c["email"]) == ("Benoit BRETECHE", "BM", "benoit.breteche@signeplus.com")
c = g["contact_signataire"]("x@signeplus.com", "X Y")
assert (c["name"], c["title"], c["mobile"]) == ("X Y", "", "")

# Texte reserve : CDD ne parle pas de rupture conventionnelle
assert "rupture conventionnelle" not in g["texte_reserve"]("CDD")
assert "rupture conventionnelle" in g["texte_reserve"]("CDI")

print("OK")
