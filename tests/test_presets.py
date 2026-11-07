import pytest
from instant_film_agent.errors import AgentError
from instant_film_agent.presets import (
    get_builtin_presets,
    list_all_presets,
    load_favorites,
    resolve_preset,
    slugify,
)


def test_builtin_presets_exist():
    presets = get_builtin_presets()
    assert len(presets) >= 10
    assert "Instax Mini (Vertical Snap)" in presets
    assert "Polaroid 600 (Square Classic)" in presets


def test_slugify():
    assert slugify("Instax Mini (Vertical Snap)") == "instax-mini-vertical-snap"
    assert slugify("Polaroid SX-70") == "polaroid-sx-70"


def test_resolve_default_favorite():
    resolved = resolve_preset("favorite")
    assert resolved.slug == "instax-mini-vertical-snap"
    assert resolved.config_dict["frame_format"] == "Portrait (Vertical)"


def test_resolve_aliases():
    cheki = resolve_preset("cheki")
    assert cheki.slug == "instax-mini-vertical-snap"

    polaroid = resolve_preset("polaroid")
    assert polaroid.slug == "polaroid-600-square-classic"

    wide = resolve_preset("wide")
    assert wide.slug == "instax-wide-landscape-panorama"


def test_resolve_not_found():
    with pytest.raises(AgentError) as exc:
        resolve_preset("non_existent_preset_999")
    err = exc.value
    assert err.code == "preset_not_found"
    assert "candidates" in err.extra
    assert len(err.extra["candidates"]) > 0
