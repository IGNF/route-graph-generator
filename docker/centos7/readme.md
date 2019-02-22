# Dockerfile pour utiliser les scripts de génération sous CentOS

## Construction de l'image

Pour construire l'image, il suffit de lancer la commande suivante à la racine du projet :
```
docker build -t centos-r2gg -f docker/centos7/Dockerfile .
```
Les éléments suivants peuvent être spécifiés:
- Proxy :
```
docker build -t centos-r2gg --build-arg proxy=$proxy -f docker/centos7/Dockerfile .
```

## Lancer un script

Pour lancer un script, il faut le placer dans un volume qui sera monté sur le /home du container, en lançant par exemple la commande suivante :
```
docker run --name centos-r2gg-populate_pivot -v /path/to/config/file:/home -v /path/to/output/files:/home centos-r2g r2gg:populate_pivot config.json
```
