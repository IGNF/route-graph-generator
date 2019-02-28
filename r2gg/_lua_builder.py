# TODO:
# En fait c'est plus compliqué que ce que je pensais, car il faut savoir quoi correspond à la vitesse
# et quoi correspond au sens. La manière de régler ça via des paramètres dans le json de coûts n'est pas
# triviale, et pose problème notamment pour le sens inverse.


def build_lua(costs_config):
    return lua_string

def _build_setup(turn_res):
    setup_string = "function setup()\n"
    setup_string += "    return {\n"
    setup_string += "        properties = {\n"
    setup_string += "            use_turn_restrictions = " + str(turn_res).lower() + "\n"
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

def _build_process_way(costs_config):
    process_way_string = (
        "function process_way (profile, way, result)\n"
        "\n"
        "    -- récupération des attributs utiles\n"
        "    local cleabs  = way:get_value_by_key(\"cleabs\")\n"
        "    local direction    = tonumber(way:get_value_by_key(\"direction\"))\n"
        "    local nature  = way:get_value_by_key(\"nature\")\n"
        "    local vitesse_moyenne = way:get_value_by_key(\"vitesse_moyenne_vl\")\n"
        "\n"
        "    -- clé absolue du troncon\n"
        "    if cleabs and cleabs ~= "" then\n"
        "        result.name = cleabs\n"
        "    end\n"
        "\n"
        "    -- vitesse\n"
        "    result.forward_speed  = vitesse_moyenne\n"
        "    result.backward_speed = vitesse_moyenne\n"
        "\n"
        "    -- gestion du sens direct\n"
        "    if direction >= 0 then\n"
        "        result.forward_mode  = mode.driving\n"
        "    else\n"
        "        result.forward_mode  = mode.inaccessible\n"
        "    end\n"
        "\n"
        "    -- gestion du sens inverse\n"
        "    if direction <= 0 then\n"
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
