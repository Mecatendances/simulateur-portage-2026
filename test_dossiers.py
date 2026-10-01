"""python test_dossiers.py : sauvegarde, reprise, doublons et isolation, sans dépendance."""
import os
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import dossiers


def verifier():
    tenant, alice, bob = str(uuid4()), str(uuid4()), str(uuid4())
    owner = dossiers.identite({"is_logged_in": True, "tid": tenant, "oid": alice})
    autre = dossiers.identite({"is_logged_in": True, "tid": tenant, "oid": bob})
    autre_tenant = dossiers.identite({"is_logged_in": True, "tid": str(uuid4()), "oid": alice})
    for user in ({}, {"is_logged_in": True, "email": "alice@example.test"}):
        try:
            dossiers.identite(user)
            raise AssertionError("Une identité incomplète doit être refusée")
        except ValueError:
            pass

    state = {"sim_prenom": "Alice", "sim_tjm": 625, "cfg_frais_gestion": 8.0,
             "sps_taux": 2.5, "geo_dom": {"label": "Adresse de test", "lat": 48.0},
             "_dossier_proprietaire": owner, "secret": "à exclure"}
    params = dossiers.parametres(state)
    assert "secret" not in params and "_dossier_proprietaire" not in params
    donnees = {"format": 1, "parametres": params, "resultats": {"net_payable": 4500.5}}
    identifiant = uuid4().hex
    pdf = b"%PDF-1.7\narchive de test\n%%EOF"
    revision = dossiers.enregistrer(owner, identifiant, 0, "Alice", donnees, pdf, "alice.pdf")
    assert revision == 1
    # Nouvelle connexion : données et octets PDF durables et inchangés.
    saved = dossiers.ouvrir(owner, identifiant)
    assert saved["donnees"] == donnees and saved["pdf"] == pdf
    assert saved["cree_le"] == saved["modifie_le"]
    assert dossiers.enregistrer(owner, identifiant, 0, "Alice", donnees, pdf, "alice.pdf") == 1
    assert len(dossiers.lister(owner)) == 1
    assert dossiers.ouvrir(owner, identifiant)["modifie_le"] == saved["modifie_le"]

    for other in (autre, autre_tenant):
        assert dossiers.lister(other) == []
        try:
            dossiers.ouvrir(other, identifiant)
            raise AssertionError("Lecture d'un dossier appartenant à un autre compte")
        except ValueError:
            pass
        for rev in (0, 1):
            try:
                dossiers.enregistrer(other, identifiant, rev, "Bob", donnees, pdf, "bob.pdf")
                raise AssertionError("Écriture d'un dossier appartenant à un autre compte")
            except (ValueError, sqlite3.IntegrityError):
                pass
    assert dossiers.ouvrir(owner, identifiant) == saved

    state["sim_tjm"] = 999
    state["sim_commission_fixe"] = 200
    dossiers.restaurer(state, saved["donnees"]["parametres"])
    assert state["sim_tjm"] == 625 and state["cfg_frais_gestion"] == 8.0
    assert "sim_commission_fixe" not in state and state["_dossier_proprietaire"] == owner
    assert state["geo_dom"]["lat"] == 48.0

    donnees["parametres"]["sim_tjm"] = 700
    assert dossiers.enregistrer(owner, identifiant, 1, "Alice", donnees, pdf + b"updated", "alice.pdf") == 2
    assert len(dossiers.lister(owner)) == 1
    try:
        dossiers.enregistrer(owner, identifiant, 1, "Alice", saved["donnees"], pdf, "alice.pdf")
        raise AssertionError("Une ancienne version ne doit pas écraser le dossier")
    except ValueError:
        pass
    assert dossiers.ouvrir(owner, identifiant)["donnees"]["parametres"]["sim_tjm"] == 700

    previous = dossiers.ouvrir(owner, identifiant)
    try:
        dossiers.enregistrer(owner, identifiant, 2, "Alice", donnees, b"invalid", "alice.pdf")
        raise AssertionError("Un PDF invalide ne doit pas remplacer la sauvegarde")
    except ValueError:
        pass
    assert dossiers.ouvrir(owner, identifiant) == previous


