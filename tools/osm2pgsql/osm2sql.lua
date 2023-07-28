-- This is a specific configuration that is used for r2gg 
-- This script will load data into a BDD but it will not be a pivot ready for use
-- A SQL script will have to be run on the result of this script to have a pivot ready for the next transformation 

-- For more information about LUA configuration for osm2pgsql, please see : 
-- https://osm2pgsql.org/doc/manual.html#the-flex-output

-- For more info about OSM data, please see :
-- https://wiki.openstreetmap.org/wiki/Highways
-- https://wiki.openstreetmap.org/wiki/Map_features#Highway
-- https://wiki.openstreetmap.org/wiki/Relation:route
-- https://wiki.openstreetmap.org/wiki/Relation:restriction
-- https://wiki.openstreetmap.org/wiki/Conditional_restrictions

-- Set this to the projection you want to use
local srid = 4326

local tables = {}

-- Definitions of the tables and their columns 
-- We only need ways and relations, there are usefull for routing
-- a nodes table will be created later by an sql script
-- We create a structure close to the pivot of r2gg. It has additional columns (ex. 'osm_id')

tables.edges = osm2pgsql.define_way_table('edges', {

    { column = 'source_id', type = 'bigint' },
    { column = 'target_id', type = 'bigint' },
    { column = 'x1', type = 'real' },
    { column = 'y1', type = 'real' },
    { column = 'x2', type = 'real' },
    { column = 'y2', type = 'real' },
    { column = 'length_m', type = 'real' },
    { column = 'direction', type = 'integer' },
    { column = 'vitesse_moyenne_vl', type = 'integer' },
    { column = 'geom', type = 'linestring', projection = srid },

    -- Additional colums for specific OSM data
    { column = 'name', type = 'text' }

})

tables.non_comm = osm2pgsql.define_relation_table('non_comm', {

    -- here, we add a cleabs because OSM data could often create multiple lines for the same restriction
    { column = 'cleabs', type = 'serial', create_only = true },
    { column = 'id_from', type = 'bigint' },
    { column = 'id_to', type = 'bigint' },
    { column = 'common_vertex_id', type = 'bigint' },
    
    -- Additional colums for specific OSM data
    { column = 'restriction_type' , type = 'text' }

})


-- These tag keys are generally regarded as useless for most rendering. Most
-- of them are from imports or intended as internal information for mappers.
--
-- If a key ends in '*' it will match all keys with the specified prefix.
--
-- If you want some of these keys, perhaps for a debugging layer, just
-- delete the corresponding lines.
local delete_keys = {
    -- "mapper" keys
    'attribution',
    'comment',
    'created_by',
    'fixme',
    'note',
    'note:*',
    'odbl',
    'odbl:note',
    'source',
    'source:*',
    'source_ref',

    -- "import" keys

    -- Corine Land Cover (CLC) (Europe)
    'CLC:*',

    -- Geobase (CA)
    'geobase:*',
    -- CanVec (CA)
    'canvec:*',

    -- osak (DK)
    'osak:*',
    -- kms (DK)
    'kms:*',

    -- ngbe (ES)
    -- See also note:es and source:file above
    'ngbe:*',

    -- Friuli Venezia Giulia (IT)
    'it:fvg:*',

    -- KSJ2 (JA)
    -- See also note:ja and source_ref above
    'KSJ2:*',
    -- Yahoo/ALPS (JA)
    'yh:*',

    -- LINZ (NZ)
    'LINZ2OSM:*',
    'linz2osm:*',
    'LINZ:*',
    'ref:linz:*',

    -- WroclawGIS (PL)
    'WroclawGIS:*',
    -- Naptan (UK)
    'naptan:*',

    -- TIGER (US)
    'tiger:*',
    -- GNIS (US)
    'gnis:*',
    -- National Hydrography Dataset (US)
    'NHD:*',
    'nhd:*',
    -- mvdgis (Montevideo, UY)
    'mvdgis:*',

    -- EUROSHA (Various countries)
    'project:eurosha_2012',

    -- UrbIS (Brussels, BE)
    'ref:UrbIS',

    -- NHN (CA)
    'accuracy:meters',
    'sub_sea:type',
    'waterway:type',
    -- StatsCan (CA)
    'statscan:rbuid',

    -- RUIAN (CZ)
    'ref:ruian:addr',
    'ref:ruian',
    'building:ruian:type',
    -- DIBAVOD (CZ)
    'dibavod:id',
    -- UIR-ADR (CZ)
    'uir_adr:ADRESA_KOD',

    -- GST (DK)
    'gst:feat_id',

    -- Maa-amet (EE)
    'maaamet:ETAK',
    -- FANTOIR (FR)
    'ref:FR:FANTOIR',

    -- 3dshapes (NL)
    '3dshapes:ggmodelk',
    -- AND (NL)
    'AND_nosr_r',

    -- OPPDATERIN (NO)
    'OPPDATERIN',
    -- Various imports (PL)
    'addr:city:simc',
    'addr:street:sym_ul',
    'building:usage:pl',
    'building:use:pl',
    -- TERYT (PL)
    'teryt:simc',

    -- RABA (SK)
    'raba:id',
    -- DCGIS (Washington DC, US)
    'dcgis:gis_id',
    -- Building Identification Number (New York, US)
    'nycdoitt:bin',
    -- Chicago Building Inport (US)
    'chicago:building_id',
    -- Louisville, Kentucky/Building Outlines Import (US)
    'lojic:bgnum',
    -- MassGIS (Massachusetts, US)
    'massgis:way_id',
    -- Los Angeles County building ID (US)
    'lacounty:*',
    -- Address import from Bundesamt für Eich- und Vermessungswesen (AT)
    'at_bev:addr_date',

    -- misc
    'import',
    'import_uuid',
    'OBJTYPE',
    'SK53_bulk:load',
    'mml:class'
}

