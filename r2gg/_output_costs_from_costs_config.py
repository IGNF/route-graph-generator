from collections import defaultdict

def output_costs_from_costs_config(costs_config, row):
    """
    Fonction pour calculer les coûts associés à une arrête par rapport à la configuration des coûts

    Parameters
    ----------
    costs_config: dict
        défintion des coûts. objet correspondant au schéma JSON de configuration des coûts.
    row: dict
        ligne de la base de données correspondant à l'arrête sur laquelle calculer des coûts

    Returns
    -------
    tuple
        tuple des valeurs des coûts calculés pour row
    """

    values = {}
    output_costs = ()

    # Récupération des variables
    for variable in costs_config["variables"]:
        if variable["mapping"] == "value":
            values[variable["name"]] = row[variable["column_name"]]
        else:
            values[variable["name"]] = variable["mapping"][str(row[variable["column_name"]])]

    # Calcul des outputs
    for output in costs_config["outputs"]:
        result_direct = 0
        result_reverse = 0
        # Passage en defaultdict pour la gestion des champs facultatifs
        output = defaultdict(bool, output)
        if output["direct_conditions"]:
            if not _conditions_to_bool(output["direct_conditions"], values):
                result_direct = -1
        if output["reverse_conditions"]:
            if not _conditions_to_bool(output["reverse_conditions"], values):
                result_reverse = -1

        # Si les deux résultats sont à -1, inutile de faire l'opération
        if result_direct != -1 or result_reverse != -1:
            result = compute_operations(output["operations"], values)

            if result_direct != -1:
                result_direct = result

            if result_reverse != -1:
                result_reverse = result

        output_costs += (result_direct, result_reverse)

    return output_costs

def compute_operations(operations, values):
    """
    Calcule la valeur numérique du coût à partir des opérations définies dans la configuration

    Parameters
    ----------
    operations: array
        tableau comprenant des opérations, au format ["opération", valeur] avac valeur pouvant être
        dans values ou bien une valeur numérique
    values: dict
        Dictionnaire des valeurs de la configuration des coûts

    Returns
    -------
    float
        le résultat du calcul du coût
    """
    result = 0
    for operation in operations:
        if operation[0] == "add":
            if isinstance(operation[1], str):
                result += values[operation[1]]
            else:
                result += operation[1]
        elif operation[0] == "substract":
            if isinstance(operation[1], str):
                result -= values[operation[1]]
            else:
                result -= operation[1]
        elif operation[0] == "multiply":
            if isinstance(operation[1], str):
                result *= values[operation[1]]
            else:
                result *= operation[1]
        elif operation[0] == "divide":
            if isinstance(operation[1], str):
                result /= values[operation[1]]
            else:
                result /= operation[1]

    return result

def compute_operations_string(operations):
    """
    Génère la chaine de caractères correspondant au calcul des opérations
    Parameters
    ----------
    operations: array
        tableau comprenant des opérations, au format ["opération", valeur] avac valeur pouvant être
        Dictionnaire des valeurs de la configuration des coûts

    Returns
    -------
    string
        chaine de caractères correspondant au calcul des opérations
    """
    operation_str = "0";
    for operation in operations:
        if operation[0] == "add":
            operation_str += "+"
        elif operation[0] == "substract":
            operation_str += "-"
        elif operation[0] == "multiply":
            operation_str += "*"
        elif operation[0] == "divide":
            operation_str += "/"

        operation_str += str(operation[1])

    return operation_str


def _conditions_to_bool(conditions_str, values):
    """
    Fonction pour parser une chaîne de caractères correspondant à des conditions vers un booléen
    Se comporte comme un AND sur l'ensemble des conditions -> vrai si TOUT est vrai, false sinon

    Parameters
    ----------
    conditions_str: str
        chaine de caractère correspondant à toutes les conditions
    values: dict
        Dictionnaire des valeurs de la configuration des coûts

    Returns
    -------
    bool
        true si TOUTES les conditions sont vérifiée, false sinon
    """

    conditions = conditions_str.split(";")
    for condition in conditions:
        if not _condition_to_bool(condition, values):
            return False

    return True


def _condition_to_bool(condition, values):
    """
    Fonction pour parser une condition vers un booléen

    Parameters
    ----------
    condition: str
        chaine de caractère correspondant à 1 condition
    values: dict
        Dictionnaire des valeurs de la configuration des coûts

    Returns
    -------
    bool
        true si la condition est vérifiée, false sinon
    """

    # On teste 1 à 1 les différents tests possibles, en faisant bien attention à
    # tester ">=" avant ">" car le second est compris dans le premier (idem pour "<=")
    #
    # La conversion en float ne se fait qu'ici (dans les opérateurs > < >= <=) car on pourrait comparer des strings
    # avec == et !=
    test = condition.split("==")
    if len(test) == 2:
        return values[test[0]] == test[1].strip("'")

    test = condition.split("~=")
    if len(test) == 2:
        return values[test[0]] != test[1].strip("'")

    test = condition.split(">=")
    if len(test) == 2:
        return values[test[0]] >= float(test[1])

    test = condition.split("<=")
    if len(test) == 2:
        return values[test[0]] <= float(test[1])

    test = condition.split(">")
    if len(test) == 2:
        return values[test[0]] > float(test[1])

    test = condition.split("<")
    if len(test) == 2:
        return values[test[0]] < float(test[1])
