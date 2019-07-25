api_version = 4
function setup()
    return {
        properties = {
            use_turn_restrictions = true,
            weight_name = 'duration'
        }
     }
end
function process_node (profile, node, result)

end
function process_way (profile, way, result)

    -- récupération des attributs utiles
    local nature = tonumber(way:get_value_by_key("nature"))
    local length_m = tonumber(way:get_value_by_key("length_m"))
    local vitesse_voiture = tonumber(way:get_value_by_key("vitesse_moyenne_vl"))
    local sens = tonumber(way:get_value_by_key("direction"))
    local way_names = way:get_value_by_key("way_names")
    -- noms du troncon
    if way_names and way_names ~= '' then
        result.name = way_names
    end

    -- vitesse
    result.forward_speed  = vitesse_voiture
    result.backward_speed = vitesse_voiture

    -- gestion du sens direct
    if sens>=0 and vitesse_voiture>0 then
        result.forward_mode  = mode.driving
    else
        result.forward_mode  = mode.inaccessible
    end

    -- gestion du sens inverse
    if sens<=0 and vitesse_voiture>0 then
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
