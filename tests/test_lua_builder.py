from r2gg._lua_builder import build_lua
from r2gg._read_config import config_from_path

COSTS_CONFIG = "docker/config/costs_calculation.json"


def test_osrm_name_uses_short_names_by_priority():
    lua = build_lua(config_from_path(COSTS_CONFIG), "cost_s_car")

    assert "way_names" not in lua
    assert '{"nom_1_droite", "nom_1_gauche", "cpx_toponyme_route_nommee", "cpx_numero"}' in lua
    assert "value ~= 'None'" in lua
