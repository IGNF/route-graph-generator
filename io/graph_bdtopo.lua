way_type = {
["no_pedestrian"] =  {["auto_forward"] = "true", ["pedestrian_forward"] = "false"},
["regular"] =        {["auto_forward"] = "true", ["pedestrian_forward"] = "true"},
["no_car"] =         {["auto_forward"] = "false", ["pedestrian_forward"] = "true"}
}

restriction = {
["no_left_turn"] = 0,
["no_right_turn"] = 1,
["no_straight_on"] = 2,
["no_u_turn"] = 3,
["only_right_turn"] = 4,
["only_left_turn"] = 5,
["only_straight_on"] = 6,
["no_entry"] = 7,
["no_exit"] = 8,
["no_turn"] = 9
}

function round(val, n)
  if (n) then
    return math.floor( (val * 10^n) + 0.5) / (10^n)
  else
    return math.floor(val+0.5)
  end
end

function restriction_prefix(restriction_str)
  --not a string
  if restriction_str == nil then
    return nil
  end

  --find where the restriction type ends.
  --format looks like
  --restriction:conditional=no_left_turn @ (07:00-09:00,15:30-17:30)
  local index = 0
  local found = false
  for c in restriction_str:gmatch"." do
    if c == "@" then
      found = true
      break
    end
    if c ~= " " then
      index = index + 1
    end
  end

  --@ symbol did not exist
  if found == false then
    return nil
  end

  --return the type of restriction
  return restriction_str:sub(0, index)
end

function restriction_suffix(restriction_str)
  --not a string
  if restriction_str == nil then
    return nil
  end

  --find where the restriction type ends.
  --format looks like
  --restriction:conditional=no_left_turn @ (07:00-09:00,15:30-17:30)
  local index = 0
  local found = false
  for c in restriction_str:gmatch"." do

    if found == true then
      if c ~= " " then
        index = index + 1
        break
      end
    elseif c == "@" then
      found = true
    end
    index = index + 1
  end

  --@ symbol did not exist
  if found == false then
    return nil
  end

  --return the date and time information for the restriction
  return restriction_str:sub(index, string.len(restriction_str))
end


--convert the numeric (non negative) number portion at the beginning of the string
function numeric_prefix(num_str, allow_decimals)
  --not a string
  if num_str == nil then
    return nil
  end

  --find where the numbers stop
  local index = 0
  -- flag to say if we've seen a decimal dot already. we shouldn't allow two,
  -- otherwise the call to tonumber() might fail.
  local seen_dot = false
  for c in num_str:gmatch"." do
    if tonumber(c) == nil then
      if c == "." then
        if allow_decimals == false or seen_dot then
           break
        end
        seen_dot = true
      else
        break
      end
    end
    index = index + 1
  end

  --there weren't any numbers
  if index == 0 then
    return nil
  end

  --Returns the substring that's numeric at the start of num_str
  return num_str:sub(0, index)
end

--normalize a speed value
function normalize_speed(speed)
  --grab the number prefix
  local num = tonumber(numeric_prefix(speed, false))

  --check if the rest of the string ends in "mph" convert to kph
  if num then
    if speed:sub(-3) == "mph" then
      num = round(num * 1.609344)
    end

    --if num > 150kph or num < 10kph....toss
    if num > 150 or num < 10 then
      return nil
    end
  end

  return num
end


