# Rennes Traffic Debug

## Description

Cette application Flask permet de surveiller l’état du trafic routier de Rennes Métropole.  
Elle a été **corrigée, déboguée et instrumentée** dans le cadre de la *Story 4 du cas pratique E5*.

L’objectif est de mettre en place un dispositif complet de :

- monitorage applicatif
- journalisation des erreurs
- suivi des performances du modèle (MLOps)

---

## Technologies utilisées

- **Flask** : framework web
- **Flask-MonitoringDashboard** : monitoring applicatif
- **MLflow** : suivi des expériences et des métriques
- **logging (Python)** : journalisation des erreurs
- **Plotly** : visualisation des données

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/VOTRE_UTILISATEUR/rennes_traffic_debug.git
cd rennes_traffic_debug
```
### 2. Créer un environnement virtuel

```bash
python -m venv venv
```

Activation
- Windows (PowerShell)
```bash
.\venv\Scripts\Activate.ps1
```
- Linux / macOS
```bash
source venv/bin/activate
```
### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration

```bash
cp .env.example .env
```

### 5. Lancer l’application

```bash
python app.py
```

---
## Accès à l’application

- Application principale : http://127.0.0.1:5000
- Dashboard de monitoring : http://127.0.0.1:5000/dashboard
- Health check : http://127.0.0.1:5000/health
---
## Fonctionnalités
- Visualisation des points de trafic
- Prédiction de l’état du trafic en fonction de l’heure
- Monitoring des performances de l’application
- Journalisation des erreurs avec horodatage
- Suivi des expériences via MLflow
---
## Monitoring et MLOps

Dans une approche MLOps, plusieurs outils ont été intégrés :
- MLflow : suivi des métriques et des expériences
- Flask Monitoring Dashboard : surveillance des performances applicatives
- Logging Python : enregistrement des erreurs avec horodatage

Ces outils permettent :

- la détection automatique des incidents
- l’analyse des performances
- l’amélioration continue de l’application
---
## Bugs corrigés

Les principaux incidents identifiés et corrigés sont :

- Mauvais template home.html remplacé par index.html
- Appel incorrect de la fonction prediction_from_model
- Vecteur horaire incorrect (25 valeurs au lieu de 24)
- Erreur de syntaxe dans le filtrage pandas
- Mauvaise extraction des coordonnées (latitude / longitude)
- Correction d’une erreur HTML sur la balise <h4>
---
## Structure du projet
```bash
rennes_traffic_debug/
│
├── app.py
├── requirements.txt
├── src/
├── templates/
├── static/
└── logs/
```