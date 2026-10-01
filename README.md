# 📊 Simulateur de Portage Salarial 2026

Ce simulateur est un outil interactif permettant de calculer le revenu net d'un consultant en portage salarial en fonction de son TJM, de ses jours travaillés et de ses frais professionnels. Il est à jour avec les barèmes du **1er Janvier 2026**.

## 🚀 Fonctionnalités

- **Calcul en temps réel** : Simulation instantanée du bulletin de paie (Brut, Net, Charges).
- **Barèmes 2026** : Intègre le nouveau SMIC (1 823,03 €) et le nouveau PMSS (4 005 €).
- **Gestion des Frais** : Calcul détaillé des Indemnités Kilométriques (1.25€/km) et frais remboursables.
- **Mutuelle Santé** : Prise en compte de la mutuelle basée sur le PMSS 2026.
- **Email & Explications** : Générateur de texte commercial pour accompagner l'envoi des simulations.

## 🛠 Installation

```bash
git clone https://github.com/Mecatendances/simulateur-portage-2026.git
pip install -r requirements.txt
streamlit run app.py
```

## Dossiers personnels

L'encart avec le nom de la personne connectée, en haut à droite, ouvre la page
**Mon profil** (`/profil`) : coordonnées Microsoft et **Mes dossiers en cours**.
Le bouton **Retour au simulateur** conserve les saisies, même non enregistrées.
Un clic sur **Enregistrer le dossier** ou **Télécharger le PDF** conserve la simulation
et son PDF. **Reprendre** dans le profil revient au simulateur avec les champs et réglages du dossier.
Les sauvegardes suivantes mettent à jour ce même dossier ; **Nouveau dossier** ouvre
une simulation vierge. Un avertissement protège les modifications non enregistrées
lors d'un changement de dossier. Le dernier PDF sauvegardé reste téléchargeable
dans le menu **PDF enregistré** du simulateur.

Chaque dossier appartient au compte Microsoft (`tid` + `oid`) qui l'a créé.
Le nom ou le prénom du consultant est requis. Le profil reste alimenté par Entra.
Le PDF et les données sont enregistrés dans la même transaction SQLite ; une modification
concurrente depuis un autre onglet est refusée. Un échec de stockage est signalé à l'écran,
y compris après un clic sur le téléchargement : le navigateur peut recevoir le PDF
avant la confirmation de sauvegarde, il faut alors réessayer l'enregistrement.
Si une saisie change au moment du téléchargement, un message demande de retélécharger
le PDF après le recalcul pour conserver les dernières valeurs.

En local, la base se trouve dans `data/dossiers.sqlite3` (exclue de Git et de l'image Docker).
Pour Docker, `docker compose up -d --build` monte un volume nommé persistant et le fichier
de secrets SSO en lecture seule. Sur une autre plateforme, configurer
`DOSSIERS_DB_PATH=/data/dossiers.sqlite3` et monter **le même volume persistant** sur `/data`
à chaque déploiement. Utiliser une seule instance avec cette base locale.
Avec `docker run`, conserver `--restart unless-stopped`, le montage du fichier SSO en
lecture seule et les options `-e DOSSIERS_DB_PATH=/data/dossiers.sqlite3` et
`-v simulateur-portage-dossiers:/data` lors de chaque remplacement du conteneur.

Sauvegarder régulièrement la base avec l'API `sqlite3.Connection.backup` ou la commande
SQLite `.backup`, et vérifier la restauration. Ne pas supprimer le volume avec
`docker compose down -v`. La base contient les coordonnées des consultants et leurs simulations ;
son accès et les sauvegardes doivent être réservés aux personnes habilitées.

Vérifications : `python test_calcul.py`, `python test_dossiers.py`, puis
`python test_dossiers.py --ui` et `python test_pdf.py` dans l'environnement contenant
les dépendances du projet. Le test d'interface utilise un annuaire fictif et une base temporaire.

---
*Données mises à jour pour l'exercice 2026.*
