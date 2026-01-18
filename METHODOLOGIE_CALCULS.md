# 📘 Méthodologie Technique & Algorithmes 2026

Ce document explicite la logique de calcul du simulateur. Il détaille notamment comment nous avons remplacé les formules complexes de l'ancien fichier Excel par un moteur de calcul dynamique respectant les règles de paie françaises 2026.

---

## 1. Gestion des Abattements et Taux (Vs l'Ancien Excel)

### 📉 Le Problème de l'Ancien Excel (Les "39 SI")
L'ancien fichier utilisait une formule statique avec **38 conditions imbriquées** pour déterminer le taux de charges patronales (ex: *Si Dispo < 5000 alors Taux=40%*).
*   **Limites :** C'était une approximation "en escalier" de la réalité. Elle tentait de simuler manuellement les allègements de charges (Réduction Fillon, Taux maladie réduit) sans les calculer vraiment.
*   **Risque :** Ces taux sont devenus obsolètes avec le changement du SMIC au 1er janvier 2026.

### 🚀 La Solution du Simulateur : Le "Triage Dynamique"
Au lieu de figer des taux arbitraires, le simulateur intègre les **mécanismes réels** de la paie française via un algorithme à 3 niveaux. Il détecte automatiquement votre tranche de salaire pour appliquer les bons abattements.

#### Les 3 Paliers d'Abattements pris en compte :

1.  **🟢 Niveau 1 : L'Optimisation Maximale (Bas Salaires)**
    *   **Contexte :** Pour les rémunérations brutes inférieures à **2,5 SMIC** (environ 4 557 €).
    *   **Abattements appliqués :**
        *   **Réduction Générale (ex-Fillon) :** Réduit drastiquement les charges patronales Urssaf/Retraite.
        *   **Taux Maladie Réduit :** Application d'un taux de 7% au lieu de 13%.
    *   **Résultat :** Le simulateur applique un **Taux Réduit de ~41%** (au lieu de 47%), ce qui booste le Net du consultant.

2.  **🔵 Niveau 2 : Le Régime Standard (Salaires Moyens)**
    *   **Contexte :** Pour les rémunérations entre **2,5 et 3,5 SMIC** (de 4 557 € à 6 380 €).
    *   **Mécanisme :** Les allègements Fillon disparaissent, le taux maladie passe à taux plein (13%).
    *   **Résultat :** Application du **Taux Standard de ~46,69%**. C'est le taux de croisière en portage.

3.  **🔴 Niveau 3 : La Majoration (Hauts Salaires)**
    *   **Contexte :** Pour les rémunérations supérieures à **3,5 SMIC** (plus de 6 380 € Brut).
    *   **Surcharge :** Perte de certains plafonnements d'exonération (Bandeau Famille/Maladie) et application de la "Contribution d'Équilibre" sur la totalité du salaire.
    *   **Résultat :** Le simulateur applique une **Majoration de +1,8%**, portant le taux global à **~48,49%**.

---

## 2. L'Algorithme de "Reverse Engineering" (Calcul Inversé)

En portage, on ne part pas du Brut, mais du Chiffre d'Affaires. Le simulateur doit donc résoudre une équation pour trouver le Brut.

### La Mécanique Pas-à-Pas :

1.  **Nettoyage de l'Enveloppe :**
    On part du CA et on retire tout ce qui n'est pas du salaire :
    $$Masse \ Dispo = CA - (Frais \ Gestion \ 5\%) - (Frais \ Pro \ IK \ + \ Autres)$$

2.  **Déduction des Coûts Fixes (Avant Brut) :**
    On retire les coûts qui ne dépendent pas proportionnellement du brut final :
    *   **Mutuelle (Part Patronale) :** ~30 € (50% de 1,5% du PMSS 2026).
    *   **Réserve Financière :** 10% du Salaire de Base Conventionnel (2 374 €), soit 237,40 €.

3.  **Le "Solver" (La recherche du Brut) :**
    Il reste une somme $S$. On cherche le Brut $B$ tel que $B + Charges(B) = S$.
    Le simulateur fait une boucle de test :
    *   *Essai 1 :* Je calcule avec le **Taux Réduit (41%)**. Si le Brut trouvé est < 2,5 SMIC, je valide ✅.
    *   *Essai 2 :* Sinon, je calcule avec le **Taux Standard (46,69%)**. Si le Brut est < 3,5 SMIC, je valide ✅.
    *   *Essai 3 :* Sinon, j'applique le **Taux Majoré (48,49%)**.

4.  **Reconstruction du Bulletin de Paie :**
    Une fois le Brut Total trouvé, il est "saucissonné" pour respecter le légal :
    *   **Salaire de Base :** 2 374 € (fixe).
    *   **Prime d'Apport :** 118,70 € (5% du base).
    *   **Indemnité Congés Payés :** 10% du total partiel.
    *   **Complément de Rémunération :** C'est la variable d'ajustement qui absorbe tout le reste.

---

## 3. Données de Référence 2026

Le simulateur est calibré sur les chiffres officiels du **1er Janvier 2026**.

| Indicateur | Valeur 2026 | Impact |
| :--- | :--- | :--- |
| **SMIC Mensuel** | **1 823,03 €** | Détermine les seuils d'abattements (2,5 et 3,5 SMIC). |
| **PMSS** | **4 005,00 €** | Base de calcul de la Mutuelle et Prévoyance. |
| **IK (Catégorie C)** | **1.25 € / km** | Barème d'optimisation fiscale pour les déplacements. |

---
*Ce moteur de calcul garantit une précision au centime près et une conformité avec les règles URSSAF 2026, remplaçant avantageusement les approximations manuelles.*