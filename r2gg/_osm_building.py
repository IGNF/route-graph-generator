from lxml import etree

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

    for k,v in way.items():
        if k == 'internodes' or k.endswith('_id') or k == 'geom' or k=='geometrie' :
            continue
        tag = etree.SubElement(wayEl, 'tag')
        tag.set('k', '%s' %k)
        tag.set('v', '%s' %str(v))
    return wayEl
