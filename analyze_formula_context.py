import pandas as pd
import openpyxl

file_path = 'Simulation Annuelle Temps Complet 2025 - Modifiée.xlsx'
sheet_name = 'a remplir'

try:
    # Lire la feuille sans header pour avoir les coordonnées exactes
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    
    # On regarde autour de la ligne 35 à 50, colonnes C (index 2) à N (index 13)
    # Attention pandas est 0-indexed, Excel est 1-indexed.
    # Ligne 35 excel = index 34
    
    subset = df.iloc[34:60, [2, 7, 13]] # Colonnes C, H, N
    print("--- Contenu des cellules référencées par la formule ---")
    print("Col C (Seuils) | Col H (Taux ?) | Col N (Calcul)")
    print(subset.to_string())
    
except Exception as e:
    print(e)
