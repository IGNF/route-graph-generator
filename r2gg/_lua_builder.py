from r2gg._output_costs_from_costs_config import compute_operations_string

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

    result = "api_version = 4\n"

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

    result += _build_process_node()
    result += _build_process_way(costs_config, output_cost)
    result += _build_return()
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
    # Demi-tour aux wapoints si pas de turn restriction (cf #37043)
    if (not turn_res):
        setup_string += "            continue_straight_at_waypoint = false,\n"
    setup_string += "            weight_name = \'" + cost_type + "\',\n"
    setup_string += "        },\n"
    setup_string += "        classes = { \"toll\", \"bridge\", \"tunnel\" },\n"
    setup_string += "        excludable = {\n"
    setup_string += "            { [\"toll\"] = true },\n"
    setup_string += "            { [\"bridge\"] = true },\n"
    setup_string += "            { [\"tunnel\"] = true },\n"
    setup_string += "            { [\"toll\"] = true, [\"bridge\"] = true },\n"
    setup_string += "            { [\"toll\"] = true, [\"tunnel\"] = true },\n"
    setup_string += "            { [\"bridge\"] = true, [\"tunnel\"] = true },\n"
    setup_string += "            { [\"toll\"] = true, [\"bridge\"] = true, [\"tunnel\"] = true }\n"
    setup_string += "        }\n"
    setup_string += "    }\n"
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
        if variable["mapping"] == "value":
            var_str = "    local {0} = tonumber(way:get_value_by_key(\"{1}\")) or way:get_value_by_key(\"{1}\")\n".format(variable["name"], variable["column_name"])
            get_variables_strings.append(var_str)
        else:
            temp_var_str  = "    local {0}_tmp = tonumber(way:get_value_by_key(\"{1}\")) or way:get_value_by_key(\"{1}\")\n".format(variable["name"], variable["column_name"])
            local_var_str = "    local {}\n".format(variable["name"])
            get_variables_strings.append(temp_var_str)
            get_variables_strings.append(local_var_str)
            for key, value in variable["mapping"].items():
                cond_str = "    if {}_tmp == \"{}\" then\n".format(variable["name"], key)
                var_str  = "        {0} = tonumber(\"{1}\") or \"{1}\"\n".format(variable["name"], value)
                var_str += "    end\n"
                get_variables_strings.append(cond_str)
                get_variables_strings.append(var_str)

    # Récupération des attributs nécéssaires à la gestion des péages, ponts et tunnels.
    get_variables_strings.append("    local acces_vehicule_leger = way:get_value_by_key(\"acces_vehicule_leger\")\n")
    get_variables_strings.append("    local position_par_rapport_au_sol = tonumber(way:get_value_by_key(\"position_par_rapport_au_sol\"))\n")

    for string in get_variables_strings:
        process_way_string += string

    # pour le nom
    process_way_string += "    local way_names = way:get_value_by_key(\"way_names\")\n"

    process_way_string += (
        "    -- noms du troncon\n"
        "    if way_names and way_names ~= '' then\n"
        "        result.name = way_names\n"
        "    end\n"
    )

    # vitesse
    process_way_string += "\n    -- vitesse\n"
    process_way_string += "    result.forward_speed  = {}\n".format(output_cost["speed_value"])
    process_way_string += "    result.backward_speed = {}\n".format(output_cost["speed_value"])
    process_way_string += "\n"

    # durée
    process_way_string += "\n    -- durée\n"
    process_way_string += "    result.duration  = {}\n".format(compute_operations_string(output_cost["operations"]))
    process_way_string += "\n"

    # gestion du sens direct
    process_way_string += "    -- gestion du sens direct\n"

    direct_conditions_str = "true"
    if output_cost["direct_conditions"]:
        direct_conditions_array = output_cost["direct_conditions"].split(";")
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
        reverse_conditions_array = output_cost["reverse_conditions"].split(";")
        reverse_conditions_str = " and ".join(reverse_conditions_array)

    process_way_string += "    if {} then\n".format(reverse_conditions_str)
    process_way_string += "        result.backward_mode  = mode.driving\n"
    # si le coût est de type distance, il faut rajouter l'attribut rate
    if output_cost["cost_type"] == 'distance':
        process_way_string += "        result.backward_rate  = 1\n"
    process_way_string += "    else\n"
    process_way_string += "        result.backward_mode  = mode.inaccessible\n"
    process_way_string += "    end\n"
    process_way_string += "\n"

    # Gestion des pếages.
    process_way_string += "    -- Gestion des pếages.\n"
    process_way_string += "    if acces_vehicule_leger == 'A péage' then\n"
    process_way_string += "        result.forward_classes[\"toll\"] = true\n"
    process_way_string += "        result.backward_classes[\"toll\"] = true\n"
    process_way_string += "    end\n"
    process_way_string += "\n"

    # Gestion des ponts.
    process_way_string += "    -- Gestion des ponts.\n"
    process_way_string += "    if position_par_rapport_au_sol and position_par_rapport_au_sol > 0 then\n"
    process_way_string += "        result.forward_classes[\"bridge\"] = true\n"
    process_way_string += "        result.backward_classes[\"bridge\"] = true\n"
    process_way_string += "    end\n"
    process_way_string += "\n"

    # Gestion des tunnels.
    process_way_string += "    -- Gestion des tunnels.\n"
    process_way_string += "    if position_par_rapport_au_sol and position_par_rapport_au_sol < 0 then\n"
    process_way_string += "        result.forward_classes[\"tunnel\"] = true\n"
    process_way_string += "        result.backward_classes[\"tunnel\"] = true\n"
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
