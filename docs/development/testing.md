# Tests

## Prérequis de l'environnement de test

- Docker >= 20.10
- Construction de l'image 

La construction de l'image est lancée avec une commande :  

```sh
docker build -t r2gg-debian -f docker/debian/Dockerfile .
```

## Initialisation de la base de données de tests

```sh
```
docker-compose -f tests/dev/docker-compose.dev.yml up -d
```

Mot de passe de l'utilisateur en base : `ign`

## Exécution des tests dans l'image docker

```sh
docker run -it -v $(pwd):/r2gg r2gg-debian bash
```

```sh
cd /r2gg
pip install -U -r requirements/testing.txt
pytest
```
