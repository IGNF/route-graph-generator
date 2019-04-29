def build_lua(costs_config, output_cost_name):
    """
    Fonction qui crée un fichier .lua de profil OSRM à partir d'un dictionnaire de
    définition des coûts (costs_config) et d'un nom de coût spécifique
    (output_cost_name) qui doît être présent dans la valeur associée à la clé
    outputs de costs_config.

    Parameters
    ----------
    costs_config: dict
        Dictionnaire de configuration des coûts correspondant au schéma JSON de
        configuration des coûts
    output_cost_name: str
        Nom de coût spécifique qui doît être présent dans la valeur associée à
        la clé outputs de costs_config.

    Returns
    -------
    str
        chaîne de caractères correspondant à un fichier .lua de profil OSRM pour
        le coût spécifié
    """

    result = ""

    output_cost = None
    for output in costs_config["outputs"]:
        if output["name"] == output_cost_name:
            output_cost = output

    assert output_cost != None, "output cost name not in configuration outputs"

    if output_cost["cost_type"]:
        result += _build_setup(bool(output_cost["turn_restrictions"]),
                               output_cost["cost_type"])
    else:
        result += _build_setup(bool(output_cost["turn_restrictions"]))

    result += _build_process_node
    result += _build_process_way
    result += _build_return
    return result


def _build_setup(turn_res, cost_type = 'duration'):
    """
    Fonction de construction de la fonction setup du fichier .lua

    Parameters
    ----------
    turn_res: bool
        true si on utilise les non_communications, false sinon
    cost_type: str
        type de coût comme défini dans la documentation des profils .lua OSRM
        pour l'instant, parmi {'duration', 'distance'}

    Returns
    -------
    str
        chaîne de caractères correspondant à la fonction setup du fichier .lua
    """

    setup_string = "function setup()\n"
    setup_string += "    return {\n"
    setup_string += "        properties = {\n"
    setup_string += "            use_turn_restrictions = " + str(turn_res).lower() + ",\n"
    setup_string += "            weight_name = \'" + cost_type + "\'\n"
    setup_string += "        }\n"
    setup_string += "     }\n"
    setup_string += "end\n"

    return setup_string

def _build_process_node():
    """
    Fonction de construction de la fonction process_node du fichier .lua
    pour l'instant, elle est vide

    Returns
    -------
    str
        chaîne de caractères correspondant à la fonction process_node du fichier .lua
        pour l'instant, elle est vide
    """

    process_node_string = (
        "function process_node (profile, node, result)\n"
        "\n"
        "end\n"
    )

    return process_node_string

def _build_process_way(costs_config, output_cost):
    """
    Fonction de construction de la fonction process_way du fichier .lua

    Parameters
    ----------
    costs_config: dict
        Dictionnaire de configuration des coûts correspondant au schéma JSON de
        configuration des coûts
    output_cost: dict
        Dictionnaire de la configuration du coût dont le nom est output_cost_name

    Returns
    -------
    str
        chaîne de caractères correspondant à la fonction process_way du fichier .lua
    """

    process_way_string = (
        "function process_way (profile, way, result)\n"
        "\n"
        "    -- récupération des attributs utiles\n"
    )

    # récupération des attributs utiles
    get_variables_strings = []
    for variable in costs_config["variables"]:
        var_str = "    local {} =  way:get_value_by_key(\"{}\")\n".format(variable["name"], variable["column_name"])
        get_variables_strings.append(var_str)

    for string in get_variables_strings:
        process_way_string += string

    # vitesse
    process_way_string += "\n-- vitesse\n"
    process_way_string += "    result.forward_speed  = {}\n".format(output_cost["speed_value"])
    process_way_string += "    result.backward_speed = {}\n".format(output_cost["speed_value"])
    process_way_string += "\n"

    # gestion du sens direct
    process_way_string += "    -- gestion du sens direct\n"

    direct_conditions_str = "true"
    if output_cost["direct_conditions"]:
        direct_conditions_array = output_cost["direct_conditions"].split(",")
        direct_conditions_str = " and ".join(direct_conditions_array)

    process_way_string += "    if {} then\n".format(direct_conditions_str)
    process_way_string += "        result.forward_mode  = mode.driving\n"
    # si le coût est de type distance, il faut rajouter l'attribut rate
    if output_cost["cost_type"] == 'distance':
        process_way_string += "        result.forward_rate  = 1\n"
    process_way_string += "    else\n"
    process_way_string += "        result.forward_mode  = mode.inaccessible\n"
    process_way_string += "    end\n"
    process_way_string += "\n"

    # gestion du sens inverse
    process_way_string += "    -- gestion du sens inverse\n"

    reverse_conditions_str = "true"
    if output_cost["reverse_conditions"]:
        reverse_conditions_array = output_cost["reverse_conditions"].split(",")
        reverse_conditions_str = " and ".join(reverse_conditions_array)

    process_way_string += "    if {} then\n".format(reverse_conditions_str)
    process_way_string += "        result.backward_mode  = mode.driving\n"
    # si le coût est de type distance, il faut rajouter l'attribut rate
    if output_cost["cost_type"] == 'distance':
        process_way_string += "        result.backward_rateforward_rate  = 1\n"
    process_way_string += "    else\n"
    process_way_string += "        result.backward_mode  = mode.inaccessible\n"
    process_way_string += "    end\n"
    process_way_string += "\n"
    process_way_string += "end\n"

    return process_way_string

def _build_return():
    """
    Fonction de construction de la fonction return du fichier .lua

    Returns
    -------
    str
        chaîne de caractères correspondant à la fonction return du fichier .lua
    """

    return_string = (
        "return {\n"
        "  setup = setup,\n"
        "  process_way = process_way,\n"
        "  process_node = process_node\n"
        "}\n"
    )
    return return_string
