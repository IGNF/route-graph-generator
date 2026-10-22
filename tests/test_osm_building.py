import pytest
from lxml import etree

from r2gg._osm_building import bdtopo_highway_tags, writeWayTags


def _way(**attrs):
    way = {
        "nature": "Route à 1 chaussée",
        "importance": 5,
        "urbain": True,
        "vitesse_moyenne_vl": 30,
        "direction": 0,
        "length_m": 100,
        "position_par_rapport_au_sol": 0,
    }
    way.update(attrs)
    return way


def _tags(way):
    wayEl = writeWayTags(etree.Element("way", id="1"), way)
    return {tag.get("k"): tag.get("v") for tag in wayEl.findall("tag")}


@pytest.mark.parametrize("attrs, expected", [
    ({"importance": 1}, "trunk"),
    ({"importance": 2, "nature": "Route à 2 chaussées"}, "primary"),
    ({"importance": 3, "nature": "Rond-point"}, "secondary"),
    ({"importance": 4}, "tertiary"),
    ({"importance": 5, "urbain": True}, "residential"),
    ({"importance": 5, "urbain": False}, "unclassified"),
    ({"importance": None, "urbain": False}, "unclassified"),
    ({"importance": 6}, "service"),
    ({"nature": "Type autoroutier", "importance": 1}, "motorway"),
    ({"nature": "Bretelle", "importance": 1}, "motorway_link"),
    ({"nature": "Sentier", "importance": 6}, "path"),
    ({"nature": "Escalier", "importance": 6}, "steps"),
    ({"nature": "Piste cyclable", "importance": 6}, "cycleway"),
    ({"nature": "Chemin", "importance": 6}, "track"),
    ({"nature": "Route empierrée", "importance": 5}, "track"),
])
def test_every_bdtopo_nature_gets_a_highway(attrs, expected):
    """Valhalla's default lua drops ways without a known highway tag, so every
    BDTopo nature must map to one."""
    assert bdtopo_highway_tags(_way(**attrs))["highway"] == expected


def test_ferry():
    assert bdtopo_highway_tags(_way(nature="Bac ou liaison maritime")) == {"route": "ferry"}


def test_no_car_speed_forbids_motor_vehicles():
    assert bdtopo_highway_tags(_way(vitesse_moyenne_vl=0))["motor_vehicle"] == "no"
    assert "motor_vehicle" not in bdtopo_highway_tags(_way(vitesse_moyenne_vl=30))


def test_way_tags_contain_highway_and_no_driveway():
    tags = _tags(_way(cpx_classement_administratif="Départementale", importance=3))
    assert tags["highway"] == "secondary"
    assert "service" not in tags


def test_physically_impossible_access_keeps_way_for_pedestrians():
    tags = _tags(_way(acces_vehicule_leger="Physiquement impossible"))
    assert tags["highway"] == "residential"
    assert tags["motor_vehicle"] == "no"


def test_motorway_forbids_pedestrians():
    tags = _tags(_way(nature="Type autoroutier", importance=1, vitesse_moyenne_vl=110))
    assert tags["highway"] == "motorway"
    assert tags["foot"] == "no"


def test_way_names_written_to_name():
    way_names = '{"nom_1_gauche": "Rue des Rosiers", "nom_1_droite": "Rue des Rosiers"}'
    tags = _tags(_way(way_names=way_names))
    assert tags["name"] == way_names
    assert tags["way_names"] == way_names
