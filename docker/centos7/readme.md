# Dockerfile pour utiliser Road2 sous CentOS


# Construction de l'image

Pour construire l'image, il suffit de lancer la commande suivante à la racine du projet Road2:
```
docker build -t centos-python3 -f docker/centos/Dockerfile .
```

Les éléments suivants peuvent être spécifiés:
- Proxy

```
docker build -t centos-python3 --build-arg proxy=$proxy -f docker/centos/Dockerfile .
```

# Lancer un script

Pour lancer un script, il faut le placer dans un volume qui sera monté sur le /home du container, en lançant par exemple la commande suivante:
```
docker run --name centos-mon_script -v /home/myname/python_scripts:/home centos-python3 mon_script.py [arguments éventuels]
```
