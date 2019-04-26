# TODO:
# En fait c'est plus compliqué que ce que je pensais, car il faut savoir quoi correspond à la vitesse
# et quoi correspond au sens. La manière de régler ça via des paramètres dans le json de coûts n'est pas
# triviale, et pose problème notamment pour le sens inverse.


def build_lua(costs_config, output_cost_name):
    return costs_config

def _build_setup(turn_res, cost_type = 'duration'):
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
    process_node_string = (
        "function process_node (profile, node, result)\n"
        "\n"
        "end\n"
    )

    return process_node_string

def _build_process_way(costs_config, output_cost_name):

    process_way_string = (
        "function process_way (profile, way, result)\n"
        "\n"
        "    -- récupération des attributs utiles\n"
    )

    get_variables_strings = []
    speed_var_name = '0'
    for variable in costs_config["variables"]:
        var_str = "    local {} =  way:get_value_by_key(\"{}\")\n".format(variable["name"], variable["column_name"])
        get_variables_strings.append(var_str)
        if variable["isSpeed"]:
            speed_var_name = variable["name"]

    for string in get_variables_strings:
        process_way_string += string

    output_cost = None

    for output in costs_config["outputs"]:
        if output["name"] == output_cost_name:
            output_cost = output

    assert output_cost != None, "output cost name not in configuration outputs"

    process_way_string += "\n-- vitesse\n"
    process_way_string += "    result.forward_speed  = {}\n".format(speed_var_name)
    process_way_string += "    result.backward_speed = {}\n".format(speed_var_name)

    process_way_string += (
        "\n"
        "    -- gestion du sens direct\n"
        "    if sens >= 0 then\n"
        "        result.forward_mode  = mode.driving\n"
        "    else\n"
        "        result.forward_mode  = mode.inaccessible\n"
        "    end\n"
        "\n"
        "    -- gestion du sens inverse\n"
        "    if sens <= 0 then\n"
        "        result.backward_mode  = mode.driving\n"
        "    else\n"
        "        result.backward_mode  = mode.inaccessible\n"
        "    end\n"
        "\n"
        "end\n"
    )

    return process_way_string

def _build_return():
    return_string = (
        "return {\n"
        "  setup = setup,\n"
        "  process_way = process_way,\n"
        "  process_node = process_node\n"
        "}\n"
    )

    return return_string
