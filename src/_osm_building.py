from lxml import etree
from xml.dom import minidom

def writeNode(node):
    nodeEl = etree.Element("node", id="%s" %node['id'])

    nodeEl.set('lon', '%s' % node['lon'])
    nodeEl.set('lat', '%s' % node['lat'])

    nodeEl.set('user', 'bduni')
    nodeEl.set('uid', '1')
    nodeEl.set('visible', 'true')

    nodeEl.set('version', '1')
    nodeEl.set('changeset', '1')
    nodeEl.set('timestamp', '2016-01-01T00:00:00Z')

    return nodeEl

def writeWay(way):
    wayEl = etree.Element("way", id="%s" %way['id'])


    wayEl.set('user', 'bduni')
    wayEl.set('uid', '1')
    wayEl.set('visible', 'true')

    wayEl.set('version', '1')
    wayEl.set('changeset', '1')
    wayEl.set('timestamp', '2016-01-01T00:00:00Z')
    return wayEl

def writeWayNds(wayEl, way, internodes):
    nd = etree.SubElement(wayEl, 'nd')
    nd.set('ref', '%s' %way['source_id'])

    for internode in internodes:
        nd = etree.SubElement(wayEl, 'nd')
        nd.set('ref', '%s' %internode['id'])

    nd = etree.SubElement(wayEl, 'nd')
    nd.set('ref', '%s' %way['target_id'])

    return wayEl

# Ecriture des restrictions
def writeRes(res,i):

    resEl = etree.Element("relation", id="%s" %i)
    resEl.set('visible', 'true')
    resEl.set('version', '1')
    resEl.set('uid', '1')
    resEl.set('user', 'bduniv2')
    resEl.set('changeset', '1')
    resEl.set('timestamp', '2016-01-01T00:00:00Z')

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
    for k,v in way.iteritems():
        if k == 'internodes' or k.endswith('_id') or k == 'geom' or k=='geometrie' :
            continue
        tag = etree.SubElement(wayEl, 'tag')
        tag.set('k', '%s' %k.decode('utf8'))
        tag.set('v', '%s' %str(v).decode('utf8'))
    return wayEl
