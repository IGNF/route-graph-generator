from lxml import etree

PIVOT_ATTRIBUTE_TO_OSM = {
    "direction": {
        -1: {"oneway": "-1"},
        1: {"oneway": "1"}
    },
    "vitesse_moyenne_vl": "",
    "nature": {
        "Route à 2 chaussées": {"highway": "motorway"},
        "Type autoroutier": {"highway": "motorway", "foot": "no"},
        "Bretelle": {"highway": "motorway", "foot": "no"},
        "Sentier": {"highway": "footway", "surface": "unpaved"},
        "Route empierrée": {"surface": "unpaved"},
        "Chemin": {"surface": "unpaved"},
    },
    "cleabs": "",
    "importance": "",
    "way_names": "",
    "nom_1_gauche": "",
    "nom_1_droite": "",
    "cpx_numero": "",
    "cpx_toponyme_route_nommee": "",
    "sens_de_circulation": "",
    "position_par_rapport_au_sol": "",
    "acces_vehicule_leger": {
        "Physiquement impossible": {"highway": "footway"},
        "A péage": {"toll": "yes"},
    },
    "largeur_de_chaussee": "",
    "nombre_de_voies": "",
    "insee_commune_gauche": "",
    "insee_commune_droite": "",
    "itineraire_vert": "",
    "reserve_aux_bus": "",
    "urbain": "",
    "acces_pieton": {
        "Restreint aux ayants droit": {"foot": "no"}
    },
    "nature_de_la_restriction": "",
    "restriction_de_hauteur": "maxheight",
    "restriction_de_poids_total": "maxweight",
    "restriction_de_poids_par_essieu": "maxaxleload",
    "restriction_de_largeur": "maxwidth",
    "restriction_de_longueur": "maxlength",
    "matieres_dangereuses_interdites": {
        "t": {"hazmat": "no"}
    },
    "cpx_gestionnaire": "",
    "cpx_numero_route_europeenne": "",
    "cpx_classement_administratif": {
        "Départementale": {"service": "driveway"},
        "Nationale": {"service": "driveway"},
        "Autoroute": {"service": "driveway"},
    },
    "transport_exceptionnel": "",
    "vla_par_defaut": "",
    "cout_penalites": "",
    "vehicule_leger_interdit": "",
    "cout_vehicule_prioritaire": "",
}

def writeNode(node, extraction_date):
    """
    Fonction qui écrit un noeud en xml à partir d'un dict (potentiellement une ligne de bdd)

    Parameters
    ----------
    node: dict
        Dictionnaire des attributs du noeud.
        pour l'instant ne contient que la clé "id"
    extraction_date: str
        date de l'extraction des données au format YYYY-MM-DD

    Returns
    -------
    lxml.etree.Element
        element xml correspondant au noeud
    """

    nodeEl = etree.Element("node", id="%s" %node['id'])

    nodeEl.set('lon', '%s' % node['lon'])
    nodeEl.set('lat', '%s' % node['lat'])
    nodeEl.set('version', '1')
    nodeEl.set('timestamp', '%sT13:37:00Z' % extraction_date)

    return nodeEl

def writeWay(way, extraction_date):
    """
    Fonction qui écrit une arrête vierge en xml à partir d'un dict
    (potentiellement une ligne de bdd)

    Parameters
    ----------
    way: dict
        Dictionnaire des attributs de l'arrête.
    extraction_date: str
        date de l'extraction des données au format YYYY-MM-DD

    Returns
    -------
    lxml.etree.Element
        element xml correspondant à l'arrête vierge
    """

    wayEl = etree.Element("way", id="%s" %way['id'])
    wayEl.set('version', '1')
    wayEl.set('timestamp', '%sT13:37:00Z' % extraction_date)

    return wayEl

def writeWayNds(wayEl, way, internodes):
    """
    Fonction qui écrit dans un arrête en xml les noeuds intermédiaires

    Parameters
    ----------
    wayEl: lxml.etree.Element
        objet xml corrrespondant à l'arrête
    way: dict
        Dictionnaire des attributs de l'arrête.
    internodes: [dict]
        Liste de dict, réponse de la fonction inter_nodes(geom) définie en SQL

    Returns
    -------
    lxml.etree.Element
        element xml correspondant à l'arrête avec ses noeuds
    """

    nd = etree.SubElement(wayEl, 'nd')
    nd.set('ref', '%s' %way['source_id'])

    for internode in internodes:
        nd = etree.SubElement(wayEl, 'nd')
        nd.set('ref', '%s' %internode['id'])

    nd = etree.SubElement(wayEl, 'nd')
    nd.set('ref', '%s' %way['target_id'])

    return wayEl

