# 📊 Simulateur de Portage Salarial 2025

Ce simulateur est un outil interactif permettant de calculer le revenu net d'un consultant en portage salarial en fonction de son TJM, de ses jours travaillés et de ses frais professionnels. Il est basé sur les règles et taux de charges sociales de 2025.

## 🚀 Fonctionnalités

- **Calcul en temps réel** : Simulation instantanée du bulletin de paie (Brut, Net, Charges).
- **Logique 2025** : Intègre le Salaire de Base (2374€), la prime d'apport d'affaires (5%), et la réserve financière (10%).
- **Gestion des Frais** : Calcul détaillé des Indemnités Kilométriques (1.25€/km - Catégorie C) et des frais remboursables (Télétravail, repas, etc.).
- **Mutuelle Santé** : Prise en compte de la mutuelle (1.5% du PMSS) avec répartition employeur/salarié.
- **Configuration Flexible** : Un onglet dédié permet de modifier tous les paramètres globaux (taux de charges, PMSS, salaire de base).
- **Export PDF** : Génération d'un récapitulatif détaillé pour le consultant.

## 🛠 Installation et Utilisation

### Localement
1. Clonez le dépôt :
   ```bash
   git clone https://github.com/Mecatendances/simulateur-portage-2025.git
   cd simulateur-portage-2025
   ```
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancez l'application :
   ```bash
   streamlit run app.py
   ```

### Via Docker
1. Construisez l'image :
   ```bash
   docker build -t simulateur-portage .
   ```
2. Lancez le conteneur :
   ```bash
   docker run -p 8501:8501 simulateur-portage
   ```

## 📈 Logique de Calcul

L'application utilise une méthode de "calcul à l'envers" pour optimiser le salaire du consultant :
- **Chiffre d'Affaires** = TJM × Jours Facturés
- **Masse Salariale** = CA - Frais de Gestion - Frais Professionnels - Mutuelle (Part Pat.)
- **Salaire Brut** = Calculé pour équilibrer la Masse Salariale en incluant les charges patronales et les congés payés.

---
*Développé pour l'optimisation des revenus en portage salarial.*
