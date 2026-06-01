# Diagnostic E5 — Carte Rennes Traffic Debug

## Symptôme observé

La carte est affichée, mais elle donne l'impression d'être figée :

- l'utilisateur sélectionne une heure et lance une prédiction ;
- le résultat textuel change ;
- la carte ne donne pas d'impression de mise à jour métier ;
- les points affichent souvent `unknown` et `Inconnu`.

## Causes identifiées

1. **La prédiction ne pilotait pas la carte.**  
   La route `/predict` recalculait seulement le résultat textuel. La carte était reconstruite avec le même flux Rennes Métropole, sans rafraîchissement côté navigateur.

2. **La carte Plotly était rendue sans configuration explicite d'interactivité.**  
   Le rendu utilisait `Plotly.newPlot` sans `scrollZoom`, sans `responsive` et sans bouton de rafraîchissement asynchrone.

3. **L'extraction des champs de l'API était incomplète.**  
   Le code récupérait `trafficStatus`, mais n'exploitait pas correctement les identifiants de tronçons publiés par Rennes Métropole (`predefinedLocationRerefence` / `predefinedLocationReference`).

4. **Les erreurs API 400 étaient déjà visibles dans `logs/errors.log`.**  
   Le dépôt contenait des traces d'erreur pour des appels avec `limit=500` puis `limit=200`. La valeur a été bornée à 100 pour rester sûre avec l'API Explore v2.1.

## Correctifs appliqués

- ajout d'un endpoint `/api/traffic-map` ;
- rafraîchissement AJAX de la carte sans rechargement de page ;
- auto-refresh toutes les 3 minutes ;
- activation de `scrollZoom`, `responsive`, `dragmode='pan'` ;
- extraction robuste des champs `trafficStatus`, `geo_point_2d`, `geo_shape`, `predefinedLocationRerefence`, `datetime`, `averageVehicleSpeed`, `travelTime`, `travelTimeReliability` ;
- traduction des statuts en français : Fluide, Chargé, Congestionné, Impossible, Inconnu ;
- couleurs explicites par niveau de trafic ;
- cache local de secours si l'API externe est momentanément indisponible ;
- tests unitaires ajoutés pour valider l'extraction, la prédiction et la carte.

## Commandes de validation

```bash
python -m compileall app.py src tests
python -m pytest -q
python app.py
```

## Preuves matérielles recommandées pour le rapport E5

- capture de la carte avant correction : points `unknown`, impression de carte figée ;
- capture de `logs/errors.log` montrant les erreurs HTTP 400 ;
- capture du diff Git des fichiers modifiés ;
- capture de `/api/traffic-map` retournant le JSON de la carte ;
- capture de la carte après correction avec bouton `Rafraîchir` ;
- capture du dashboard Flask-MonitoringDashboard ;
- capture de MLflow avec les métriques `nb_points_loaded`, `response_time_index`, `response_time_predict` ;
- capture du résultat des tests `python -m pytest -q`.
