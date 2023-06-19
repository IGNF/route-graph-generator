# CHANGELOG

## NEXT-VERSION

FIX:
- Durée de parcours incohérente sur OSRM entre car-fastest et car-shortest

## 2.2.1

CHANGED:
- reference de la doc à la branche master
- modification de la ci github pour prendre en compte la branche master
- suppression du déploiement de github pages lors d'un tag

ADDED:
- A code of conduct was adapted from the contributor covenant
- A contributing was added

## 2.2.0

FIX:
- pas d'exception si certains attributs non nécessaire ne sont pas présent dans le .json pour la création de configuration road2
- suppression d'attribut 'name' dans la configuration d'exemple

ADD:
- ajout d'un json-schema pour le fichier cost_calculations

## 2.1.0

FIX:
- Déconnexion de la base de données de travail après traitement

CHANGES:
- Pas de connexion à la base de travail si non utilisée

ADD:
- Ajout de la documentation sur GitHub Pages : https://ignf.github.io/route-graph-generator/
- Ajout de la publication de l'image docker sur le container GitHub : https://github.com/IGNF/route-graph-generator/pkgs/container/route-graph-generator
- Première livraison sur PyPi
- Ajout de tests de bout en bout avec pytest. Pour l'instant sql2pivot et pivot2osm sont testés.
- Ajout support des schémas d'entrée pour la conversion vers la base pivot
- Ajout d'un script pour la conversion d'une BDTOPO

UPDATE:
- Mise à jour version python en 3.10 dans l'image docker
- Mise à jour dockerfile pour meilleur gestion des requirements
- Mise à jour dockerfile pour utiliser la version bullseye de debian

## 2.0.0

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

## 1.2.3

DEPS:
- Utilisation d'un fork de Valhalla pour avoir plus d'options (en attente de merge sur le projet initial)

## 1.2.1

UPDATE
- Passage à OSRM 5.26.0

## 1.2.0

CHANGE :
- suppression de la partie ssh
- modification des fichiers de configuration des générations
- renommage de r2gg-populate_pivot en r2gg-sql2pivot
- Ajout d'une commande pour générer la configuration de Road2 r2gg-road2config
- Gestion interne différente pour prendre en compte la nouvelle configuration de Road2 (gestion de sources et ressources différente)

## 1.1.2

FEATURES
- génération de données Valhalla
- possibilité d'utiliser des fichiers .osm.pbf pour osrm

## 1.1.1

FEATURES :
- génération à partir de données OSM dans l'image docker si aucun argument n'est fourni

## 1.1.0

FEATURES :
- génération des ressources smartpgr

CHANGE :
- refonte de la partie docker
- refactorisation de la partie OSRM
- mise à jour de la configuration docker pour Road2

FIX :
- diverses petites corrections dans le script sql et dans les scripts python
