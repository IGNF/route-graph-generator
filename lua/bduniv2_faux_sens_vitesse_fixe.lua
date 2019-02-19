

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
    local sens    = way:get_value_by_key("sens_de_circulation")
    local nature  = way:get_value_by_key("nature")
    local vitesse_moyenne = way:get_value_by_key("vitesse_moyenne_vl")

    -- clé absolue du troncon
    if cleabs and cleabs ~= "" then
        result.name = cleabs
    end

    -- vitesse
    result.forward_speed  = vitesse_moyenne
    result.backward_speed = vitesse_moyenne

    -- gestion du sens direct A L'ENVERS
    if sens == "Sens direct" or sens == "Double sens" or sens == "Sans objet" then
        -- result.forward_mode  = mode.driving
	result.backward_mode  = mode.driving
    else
       -- result.forward_mode  = mode.inaccessible
       result.backward_mode  = mode.inaccessible
    end

    -- gestion du sens inverse A L'ENVERS
    if sens == "Sens inverse" or sens == "Double sens" or sens == "Sans objet" then
        -- result.backward_mode  = mode.driving
         result.forward_mode  = mode.driving
    else
        -- result.backward_mode  = mode.inaccessible
	result.forward_mode = inaccessible
    end

end

return {
  setup = setup,
  process_way = process_way,
  process_node = process_node
}