# Ecriture des restrictions
def writeRes(res, i, extraction_date):
    """
    Fonction qui écrit une restriction (non communication) en xml à partir d'un dict

    Parameters
    ----------
    res: dict
        Dictionnaire des attributs de la restriction.
    i: int
        identifiant de la retriction
    extraction_date: str
        date de l'extraction des données au format YYYY-MM-DD

    Returns
    -------
    lxml.etree.Element
        element xml correspondant à la restriction
    """

    resEl = etree.Element("relation", id="%s" %i)
    resEl.set('version', '1')
    resEl.set('timestamp', '%sT13:37:00Z' % extraction_date)

    _from = etree.SubElement(resEl, 'member')
    _from.set('type', 'way')
    _from.set('ref', '%s' %res['id_from'])
    _from.set('role','from')

    _from = etree.SubElement(resEl, 'member')
    _from.set('type', 'node')
    _from.set('ref', '%s' %res['common_vertex_id'])
    _from.set('role','via')

    _to = etree.SubElement(resEl, 'member')
    _to.set('type', 'way')
    _to.set('ref', '%s' %res['id_to'])
    _to.set('role','to')

    _tag0 = etree.SubElement(resEl, 'tag')
    _tag0.set('k','restriction')
    # TODO : Peut on définir plus précisément les restrictions ?
    _tag0.set('v','no_entry')

    _tag = etree.SubElement(resEl, 'tag')
    _tag.set('k','type')
    _tag.set('v','restriction')

    return resEl

def writeWayTags(wayEl, way):
    """
    Fonction qui ajoute des attributs (tags) à un élement xml d'arrête

    Parameters
    ----------
    wayEl: lxml.etree.Element
        objet xml corrrespondant à l'arrête
    way: int
        Dictionnaire des attributs de l'arrête.

    Returns
    -------
    lxml.etree.Element
        element xml correspondant à l'arrête avec ses attributs
    """
    tags_present = set()
    for k,v in way.items():
        if k == 'internodes' or k.endswith('_id') or k == 'geom' or k=='geometrie' :
            continue
        tag = etree.SubElement(wayEl, 'tag')
        tag.set('k', '%s' %k)
        tag.set('v', '%s' %str(v))
        tags_present.add(k)
        if PIVOT_ATTRIBUTE_TO_OSM.get(k, "") != "" and isinstance(PIVOT_ATTRIBUTE_TO_OSM.get(k, ""), dict):
            for attr_value, new_tags in PIVOT_ATTRIBUTE_TO_OSM.get(k, "").items():
                if v == attr_value:
                    for t, val in new_tags.items():
                        if t not in tags_present:
                            newtag = etree.SubElement(wayEl, 'tag')
                            newtag.set('k', '%s' %t)
                            newtag.set('v', '%s' %str(val))
                            tags_present.add(t)
        elif PIVOT_ATTRIBUTE_TO_OSM.get(k, "") != "" and isinstance(PIVOT_ATTRIBUTE_TO_OSM.get(k, ""), str):
            tag = etree.SubElement(wayEl, 'tag')
            tag.set('k', '%s' %PIVOT_ATTRIBUTE_TO_OSM.get(k, ""))
            tag.set('v', '%s' %str(v))
            tags_present.add(k)
        # Cas particulier : vitesse
        if k == "vitesse_moyenne_vl":
            corrected_speed = v
            if way["urbain"] and v > 0:
                corrected_speed = 3.6 * way["length_m"] / ((3.6 / corrected_speed) * way["length_m"] + 5)
            advisory_speed = etree.SubElement(wayEl, 'tag')
            advisory_speed.set('k', "maxspeed:advisory")
            advisory_speed.set('v', '%s' %str(corrected_speed))
            tags_present.add("maxspeed:advisory")
            practical_speed = etree.SubElement(wayEl, 'tag')
            practical_speed.set('k', "maxspeed:practical")
            practical_speed.set('v', '%s' %str(corrected_speed))
            tags_present.add("maxspeed:practical")
            if way["direction"] <= 0:
                backward_speed = etree.SubElement(wayEl, 'tag')
                backward_speed.set('k', "maxspeed:backward")
                backward_speed.set('v', '%s' %str(corrected_speed))
                tags_present.add("maxspeed:backward")
            else:
                backward_speed = etree.SubElement(wayEl, 'tag')
                backward_speed.set('k', "maxspeed:backward")
                backward_speed.set('v', "0")
                tags_present.add("maxspeed:backward")

            if way["direction"] >= 0:
                forward_speed = etree.SubElement(wayEl, 'tag')
                forward_speed.set('k', "maxspeed:forward")
                forward_speed.set('v', '%s' %str(corrected_speed))
                tags_present.add("maxspeed:forward")
            else:
                forward_speed = etree.SubElement(wayEl, 'tag')
                forward_speed.set('k', "maxspeed:forward")
                forward_speed.set('v', "0")
                tags_present.add("maxspeed:forward")

        # Cas particulier : position_par_rapport_au_sol
        if k == "position_par_rapport_au_sol":
            if int(v) > 0:
                bridge = etree.SubElement(wayEl, 'tag')
                bridge.set('k', "bridge")
                bridge.set('v', "yes")
                tags_present.add("bridge")
            if int(v) < 0:
                tunnel = etree.SubElement(wayEl, 'tag')
                tunnel.set('k', "tunnel")
                tunnel.set('v', "yes")
                tags_present.add("tunnel")

    return wayEl