-- The osm2pgsql.make_clean_tags_func() function takes the list of keys
-- and key prefixes defined above and returns a function that can be used
-- to clean those tags out of a Lua table. The clean_tags function will
-- return true if it removed all tags from the table.
local clean_tags = osm2pgsql.make_clean_tags_func(delete_keys)

local highway_types = {
    'motorway',
    'motorway_link',
    'trunk',
    'trunk_link',
    'primary',
    'primary_link',
    'secondary',
    'secondary_link',
    'tertiary',
    'tertiary_link',
    'unclassified',
    'residential',
    'track',
    'service',
    'living_street',
    'pedestrian',
    'bus_guideway',
    'escape',
    'raceway',
    'road',
    'busway',
    'footway',
    'bridleway',
    'steps',
    'corridor',
    'path',
    'via_ferrata',
    'cycleway'
}

local restriction_types = {
    'restriction'
}

-- Prepare table "opt_highway_types" for quick checking of highway types
local opt_highway_types = {}
for _, k in ipairs(highway_types) do
    opt_highway_types[k] = 1
end

-- Parse a maxspeed value like "30" or "55 mph" and return a number in km/h
function parse_speed(input)
    if not input then
        return nil
    end

    local maxspeed = tonumber(input)

    -- If maxspeed is just a number, it is in km/h, so just return it
    if maxspeed then
        return maxspeed
    end

    -- If there is an 'mph' at the end, convert to km/h and return
    if input:sub(-3) == 'mph' then
        local num = tonumber(input:sub(1, -4))
        if num then
            return math.floor(num * 1.60934)
        end
    end

    return nil

end

function osm2pgsql.process_way(object)
   
    -- Cleaning unecessary tags
    if clean_tags(object.tags) then
        return
    end

    -- Get the type of "highway" and remove it from the tags
    local local_type = object:grab_tag('highway')
    -- We are only interested in highways of the given types
    if not opt_highway_types[local_type] then
        return
    end

    -- Compute the bbox
    local tx1,ty1,tx2,ty2 = object:get_bbox()  

    -- Name 
    local tname = object:grab_tag('name')

    -- Add the edge
    tables.edges:add_row({

        -- OSM id is in the way_id column
        -- So we need to be careful on adding rows because multiple add_rows 
        -- of the same object will create multiple rows with the same id

        -- Geometry
        geom = { create = 'line' },

        -- The 'vitesse_moyenne_vl' column gets the maxspeed in km/h
        vitesse_moyenne_vl = parse_speed(object.tags.maxspeed),

        -- The 'oneway' column has the special type "direction", which will
        -- store "yes", "true" and "1" as 1, "-1" as -1, and everything else
        -- as 0.
        direction = object.tags.oneway or 0,

        -- Bbox of the way
        x1 = tx1,
        y1 = ty1,
        x2 = tx2,
        y2 = ty2,

        -- Name 
        name = tname

    })

end

function osm2pgsql.process_relation(object) 

    -- Cleaning unecessary tags
    if clean_tags(object.tags) then
        return
    end

    -- We only want a restriction
    if object.tags.type ~= 'restriction' then
	    return
    end

    -- Analyzing the restriction 
    local from_ids, to_ids = {},{}
    local nb_from, nb_to = 0,0

    for _,member in ipairs(object.members) do
        
        if member.role == 'from' and member.type == 'w' then
            nb_from = nb_from + 1
            from_ids[nb_from] = member.ref
        end

        if member.role == 'to' and member.type == 'w' then
            nb_to = nb_to + 1
            to_ids[nb_to] = member.ref
        end

        -- We don't take the via for now 
        -- Because for nodes, we will create a new id from edges 
        -- And for ways, we don't handle this case in the pivot
        -- So ways via are a TODO 
    
    end 

    -- Little verification
    if nb_from == 0 or nb_to == 0 then
	    return
    end 

    -- Get restriction type 
    local trestriction_type = object:grab_tag('restriction')


    -- For each possible from and to, we will add a row  

    for _,from_id in ipairs(from_ids) do

        for _,to_id in ipairs(to_ids) do

            -- Add the resttriction
            tables.non_comm:add_row({
        
                -- Cleabs : nothing to do here
        
                -- Restriction type 
                restriction_type = trestriction_type,

                id_from = from_id,

                id_to = to_id

            })

        end

    end

end