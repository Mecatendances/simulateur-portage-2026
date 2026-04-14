# Simulateur de Portage Salarial 2026 — Document de Synthèse

## 1. Présentation Générale

Le **Simulateur de Portage Salarial 2026** est une application web interactive développée en **Python/Streamlit** qui calcule en temps réel la rémunération nette d'un consultant en portage salarial à partir de son TJM (Taux Journalier Moyen).

**Objectif :** Remplacer un fichier Excel complexe (contenant des formules à 38+ niveaux d'imbrication IF) par un moteur de calcul fiable, transparent et aligné avec la méthodologie **Silae** (logiciel de paie de référence).

**Stack technique :**

| Composant | Technologie |
|-----------|-------------|
| Interface web | Streamlit |
| Calculs | Python (Pandas) |
| Visualisation | Plotly |
| Export PDF | FPDF |
| Support Excel | openpyxl |

---

## 2. Architecture du Projet

```
Simu/
├── app.py                          # Application principale (~1 300 lignes)
├── METHODOLOGIE_CALCULS.md         # Documentation technique des calculs
├── README.md                       # Présentation du projet
├── requirements.txt                # Dépendances Python
├── Dockerfile                      # Configuration Docker
├── SYNTHESE_SIMULATEUR.md          # Ce document
│
├── Fichiers Excel (données de référence/test) :
│   ├── Simulation Annuelle Temps Complet 2025 - Modifiée.xlsx
│   └── RETOUR SIMUL V2 2.xlsx
│
└── Scripts d'analyse (rétro-ingénierie de l'Excel original) :
    ├── analyze_excel.py
    ├── analyze_excel_deep.py
    ├── analyze_formula_context.py
    └── find_complex_formula.py
```

---

## 3. Flux de Données

```
┌─────────────────────────────────────────────────────────┐
│               ENTRÉES UTILISATEUR (Sidebar)              │
│  TJM, jours travaillés, frais (IK, IGD, TR, télétravail)│
│  Options : réserve, mutuelle, effectif ≥50              │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│            MOTEUR DE CALCUL  calculate_salary()          │
│                                                          │
│  1. CA et Montant Disponible                             │
│  2. Composantes du salaire brut                          │
│  3. Convergence itérative du taux de charges (50 iter.)  │
│  4. Cotisations patronales (24 lignes Silae)             │
│  5. Réduction RGDU 2026                                  │
│  6. Provision réserve financière                         │
│  7. Cotisations salariales                               │
│  8. Net avant impôt + Net à payer                        │
└──────────────────────────┬──────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌───────────┐  ┌───────────┐  ┌──────────────┐
     │ Onglet 1  │  │ Onglet 2  │  │  Onglet 3    │
     │ Résultats │  │  Config   │  │ Email/Explic.│
     │ + PDF     │  │ Globale   │  │              │
     └───────────┘  └───────────┘  └──────────────┘
```

---

## 4. Entrées Utilisateur

### 4.1 Informations Consultant

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| Nom | Texte | — | Nom du consultant |
| TJM | EUR | 500 | Taux Journalier Moyen |
| Jours/mois | Décimal | 19 | Jours travaillés par mois |
| Jours/semaine | 1-7 | 5 | Jours travaillés par semaine |
| Intermédiation | % | 0% | Frais d'intermédiation client |

### 4.2 Frais Professionnels

| Catégorie | Paramètres | Barème 2026 |
|-----------|-----------|-------------|
| **Indemnités Kilométriques (IK)** | Type véhicule, CV fiscaux, tranche km, km/mois | Jusqu'à 0,697 €/km |
| **Grand Déplacement (IGD)** | Nb repas, nb nuitées, zone (Province/Paris) | Repas : 21,60 € · Nuitée : 57,80 € / 76,70 € |
| **Titres Restaurant** | Nb de titres | Valeur faciale : 14,36 € (part patronale max : 7,18 €) |
| **Télétravail** | Jours (0-22) | 2,70 €/jour |
| **Autres frais** | Internet, transport, divers | Montants libres |

### 4.3 Options

| Option | Défaut | Effet |
|--------|--------|-------|
| Réserve Financière | Activée | Provisionne 10% du salaire de base |
| Mutuelle Santé | Activée | 1,5% du PMSS, 50% employeur |
| Effectif ≥ 50 | Désactivé | Change le taux FNAL (0,10% → 0,50%) |

---

## 5. Moteur de Calcul

### 5.1 Étape 1 — Du CA au Montant Disponible

```
Chiffre d'Affaires (CA)    = TJM × jours travaillés/mois
Frais de gestion            = CA × 5%
Frais d'intermédiation      = CA × taux intermédiation
─────────────────────────────────────────────────────────
MONTANT DISPONIBLE          = CA − Frais de gestion − Frais d'intermédiation
```

### 5.2 Étape 2 — Construction du Salaire Brut

Le brut est composé de 5 éléments :

| Composante | Formule |
|-----------|---------|
| **Salaire de base** | 2 374 € × (jours_semaine / 5) |
| **Prime d'apport** | Base × 5% |
| **Complément de rémunération** | Calculé par convergence (variable) |
| **Complément apport d'affaires** | Complément × 5% |
| **Indemnité de Congés Payés (ICP)** | 10% × (Base + Prime + Complément) |
| **= BRUT TOTAL** | Somme des 5 composantes |

### 5.3 Étape 3 — Convergence Itérative du Taux de Charges

C'est l'algorithme le plus complexe du simulateur. Il résout une **dépendance circulaire** : le taux de charges détermine le brut, qui détermine les cotisations, qui déterminent le taux de charges.

```
taux_charges ← 0,55 (estimation initiale)

POUR iteration = 1 à 50 :
    pool           = budget_salaire / (1 + taux_charges)
    complément     = (pool − base − prime − réserve) / (1 + taux_prime)
    brut_estimé    = base + prime + complément + ICP

    cotisations    = calculer_cotisations(brut_estimé)          # 24 lignes
    charges_patron = cotisations + mutuelle + TR + forfait social

    # Calcul marginal des charges sur la réserve
    brut_avec_réserve = brut_estimé + réserve × (1 + taux_CP)
    cotis_avec_réserve = calculer_cotisations(brut_avec_réserve)
    charges_marginales = cotis_avec_réserve − cotisations

    total_charges    = charges_patron + charges_marginales
    nouveau_taux     = total_charges / pool

    SI |nouveau_taux − taux_charges| < 0,00001 : CONVERGE ✓
    taux_charges ← nouveau_taux

Précision obtenue : 4 décimales (ex. 58,6076%)
```

### 5.4 Étape 4 — Cotisations Sociales (24 lignes Silae)

Le simulateur calcule **24 types de cotisations** répartis sur 3 assiettes :

#### Assiette TOTALITÉ (brut entier)

| Cotisation | Taux Patron | Taux Salarié |
|-----------|------------|-------------|
| Maladie | 7,00% | — |
| Maladie Complémentaire | 6,00% | — |
| CSA (Autonomie) | 0,30% | — |
| Vieillesse Déplafonnée | 2,11% | 0,40% |
| Allocations Familiales | 3,45% | — |
| AF Complémentaire | 1,80% | — |
| AT/MP | 0,64% *(configurable)* | — |
| Chômage | 4,00% | — |
| AGS | 0,25% | — |
| Formation | 1,00% | — |
| Taxe Apprentissage | 0,59% | — |
| Taxe Apprentissage Libératoire | 0,09% | — |
| Dialogue Social | 0,01% | — |

#### Assiette TRANCHE A (jusqu'au PMSS = 4 005 €)

| Cotisation | Taux Patron | Taux Salarié |
|-----------|------------|-------------|
| Vieillesse Plafonnée | 8,55% | 6,90% |
| FNAL | 0,10% ou 0,50% | — |
| Retraite AGIRC-ARRCO T1 | 4,72% | 3,15% |
| CEG T1 | 1,29% | 0,86% |
| CET T1 | 0,21% | 0,14% |
| APEC T1 | 0,036% | 0,024% |
| Prévoyance Décès | 1,59% | — |

#### Assiette TRANCHE B (au-delà du PMSS)

| Cotisation | Taux Patron | Taux Salarié |
|-----------|------------|-------------|
| Retraite AGIRC-ARRCO T2 | 12,95% | 8,64% |
| CEG T2 | 1,62% | 1,08% |
| CET T2 | 0,21% | 0,14% |
| APEC T2 | 0,036% | 0,024% |
| Prévoyance Supplémentaire T2 | 0,73% | 0,73% |

#### Assiette CSG (98,25% du brut + prévoyance patronale)

| Cotisation | Taux Patron | Taux Salarié |
|-----------|------------|-------------|
| CSG Déductible | — | 6,80% |
| CSG/CRDS Non-déductible | — | 2,90% |

### 5.5 Étape 5 — Réduction RGDU 2026

La **Réduction Générale Dégressive Unique** s'applique automatiquement aux salaires inférieurs à 3 SMIC annuels (54 903,36 €).

```
ratio       = (3 × SMIC / Brut_annuel) − 1
coefficient = Tmin + Tdelta × (0,5 × ratio) ^ 1,75
réduction   = coefficient × Brut_annuel / 12
```

Paramètres selon la taille d'entreprise :
- **< 50 salariés** : FNAL 0,10%, Tmin = 0,3194, Tdelta = 0,0006
- **≥ 50 salariés** : FNAL 0,50%, Tmin = 0,3234, Tdelta = 0,0006

### 5.6 Étape 6 — Provision Réserve Financière

La réserve financière permet d'accumuler une épargne pour les périodes d'inter-contrat.

```
Provision Réserve Financière = MONTANT DISPONIBLE − (Brut + Charges Patronales)
```

**Composition :**
- **Réserve brute** = Salaire de base × (jours_semaine/5) × 10%
- **Charges futures sur la réserve** = Charges marginales calculées par analyse différentielle

**Mode « réserve réintégrée »** : La réserve est ajoutée au net (le consultant la perçoit immédiatement).

### 5.7 Étape 7 — Du Brut au Net

```
BRUT TOTAL
− Cotisations salariales (24 lignes)
− Mutuelle part salariale
− Titres Restaurant part salariale
────────────────────────────────────
= NET AVANT IMPÔT

+ Frais remboursés (IK + IGD + télétravail + autres)
────────────────────────────────────
= NET À PAYER
```

---

## 6. Interface Utilisateur

L'application comporte une **sidebar** (panneau latéral de saisie) et **3 onglets** principaux.

### 6.1 Onglet « Résultats Simulation »

- **4 indicateurs clés (KPI)** : CA, Brut, Total Charges, Net à Payer
- **Tableau détaillé** : ~25 lignes du CA au net, avec tous les postes intermédiaires
- **Graphique camembert** : Répartition (Net / Cotisations / Mutuelle & TR / Frais de gestion / Réserve)
- **Export PDF** : Téléchargement d'un bulletin de simulation complet
- **Sections dépliantes** :
  - Détail des charges patronales (ligne par ligne)
  - Détail des charges salariales (ligne par ligne)
  - Formules de calcul avec valeurs réelles

### 6.2 Onglet « Configuration Globale »

Paramètres ajustables en 3 colonnes :

| Colonne 1 : Salaires & Primes | Colonne 2 : Cotisations & Références | Colonne 3 : Frais & Divers |
|-------------------------------|--------------------------------------|---------------------------|
| Salaire de base (2 374 €) | Taux de charges (0 = auto) | Frais de gestion (5%) |
| Taux prime (5%) | Taux AT/MP (0,64%) | Taux IK (auto barème) |
| Taux congés payés (10%) | FNAL (auto selon effectif) | Barèmes IGD (lecture seule) |
| Taux réserve (10%) | PMSS (4 005 €) | Barèmes TR (lecture seule) |
| | SMIC mensuel (1 823,03 €) | |
| | Taux mutuelle (1,5%) | |
| | Part employeur mutuelle (50%) | |

Tableau de référence complet des 24 cotisations consultable en section dépliante.

### 6.3 Onglet « Email & Explications »

- **Explication pédagogique en 9 étapes** : Du CA au net, avec les valeurs réelles du calcul en cours, formules détaillées et tableaux de cotisations dépliants
- **Template email pré-rempli** : Prêt à copier/coller pour envoyer au consultant avec tous les montants calculés

---

## 7. Export PDF

La fonction `create_pdf()` génère un document professionnel contenant :

- Nom du consultant et date de calcul
- Section Activité & Frais (CA, frais de gestion, montant disponible)
- Décomposition complète du salaire brut
- Charges patronales détaillées (ligne par ligne)
- Charges salariales détaillées (ligne par ligne)
- Provision réserve financière
- Frais remboursés
- Net à payer final

Format : Tableaux 2 colonnes, montants alignés à droite en EUR.

---

## 8. Barèmes 2026 Intégrés

### Indemnités Kilométriques

**Voiture (extrait) :**

| CV Fiscaux | 0-5 000 km | 5 001-20 000 km | > 20 000 km |
|-----------|-----------|----------------|------------|
| 3 CV | 0,529 €/km | 0,316 €/km + 1 065 € | 0,370 €/km |
| 5 CV | 0,636 €/km | 0,357 €/km + 1 395 € | 0,427 €/km |
| 7 CV+ | 0,697 €/km | 0,394 €/km + 1 515 € | 0,470 €/km |

### Grand Déplacement

| Poste | Montant |
|-------|---------|
| Repas | 21,60 € |
| Nuitée Province | 57,80 € |
| Nuitée Paris/IDF | 76,70 € |

### Titres Restaurant

| Paramètre | Valeur |
|-----------|--------|
| Valeur faciale | 14,36 € |
| Part patronale max | 7,18 € |

### Télétravail

| Paramètre | Valeur |
|-----------|--------|
| Indemnité journalière | 2,70 € |
| Maximum | 22 jours/mois |

---

## 9. Alignement Méthodologie Silae

Le simulateur reproduit fidèlement le format de calcul du logiciel de paie Silae :

1. **Cotisations ligne par ligne** (et non agrégées) — 24 lignes distinctes
2. **Séparation Tranche A / Tranche B** selon le PMSS
3. **Base CSG** = 98,25% × Brut + Prévoyance patronale
4. **Complément de rémunération** calculé à partir du pool et du taux convergé
5. **Provision réserve** = MONTANT DISPO − (Brut + Charges) en une seule ligne
6. **Taux de charges** = Total charges / Pool (convergence itérative)

---

## 10. Paramètres de Référence

| Paramètre | Valeur 2026 | Rôle |
|-----------|-------------|------|
| SMIC mensuel | 1 823,03 € | Seuil RGDU, calcul réductions |
| PMSS | 4 005 € | Plafond Sécurité Sociale (Tranche A) |
| SMIC annuel × 3 | 54 903,36 € | Seuil d'application RGDU |
| Salaire de base | 2 374 € | Référence temps plein |
| Frais de gestion | 5% | Commission de la société de portage |
| Taux prime | 5% | Prime d'apport d'affaires |
| Taux congés payés | 10% | ICP |
| Taux réserve | 10% | Provision inter-contrat |
| Mutuelle | 1,5% PMSS | Complémentaire santé obligatoire |
| AT/MP | 0,64% | Accident du travail (configurable) |

---

## 11. Synthèse Fonctionnelle

```
┌──────────────────────────────────────────────────────────────┐
│                   CE QUE FAIT LE SIMULATEUR                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ✓ Calcul en temps réel du net consultant                    │
│  ✓ 24 cotisations sociales ligne par ligne (format Silae)    │
│  ✓ Convergence itérative du taux de charges                  │
│  ✓ Réduction RGDU 2026 automatique                           │
│  ✓ Gestion réserve financière + charges marginales           │
│  ✓ Tous les frais professionnels (IK, IGD, TR, télétravail)  │
│  ✓ Export PDF professionnel                                  │
│  ✓ Template email pré-rempli                                 │
│  ✓ Explications pédagogiques pas à pas                       │
│  ✓ Configuration complète des paramètres                     │
│  ✓ Graphique de répartition visuel                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Utilisateurs cibles :** Consultants en portage salarial souhaitant estimer leur rémunération nette, et gestionnaires RH calculant les coûts employeur.

---

*Document généré le 11 février 2026 — Simulateur de Portage Salarial v2026*
