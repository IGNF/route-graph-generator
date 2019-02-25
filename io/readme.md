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

## Configuration des coûts (pgRouting)
Afin de configurer les coûts pour pgRouting, il a été défini un format statique basé sur du JSON permettant de réaliser le calcul de ces coûts
### Attribut "variables"
Il s'agit d'une liste de "variables", c'est-à-dire de valeurs qui sont utilisées pour le calcul des coûts, définies à partir de colonnes de la table en entrée.
Chaque élément de la liste a plusieurs attributs :

#### Attribut "name"
Nom de la varaible, permettant de l'identifier dans le calcul des coûts.

#### Attribut "select_operation"
Opération SQL pour sélectionner la valeur dans la table en entrée. Il s'agit de ce qui suit le mot clef SQL `SELECT`. Lorsqu'il s'agit simplement de récupérer la valeur de la colonne, il s'agit du nom de la colonne. Il est conseillé pour les opérations plus complexes de donner un alias à la valeur, avec l'instruction `as value_name` à la fin de l'opération.

#### Attribut "value_name"
Nom de la valeur retournée par la sélection SQL. Losque la valeur de `select_operation` est le nom d'une colonne, `value_name` a la même valeur. Si la `select_operation` est plus complexe, `value_name` est l'alias donné à la valeur retournée.

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

#### Attribut "negative_if_zero" (facultatif)
Attribut booléen. Si `true`, rend le coût négatif si la valeur de la variable est nulle. En effet, les coûts nuls dans pgRouting correspondent à des imposibilité de passage. Cet attribut est notamment utile pour les vitesses : en effet, si la vitesse est nulle, on voudra avoit un coût négatif pour exclure le tronçon.

### Attribut "outputs"
Il s'agit d'une liste d'"outputs", c'est-à-dire des colonnes dans la table de sortie qui correspondront à des coûts. Chaque élément de la lite a plusieurs attributs.
#### Attribut "name"
Nom de la colonne de coûts résultante.

#### Attribut "negative_flags"
Liste de noms de variables (qui doivent donc correspondre aux attributs `name` des varaibles en question), qui sont potentiellement négatives. Cette liste permet d'obtenir des coûts négatifs et ainsi d'exclure des tronçons.

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
