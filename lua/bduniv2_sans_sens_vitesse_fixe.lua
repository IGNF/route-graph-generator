-- Premiere version d'un script LUA pour charger le routier de la BDUNIV2 dans OSRM

api_version = 4

function setup()
    return {
        properties = {
            use_turn_restrictions = true
        }
     }
end

function process_node (profile, node, result)

end

function process_way (profile, way, result)

    -- récupération des attributs utiles
    local cleabs  = way:get_value_by_key("cleabs")
    local nature  = way:get_value_by_key("nature")
    local vitesse_moyenne = way:get_value_by_key("vitesse_moyenne_vl")

    -- clé absolue du troncon
    if cleabs and cleabs ~= "" then
        result.name = cleabs
    end

    -- vitesse
    result.forward_speed  = vitesse_moyenne
    result.backward_speed = vitesse_moyenne

    -- sens
    result.forward_mode  = mode.driving
    result.backward_mode  = mode.driving

end

return {
  setup = setup,
  process_way = process_way,
  process_node = process_node
}