--returns 1 if you should filter this way 0 otherwise
function filter_tags_generic(kv)

  --figure out what basic type of road it is
  local forward = way_type["regular"]
  if (tonumber(kv["vitesse_moyenne_vl"]) <= 0) then
    forward = way_type["no_car"]
  elseif (kv["nature"] == "Type autoroutier" or kv["nature"] == "Bretelle") then
    forward = way_type["no_pedestrian"]
  end

  local access = "true"

  kv["emergency_forward"] = "false"
  kv["emergency_backward"] = "false"

  if forward then
    for k,v in pairs(forward) do
      kv[k] = v
    end
  end

  --check the oneway-ness and traversability against the direction of the geom
  kv["pedestrian_backward"] = kv["pedestrian_forward"]

  if (kv["direction"] ~= "0") then
    oneway_norm = "true"
  else
    oneway_norm = "false"
  end

  kv["oneway"] = oneway_norm

  if (tonumber(kv["direction"]) <= 0) then
    kv["auto_backward"] = "true"
  else
    kv["auto_backward"] = "false"
  end
  if (tonumber(kv["direction"]) >= 0) then
    kv["auto_forward"] = "true"
  else
    kv["auto_forward"] = "false"
  end

  kv["use"] = 0

  kv["road_class"] = tonumber(kv["importance"]) - 1

  local r_shoulder = nil
  local l_shoulder = r_shoulder

  kv["shoulder_right"] = r_shoulder
  kv["shoulder_left"] = l_shoulder


  local cycle_lane_right_opposite = "false"
  local cycle_lane_left_opposite = "false"

  local cycle_lane_right = 0
  local cycle_lane_left = 0

  kv["cycle_lane_right"] = cycle_lane_right
  kv["cycle_lane_left"] = cycle_lane_left

  kv["cycle_lane_right_opposite"] = cycle_lane_right
  kv["cycle_lane_left_opposite"] = cycle_lane_left

  local highway_type = kv["highway"]
  if kv["highway"] == "construction" then
    highway_type = kv["construction"]
  end

  kv["link"] = "false"

  kv["private"] = "false"
  kv["no_thru_traffic"] = "false"
  kv["ferry"] = "false"
  kv["rail"] = "false"
  kv["name"] = kv["way_names"]
  kv["name:en"] = kv["name:en"]
  kv["alt_name"] = kv["alt_name"]
  kv["official_name"] = kv["official_name"]

  kv["max_speed"] = kv["vitesse_moyenne_vl"]

  kv["advisory_speed"] = normalize_speed(kv["vitesse_moyenne_vl"])
  kv["average_speed"] = normalize_speed(kv["vitesse_moyenne_vl"])
  if (tonumber(kv["direction"]) <= 0) then
    kv["backward_speed"] = normalize_speed(kv["vitesse_moyenne_vl"])
  else
    kv["backward_speed"] = normalize_speed("0")
  end
  if (tonumber(kv["direction"]) >= 0) then
    kv["forward_speed"] = normalize_speed(kv["vitesse_moyenne_vl"])
  else
    kv["forward_speed"] = normalize_speed("0")
  end

  kv["default_speed"] = normalize_speed(kv["vitesse_moyenne_vl"])

  if tonumber(kv["vitesse_moyenne_vl"]) <= 0 then
    kv["auto_backward"] = "false"
    kv["auto_forward"] = "false"
  end

  kv["int"] = kv["int"]
  kv["int_ref"] = kv["int_ref"]
  kv["surface"] = kv["surface"]
  kv["wheelchair"] = kv["wheelchair"]

  if (tonumber(kv["nombre_de_voies"])) then
    lane_count = kv["nombre_de_voies"]
  else
    lane_count = nil
  end

  kv["lanes"] = lane_count

  kv["forward_lanes"] = nil
  kv["backward_lanes"] = nil
  if (tonumber(kv["position_par_rapport_au_sol"]) > 0) then
    kv["bridge"] = "true"
  else
    kv["bridge"] = "false"
  end

  kv["hov_tag"] = "true"
  if (kv["hov"] and kv["hov"] == "no") then
    kv["hov_forward"] = "false"
    kv["hov_backward"] = "false"
  else
    kv["hov_forward"] = kv["auto_forward"]
    kv["hov_backward"] = kv["auto_backward"]
  end

  if (tonumber(kv["position_par_rapport_au_sol"]) < 0) then
    kv["tunnel"] = "true"
  else
    kv["tunnel"] = "false"
  end

  if (kv["acces_vehicule_leger"] == 'A péage') then
    kv["toll"] = "true"
  else
    kv["toll"] = "false"
  end

  kv["destination"] = kv["destination"]
  kv["destination:forward"] = kv["destination:forward"]
  kv["destination:backward"] = kv["destination:backward"]
  kv["destination:ref"] = kv["destination:ref"]
  kv["destination:ref:to"] = kv["destination:ref:to"]
  kv["destination:street"] = kv["destination:street"]
  kv["destination:street:to"] = kv["destination:street:to"]
  kv["junction:ref"] = kv["junction:ref"]
  kv["turn:lanes"] = kv["turn:lanes"]
  kv["turn:lanes:forward"] = kv["turn:lanes:forward"]
  kv["turn:lanes:backward"] = kv["turn:lanes:backward"]

  --truck goodies
  if (kv["restriction_de_hauteur"] ~= "None") then
    kv["maxheight"] = kv["restriction_de_hauteur"]
  end

  if (kv["restriction_de_largeur"] ~= "None") then
    kv["maxwidth"] = kv["restriction_de_largeur"]
  end

  if (kv["restriction_de_longueur"] ~= "None") then
    kv["maxlength"] = kv["restriction_de_longueur"]
  end

  if (kv["restriction_de_poids_total"] ~= "None") then
    kv["maxweight"] = kv["restriction_de_poids_total"]
  end

  if (kv["restriction_de_poids_par_essieu"] ~= "None") then
    kv["maxaxleload"] = kv["restriction_de_poids_par_essieu"]
  end

  --TODO: hazmat really should have subcategories
  kv["hazmat"] = nil
  kv["maxspeed:hgv"] = normalize_speed(kv["vitesse_moyenne_vl"])

  if (kv["hgv:national_network"] or kv["hgv:state_network"] or kv["hgv"] == "local" or kv["hgv"] == "designated") then
    kv["truck_route"] = "true"
  end

  local nref = kv["ncn_ref"]
  local rref = kv["rcn_ref"]
  local lref = kv["lcn_ref"]
  local bike_mask = 0
  if nref or kv["ncn"] == "yes" then
    bike_mask = 1
  end
  if rref or kv["rcn"] == "yes" then
    bike_mask = bit.bor(bike_mask, 2)
  end
  if lref or kv["lcn"] == "yes" then
    bike_mask = bit.bor(bike_mask, 4)
  end
  if kv["mtb"] == "yes" then
    bike_mask = bit.bor(bike_mask, 8)
  end

  kv["bike_national_ref"] = nref
  kv["bike_regional_ref"] = rref
  kv["bike_local_ref"] = lref
  kv["bike_network_mask"] = bike_mask

  return 0
