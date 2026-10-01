"""Dossiers personnels : paramètres et PDF enregistrés dans une même transaction."""
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


EXTRA_KEYS = {
    "sps_taux", "saisie_dom", "saisie_mis", "sel_dom", "sel_mis",
    "geo_dom", "geo_mis", "ik_km_calcule", "ik_km_aller", "ik_duree",
}


def identite(user):
    """Identité issue de la session SSO, jamais de l'email ni du formulaire."""
    if not user.get("is_logged_in"):
        raise ValueError("Connexion Microsoft requise.")
    try:
        return f"{UUID(str(user.get('tid')))}:{UUID(str(user.get('oid')))}"
    except ValueError:
        raise ValueError("Identifiant Microsoft indisponible. Reconnectez-vous.") from None


def parametres(state):
    return {k: state[k] for k in state if k.startswith(("sim_", "cfg_")) or k in EXTRA_KEYS}


def restaurer(state, valeurs):
    for key in parametres(state):
        del state[key]
    state.update(parametres(valeurs))


@contextmanager
def connexion():
    # ponytail: une instance avec disque local ; PostgreSQL si plusieurs serveurs.
    path = Path(os.environ.get("DOSSIERS_DB_PATH", str(Path(__file__).parent / "data/dossiers.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS dossiers (
            id TEXT PRIMARY KEY, proprietaire TEXT NOT NULL,
            consultant TEXT NOT NULL, cree_le TEXT NOT NULL, modifie_le TEXT NOT NULL,
            revision INTEGER NOT NULL, donnees TEXT NOT NULL,
            pdf BLOB NOT NULL, nom_pdf TEXT NOT NULL
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS dossiers_proprietaire ON dossiers(proprietaire, modifie_le)")
        yield db


def lister(proprietaire):
    with connexion() as db:
        return [dict(row) for row in db.execute(
            "SELECT id, consultant, cree_le, modifie_le, revision FROM dossiers "
            "WHERE proprietaire = ? ORDER BY modifie_le DESC, id", (proprietaire,))]


def ouvrir(proprietaire, dossier_id):
    with connexion() as db:
        row = db.execute("SELECT * FROM dossiers WHERE id = ? AND proprietaire = ?",
                         (dossier_id, proprietaire)).fetchone()
    if row is None:
        raise ValueError("Ce dossier n'est pas accessible.")
    dossier = dict(row)
    dossier["donnees"] = json.loads(dossier["donnees"])
    return dossier


def enregistrer(proprietaire, dossier_id, revision, consultant, donnees, pdf, nom_pdf):
    if not proprietaire or not consultant.strip() or not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
        raise ValueError("Le dossier doit contenir un consultant et un PDF valide.")
    payload = json.dumps(donnees, ensure_ascii=False, allow_nan=False, sort_keys=True)
    maintenant = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with connexion() as db:
        actuel = db.execute("SELECT revision, donnees, pdf FROM dossiers WHERE id = ? AND proprietaire = ?",
                            (dossier_id, proprietaire)).fetchone()
        if actuel and actuel["donnees"] == payload and actuel["pdf"] == pdf:
            return actuel["revision"]  # Double clic : même dossier, même sauvegarde.
        if revision == 0:
            db.execute("INSERT INTO dossiers VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
                       (dossier_id, proprietaire, consultant, maintenant, maintenant, payload, pdf, nom_pdf))
        else:
            updated = db.execute(
                "UPDATE dossiers SET consultant = ?, modifie_le = ?, revision = revision + 1, "
                "donnees = ?, pdf = ?, nom_pdf = ? WHERE id = ? AND proprietaire = ? AND revision = ?",
                (consultant, maintenant, payload, pdf, nom_pdf, dossier_id, proprietaire, revision))
            if updated.rowcount != 1:
                raise ValueError("Ce dossier a changé dans un autre onglet. Rouvrez-le avant de l'enregistrer.")
    return revision + 1
