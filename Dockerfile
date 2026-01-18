# Utiliser une image Python légère
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Exposer le port standard de Streamlit
EXPOSE 8501

# Commande de lancement
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
