# 📘 Méthodologie et Algorithmes de Calcul (Version 2026)

Ce document détaille les formules mathématiques et logiques utilisées par le **Simulateur de Portage Salarial 2026**.

## 1. Principe Général : Le "Reverse Engineering"

Le simulateur utilise un algorithme de résolution pour déterminer le salaire Brut maximum à partir du Chiffre d'Affaires.

$$Salaire \ Brut = \frac{Masse \ Disponible - Réserve - Mutuelle (Part \ Pat)}{1 + Taux \ Charges \ Patronales}$$

---

## 2. Détail des Variables et Seuils 2026

### A. Le SMIC (Base de référence)
La valeur utilisée est celle en vigueur au **1er Janvier 2026**.
*   **Montant Brut Mensuel :** 1 823,03 €
*   *Note : Revalorisation annuelle au 1er janvier.*

### B. Le PMSS (Plafond Mensuel de la Sécurité Sociale)
*   **Valeur 2026 :** 4 005,00 €
*   *Utilisé pour le calcul de la mutuelle et de certaines cotisations.*

### C. Les Indemnités Kilométriques (IK)
*   **Formule :** $$Distance \ (km) \ \times 1.25 \ €$$
*   **Impact :** Optimisation fiscale via remboursement de frais non chargés.

---

## 3. Gestion des Charges Patronales (Paliers 2026)

| Scénario | Condition (Salaire Brut) | Taux Patronal Appliqué |
| :--- | :--- | :--- |
| **🟢 Taux Réduit** | < 2,5 SMIC (~4 557 €) | **~41,00 %** |
| **🔵 Taux Standard** | Entre 2,5 et 3,5 SMIC | **~46,69 %** |
| **🔴 Taux Majoré** | > 3,5 SMIC (~6 380 €) | **Standard + 1,8%** |

---
*Document mis à jour le 18 Janvier 2026.*
