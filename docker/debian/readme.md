# R2GG sur Debian

Cette image permet d'avoir r2gg et donc de générer des données pour calculer des itinéraires. 

## Construction de l'image 

La construction de l'image est lancée avec une commande :  
```
docker build -t r2gg-debian -f docker/debian/Dockerfile .
```

## Utilisation de l'image 

DRAFT
- On lance l'image sans rien paramètrer et ça marche en prenant une petite donnée osm et en la convertissant (découverte)
- on peut préciser une donnée osm et ça marche (decouverte ++)
- comme aujourd'hui, on précise un fichier de conf et ça marche ( dev, tests) 
- on met un nouveau volume, on précise un fichier de conf qui pointe sur des fichier du volume et ça marche (petite prod)