def verifier_interface():
    """Parcours réel Streamlit avec un annuaire fictif, sans connexion Microsoft."""
    from hashlib import md5
    from types import SimpleNamespace
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest

    class User(dict):
        __getattr__ = dict.__getitem__

    user = User(is_logged_in=True, tid=str(uuid4()), oid=str(uuid4()),
                name="Camille Test", email="camille@example.test")
    owner = dossiers.identite(user)
    profile = SimpleNamespace(json=lambda: {"displayName": "Camille Test", "jobTitle": "Conseil"},
                              raise_for_status=lambda: None)
    token = SimpleNamespace(json=lambda: {"access_token": "test"})

    def demarrer():
        at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30)
        at.secrets["auth"] = {"server_metadata_url": "https://login.microsoftonline.com/test/v2.0",
                              "client_id": "test", "client_secret": "test"}
        at.run()
        assert not at.exception, at.exception
        return at

    def cliquer(at, key):
        at.button(key=key).click().run()
        assert not at.exception, at.exception
        # AppTest 1.50 ne retient pas la page cible après st.switch_page.
        at._page_hash = md5(b"profil").hexdigest() if any(t.value == "Mon profil" for t in at.title) else ""

    def telecharger(at):
        # Streamlit 1.50 expose le téléchargement comme UnknownElement : envoyer son clic natif.
        download = next(w for w in at.get("download_button") if w.proto.label == "Télécharger le PDF")
        widgets = at._tree.get_widget_states()
        widgets.widgets.add(id=download.proto.id, trigger_value=True)
        at._run(widgets)
        assert not at.exception, at.exception

    with patch("streamlit.user", user), patch("requests.post", return_value=token), patch("requests.get", return_value=profile):
        at = demarrer()
        assert at.button(key="enregistrer_dossier").disabled
        at.text_input(key="sim_prenom").input("Alice")
        at.text_input(key="sim_nom").input("Martin")
        at.text_input(key="sim_email").input("alice@example.test")
        at.radio(key="sim_contrat").set_value("CDD")
        at.radio(key="sim_temps_travail").set_value("Partiel")
        at.radio(key="sim_mode_tr").set_value("Manuel")
        at.radio(key="sim_commission_mode").set_value("Montant fixe")
        at.selectbox(key="sim_vehicule").set_value("Moto")
        at.selectbox(key="sim_mois").set_value("Mai 2026")
        at.run()
        assert at.number_input(key="sim_jours_ouvres").value == 18
        for key, value in {"sim_tjm": 680, "sim_journees": 12, "sim_demi_journees": 2,
                           "sim_jours_semaine_partiel": 3.0, "sim_tr_manuel": 4,
                           "sim_commission_fixe": 250.0, "sim_tel": 60.0,
                           "sim_km": 125.0, "cfg_frais_gestion": 8.0}.items():
            at.number_input(key=key).set_value(value)
        at.selectbox(key="sim_cv_moto").set_value(4)
        at.run()
        assert not at.exception, at.exception

        # Visiter le profil puis revenir conserve aussi les saisies non enregistrées.
        saisies = dossiers.parametres(at.session_state.filtered_state)
        cliquer(at, "ouvrir_profil")
        assert any(t.value == "Mon profil" for t in at.title)
        assert len(at.sidebar.text_input) == 0
        at.run()
        cliquer(at, "retour_simulateur")
        assert dossiers.parametres(at.session_state.filtered_state) == saisies

        telecharger(at)
        rows = dossiers.lister(owner)
        assert len(rows) == 1
        dossier_id = rows[0]["id"]
        saved = dossiers.ouvrir(owner, dossier_id)
        assert saved["pdf"].startswith(b"%PDF-")
        assert saved["donnees"]["resultats"]["management_fees"] == 680 * 13 * .08
        assert saved["donnees"]["parametres"]["sim_email"] == "alice@example.test"
        cliquer(at, "enregistrer_dossier")
        assert len(dossiers.lister(owner)) == 1

        # Une saisie et Enregistrer dans le même événement sauvegardent le nouveau calcul.
        at.number_input(key="sim_tjm").set_value(690)
        cliquer(at, "enregistrer_dossier")
        saved = dossiers.ouvrir(owner, dossier_id)
        assert saved["donnees"]["parametres"]["sim_tjm"] == 690
        assert saved["donnees"]["resultats"]["management_fees"] == 690 * 13 * .08

        # Le téléchargement déjà préparé ne doit pas écraser l'archive après une nouvelle saisie.
        at.number_input(key="sim_tjm").set_value(695)
        telecharger(at)
        assert dossiers.ouvrir(owner, dossier_id) == saved
        assert at.session_state["_dossier_pdf"] == saved["pdf"]
        assert any("Attendez le recalcul" in e.value for e in at.error)
        assert at.number_input(key="sim_tjm").value == 695
        telecharger(at)
        saved = dossiers.ouvrir(owner, dossier_id)
        assert saved["donnees"]["parametres"]["sim_tjm"] == 695
        assert saved["donnees"]["resultats"]["management_fees"] == 695 * 13 * .08
        assert "_dossier_erreur" not in at.session_state

        cliquer(at, "nouveau_dossier")
        assert at.text_input(key="sim_prenom").value == ""
        assert at.number_input(key="cfg_frais_gestion").value == 5.0
        cliquer(at, "ouvrir_profil")
        cliquer(at, "ouvrir_" + dossier_id)
        assert not at.exception, at.exception
        assert dossiers.parametres(at.session_state.filtered_state) == saved["donnees"]["parametres"]
        at.number_input(key="sim_tjm").set_value(700).run()
        cliquer(at, "ouvrir_profil")
        cliquer(at, "nouveau_dossier_profil")
        assert at.button(key="confirmer_changement_dossier")
        assert at.session_state["sim_tjm"] == 700
        cliquer(at, "retour_simulateur")
        assert at.number_input(key="sim_tjm").value == 700
        cliquer(at, "enregistrer_dossier")
        assert len(dossiers.lister(owner)) == 1
        saved = dossiers.ouvrir(owner, dossier_id)
        assert saved["donnees"]["parametres"]["sim_tjm"] == 700

        with patch("dossiers.enregistrer", side_effect=sqlite3.OperationalError("test")), patch("logging.exception"):
            at.button(key="enregistrer_dossier").click().run()
        assert any("Dossier non enregistré" in e.value for e in at.error)
        assert at.number_input(key="sim_tjm").value == 700
        assert dossiers.ouvrir(owner, dossier_id) == saved

        at = demarrer()  # Nouvelle session : liste et reprise toujours accessibles.
        cliquer(at, "ouvrir_profil")
        cliquer(at, "ouvrir_" + dossier_id)
        assert at.number_input(key="sim_tjm").value == 700
        assert at.session_state["_dossier_pdf"] == saved["pdf"]
        user["oid"] = str(uuid4())
        at.run()  # Changement d'identité : ni dossier ni PDF de l'ancien compte.
        assert not at.exception, at.exception
        assert at.text_input(key="sim_prenom").value == ""
        cliquer(at, "ouvrir_profil")
        assert not any(b.key == "ouvrir_" + dossier_id for b in at.button)
        assert "_dossier_pdf" not in at.session_state
        user["is_logged_in"] = False
        at = demarrer()
        at._page_hash = md5(b"profil").hexdigest()
        at.run()
        assert not any(b.key == "enregistrer_dossier" for b in at.button)
        assert not any(t.value == "Mon profil" for t in at.title)
    print("OK : page profil, aller-retour sans perte, téléchargement, reprise, échec de stockage et changement de compte")


if __name__ == "__main__":
    original = os.environ.get("DOSSIERS_DB_PATH")
    try:
        with TemporaryDirectory() as tmp:
            os.environ["DOSSIERS_DB_PATH"] = str(Path(tmp) / "dossiers.sqlite3")
            verifier()
            if "--ui" in sys.argv:
                verifier_interface()
    finally:
        if original is None:
            os.environ.pop("DOSSIERS_DB_PATH", None)
        else:
            os.environ["DOSSIERS_DB_PATH"] = original
    print("OK : reprise, PDF conservé, doublons, conflits et accès personnels")
