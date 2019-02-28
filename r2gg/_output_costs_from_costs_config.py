from collections import defaultdict

def output_costs_from_costs_config(costs_config, row):
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
        result = 0
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
            for operation in output["operations"]:
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

            if result_direct != -1:
                result_direct = result

            if result_direct != -1:
                result_reverse = result

        output_costs += (result_direct, result_reverse)

    return output_costs

def _conditions_to_bool(conditions_str, values):
    """
    Fonction pour parser une chaîne de caractères correspondant à des conditions vers un booléen
    Se comporte comme un AND sue l'ensemble des conditions
    """
    conditions = conditions_str.split(";")
    for condition in conditions:
        if not _condition_to_bool(condition, values):
            return False

    return True


def _condition_to_bool(condition, values):
    """
    Fonction pour parser une condition vers un booléen
    """

    # On teste 1 à 1 les différents tests possibles, en faisant bien attention à
    # tester ">=" avant ">" car le second est compris dans le premier (idem pour "<=")
    #
    # La conversion en float ne se fait qu'ici (dans les opérateurs > < >= <=) car on pourrait comparer des strings
    # avec = et !=
    test = condition.split("==")
    if len(test) == 2:
        return values[test[0]] == test[1]
    test = condition.split(">=")
    if len(test) == 2:
        return values[test[0]] >= float(test[1])
    test = condition.split("<=")
    if len(test) == 2:
        return values[test[0]] <= float(test[1])
    test = condition.split("!=")
    if len(test) == 2:
        return values[test[0]] != test[1]
    test = condition.split(">")
    if len(test) == 2:
        return values[test[0]] > float(test[1])
    test = condition.split("<")
    if len(test) == 2:
        return values[test[0]] < float(test[1])
