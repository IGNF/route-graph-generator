# {{ title }} - Documentation

> **Description:** {{ description }}  
> **Auteur et contributeurs:** {{ author }}  
> **Version:** {{ version }}  
> **Code source:** {{ repo_url }}  
> **Dernière mise à jour de la documentation:** {{ date_update }}

## Présentation 

Route Graph Generator (r2gg) est un script Python qui permet la génération de graphes pour des moteurs de calcul d'itinéraire. Il a été développé pour générer les données directement utilisable par [Road2](https://github.com/IGNF/road2). 

Actuellement, il y a trois formats de sortie : OSRM, pgRouting et Valhalla. 

La conversion se fait via les fonctions de la bibliothèque r2gg développée dans ce but. Une documentation plus détaillée des fonctions de r2gg est consultable [ici](./usage/r2gg.md).

---

```{toctree}
---
caption: Route Graph Generator
---
R2GG <usage/r2gg>
Configuration <usage/configuration>
```

```{toctree}
---
caption: Utilisation avec Docker
---
Utiliser r2gg avec Docker <docker/readme>
R2GG sur Debian <docker/debian/readme>
```

```{toctree}
---
caption: SQL
---
Scripts SQL <sql/readme>
```

```{toctree}
---
caption: Développement
---
Documentation <development/documentation>
Changelog <development/history>
Contribuer <development/contributing>
Code de conduite <development/conduct>
```