end

function nodes_proc (kv, nokeys)

  --if tag exists use it, otherwise access allowed for all modes unless access = false or kv["hov"] == "designated" or kv["vehicle"] == "no")
  --if access=private use allowed modes, but consider private_access tag as true.
  local auto = 1
  local truck = 8
  local bus = 64
  local taxi = 32
  local foot = 2
  local wheelchair = 256
  local bike = 4
  local emergency = 16
  local hov = 128
  local moped = 512
  local motorcycle = 1024

  --check for gates, bollards, and sump_busters
  local gate = false
  local bollard = false
  local sump_buster = false

  --store the gate and bollard info
  kv["gate"] = tostring(gate)
  kv["bollard"] = tostring(bollard)
  kv["sump_buster"] = tostring(sump_buster)

  kv["private"] = "false"

  --store a mask denoting access
  kv["access_mask"] = bit.bor(auto, emergency, truck, bike, foot, wheelchair, bus, hov, moped, motorcycle, taxi)

  --if no information about access is given.
  kv["tagged_access"] = 0

  return 0, kv
end

function ways_proc (kv, nokeys)
  --if there were no tags passed in, ie keyvalues is empty
  if nokeys == 0 then
    return 1, kv, 0, 0
  end

  --does it at least have some interesting tags
  filter = filter_tags_generic(kv)

  --let the caller know if its a keeper or not and give back the  modified tags
  --also tell it whether or not its a polygon or road
  return filter, kv, 0, 0
