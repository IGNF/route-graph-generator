-- Premiere version d'un script LUA pour charger le routier de la BDUNIV2 dans OSRM

api_version = 4

function setup()
    return {
        properties = {
            use_turn_restrictions = false
        }
     }
end

function process_node (profile, node, result)

end

function process_way (profile, way, result)

    -- récupération des attributs utiles
    local way_names  = way:get_value_by_key("way_names")
    local direction    = tonumber(way:get_value_by_key("direction"))
    local nature  = way:get_value_by_key("nature")
    local vitesse_moyenne = way:get_value_by_key("vitesse_moyenne_vl")

    -- noms du troncon
    if way_names and way_names ~= "" then
        result.name = way_names
    end

    -- vitesse
    result.forward_speed  = vitesse_moyenne
    result.backward_speed = vitesse_moyenne

    -- gestion du sens direct
    if direction >= 0 then
        result.forward_mode  = mode.driving
    else
        result.forward_mode  = mode.inaccessible
    end

    -- gestion du sens inverse
    if direction <= 0 then
        result.backward_mode  = mode.driving
    else
        result.backward_mode  = mode.inaccessible
    end

end

return {
  setup = setup,
  process_way = process_way,
  process_node = process_node
}
