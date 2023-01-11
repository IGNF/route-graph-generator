# 2.0.0

FIX:
- Mauvaises configurations dans certains fichiers pour la partie docker

CHANGE:
- Ajout de 5 secondes en milieu urbain pour les données BDuni
- Modification de la version de notre fork valhalla

ADD:
- Ajout du fichier licence

UPDATE: 
- Mise à jour de la documentation des fichiers de génération
- Mise à jour des fichiers de génération dans la partie docker (wkt, renommage de fichiers, contraintes sur valhalla)

# 1.2.3

DEPS:
- Utilisation d'un fork de Valhalla pour avoir plus d'options (en attente de merge sur le projet initial)

# 1.2.1

UPDATE
- Passage à OSRM 5.26.0

# 1.2.0

CHANGE :
- suppression de la partie ssh
- modification des fichiers de configuration des générations
- renommage de r2gg-populate_pivot en r2gg-sql2pivot
- Ajout d'une commande pour générer la configuration de Road2 r2gg-road2config
- Gestion interne différente pour prendre en compte la nouvelle configuration de Road2 (gestion de sources et ressources différente)

# 1.1.2

FEATURES
- génération de données Valhalla
- possibilité d'utiliser des fichiers .osm.pbf pour osrm

# 1.1.1

FEATURES :
- génération à partir de données OSM dans l'image docker si aucun argument n'est fourni

# 1.1.0

FEATURES :
- génération des ressources smartpgr

CHANGE :
- refonte de la partie docker
- refactorisation de la partie OSRM
- mise à jour de la configuration docker pour Road2

FIX :
- diverses petites corrections dans le script sql et dans les scripts python