end

function rels_proc (kv, nokeys)
  if (kv["type"] == "connectivity") then
    return 0, kv
  end

  if (kv["type"] == "route" or kv["type"] == "restriction") then
     if kv["restriction:probable"] then
       if kv["restriction"] or kv["restriction:conditional"] then
         kv["restriction:probable"] = nil
       end
     end

     local restrict = restriction[kv["restriction"]] or restriction[restriction_prefix(kv["restriction:conditional"])] or
                      restriction[restriction_prefix(kv["restriction:probable"])]

     local restrict_type = restriction[kv["restriction:hgv"]] or restriction[kv["restriction:emergency"]] or
                           restriction[kv["restriction:taxi"]] or restriction[kv["restriction:motorcar"]] or
                           restriction[kv["restriction:bus"]] or restriction[kv["restriction:bicycle"]] or
                           restriction[kv["restriction:hazmat"]] or restriction[kv["restriction:motorcycle"]] or
			   restriction[kv["restriction:foot"]]

     --restrictions with type win over just restriction key.  people enter both.
     if restrict_type ~= nil then
       restrict = restrict_type
     end

     if kv["type"] == "restriction" or kv["restriction:conditional"] or kv["restriction:probable"] then

       if restrict ~= nil then

         kv["restriction:conditional"] = restriction_suffix(kv["restriction:conditional"])
         kv["restriction:probable"] = restriction_suffix(kv["restriction:probable"])

         kv["restriction:hgv"] = restriction[kv["restriction:hgv"]]
         kv["restriction:emergency"] = restriction[kv["restriction:emergency"]]
         kv["restriction:taxi"] = restriction[kv["restriction:taxi"]]
         kv["restriction:motorcar"] = restriction[kv["restriction:motorcar"]]
         kv["restriction:motorcycle"] = restriction[kv["restriction:motorcycle"]]
         kv["restriction:bus"] = restriction[kv["restriction:bus"]]
         kv["restriction:bicycle"] = restriction[kv["restriction:bicycle"]]
         kv["restriction:hazmat"] = restriction[kv["restriction:hazmat"]]
         kv["restriction:foot"] = restriction[kv["restriction:foot"]]

         if restrict_type == nil then
           kv["restriction"] = restrict
         else
           kv["restriction"] = nil
         end

       else
         return 1, kv
       end
       return 0, kv
     elseif kv["route"] == "bicycle" or kv["route"] == "mtb" then

       local bike_mask = 0

       if kv["network"] == "mtb" or kv["route"] == "mtb" then
         bike_mask = 8
       end

       if kv["network"] == "ncn" then
         bike_mask = bit.bor(bike_mask, 1)
       elseif kv["network"] == "rcn" then
         bike_mask = bit.bor(bike_mask, 2)
       elseif kv["network"] == "lcn" then
         bike_mask = bit.bor(bike_mask, 4)
       end

       kv["bike_network_mask"] = bike_mask

       kv["day_on"] = nil
       kv["day_off"] = nil
       kv["restriction"] = nil

       return 0, kv
  --has a restiction but type is not restriction...ignore
     elseif restrict ~= nil then
       return 1, kv
     else
       kv["day_on"] = nil
       kv["day_off"] = nil
       kv["restriction"] = nil
       return 0, kv
     end
  end

  return 1, kv
end

function rel_members_proc (keyvalues, keyvaluemembers, roles, membercount)
  --because we filter all rels we never call this function
  --because we do rel processing later we simply say that no ways are used
  --in the given relation, what would be nice is if we could push tags
  --back to the ways via keyvaluemembers, we could then avoid doing
  --post processing to get the shielding and directional highway info
  membersuperseeded = {}
  for i = 1, membercount do
    membersuperseeded[i] = 0
  end

  return 1, keyvalues, membersuperseeded, 0, 0, 0
end
