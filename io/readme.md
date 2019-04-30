# Fichiers de configuration de route-graph-generator

## Fichier principal
Ce fichier de configuration est conséquent, pour le comprendre il est conseillé de lire ses spécifications et ses exemples.

### Exemple
Plusieurs exemples sont présents dans le dossier io.

## Configuration des logs
#### Attribut "level"
Niveau d'importance des logs à enregistrer. Doit avoir comme valeur l'un de `CRITICAL` `ERROR` `WARNING` `INFO` `DEBUG`.

#### Attribut "filename"
Fichier où enregistrer les logs. Chemin absolu conseillé.

#### Exemple
```json
{
	"level": "DEBUG",
	"filename": "r2gg.log"
}
```

## Configuration des bases de données
#### Attribut "host"
Adresse du serveur de base de données.

#### Attribut "dbname"
Nom de la base de données concernée.

#### Attribut "username"
Nom d'utilisateur.

#### Attribut "password"
Mot de passe

#### Exemple
```json
{
	"host": "host",
	"dbname": "roads",
	"username": "user",
	"password": "pass"
}
```

## Configuration des coûts
Afin de configurer les coûts pour pgRouting, et désormais également pour OSRM, il a été défini un format statique basé sur du JSON permettant de réaliser le calcul de ces coûts
### Attribut "variables"
Il s'agit d'une liste de "variables", c'est-à-dire de valeurs qui sont utilisées pour le calcul des coûts, définies à partir de colonnes de la table en entrée.
Chaque élément de la liste a plusieurs attributs :

#### Attribut "name"
Nom de la varaible, permettant de l'identifier dans le calcul des coûts.

#### Attribut "column_name"
Nom de la colonne dans la base en entrée correspondant à la valeur.

#### Attribut "mapping"
Valeur que doit prendre la varaible en fonction de la valeur retournée par le SQL. Il s'agit soit de la chaîne de caractère `"value"`, soit d'un objet JSON. Dans le premier cas, la valeur de la variable est la valeur retournée par l'instruction SQL. Dans le second cas, il est défini un mapping valeur SQL vers valeur de la variable. Par exemple :
```json
"mapping": {
    "douze": 12,
    "treize": 13,
    "zéro": 0
 }
```
Ce mapping permet de traduire une valeur en lettres en SLQ en une valeur chiffrée pour la varaible. Le mapping devra comporter toutes les valeurs pouvant être prise par le résultat de la requête SQL.

### Attribut "outputs"
Il s'agit d'une liste d'"outputs", c'est-à-dire des colonnes dans la table de sortie qui correspondront à des coûts. Chaque élément de la lite a plusieurs attributs.
#### Attribut "name"
Nom de la colonne de coûts résultante.

#### Attribut "speed_value"
Nom de la varaible correspondant à la vitesse de ce coût OU valeur numérique

#### Attributs "direct_conditions" et "reverse_conditions"
Chaînes de caractères définissant des conditions toutes nécessaires pour la circulabilité des tronçons, séparés par des points-virgules `;`.
Si toutes les conditions ne sont pas vérifiées, le tronçon n'est pas praticable.
Si aucune condition n'est spécifiée, le tronçon est praticable.

L'attribut `direct_condition` correspond au sens direct de parcours du graphe, l'attribut `reverse_condition` correspond au sens inverse de parcours du graphe.

##### Exemple
```json
"direct_condition": "sens>=0;vitesse>0",
"reverse_condition": "sens<=0;vitesse>0"
```

#### Attribut "turn_restrictions"
Booléen, indique s'il faut prendre en compte les restrictions de virage (non_communication dans la bd uni) pour le calcul d'itinéraire

#### Attribut "cost_type"
Type du coût (OSRM). Pour l'instant, parmi {'distance', 'duration'}

#### Attribut "operations"
Il s'agit d'une liste d'opérations à réaliser pour obtenir le coût. Les opérations sont réalisées dans l'odre de la liste, à partir du nombre 0 (la première opération est donc toujours une addition ou une soustraction).

Les opérations sont des lites de 2 éléments. Le premier est une chaîne de caractères parmi `"add"` `"substract"` `"multiply"` et `"divide"`, et le scond est soit une chaîne de caractère, soint un nombre. Dans le premiers cas, la chaîne de caractères est le nom d'une variable. __Attention aux divisions par zéro.__

##### Exemple d'operations - calcul du temps en fonction de la longueur et de la vitesse :
```json
"operations": [
    ["add", "length_m"],
    ["divide", "vitesse_voiture"],
    ["multiply", 3.6]
]
```

### Exemple
Un exemple complet est présent dans le dossier [io](./costs_calculation_sample.json).

## Configuration des profils (OSRM)
La configuration des profils OSRM se fait _via_ des fonctions écrites en LUA. Se référer à la [documentation officielle](https://github.com/Project-OSRM/osrm-backend/blob/master/docs/profiles.md).

#### Exemple
Des exemples complets sont présents dans le dossier [lua](../lua).
