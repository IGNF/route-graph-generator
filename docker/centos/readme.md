# Dockerfile pour utiliser les scripts de génération sous CentOS

## Construction de l'image

Pour construire l'image, il suffit de lancer la commande suivante à la racine du projet :
```
docker build -t r2gg-centos -f docker/centos/Dockerfile .
```

## Lancer un script

Pour lancer un script, il est préférable de lui associer un volume sur `/home/docker/data` afin de récupérer le résultat. 