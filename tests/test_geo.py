import math

import pytest

from aegis.geo import asset_risk, haversine_km, proximity_risk


def test_haversine_known_distance():
    # College Station, TX -> Austin, TX is ~135 km.
    d = haversine_km(30.6280, -96.3344, 30.2672, -97.7431)
    assert 120 < d < 150


def test_proximity_risk_bounds_and_decay():
    assert proximity_risk(0.0) == 1.0
    assert math.isclose(proximity_risk(50.0, radius_km=50.0), math.exp(-1), rel_tol=1e-9)
    assert proximity_risk(1000.0) < proximity_risk(10.0)


def test_proximity_risk_rejects_bad_radius():
    with pytest.raises(ValueError):
        proximity_risk(10.0, radius_km=0)


def test_asset_risk_higher_when_closer():
    hazard = (30.0, -96.0)
    near = asset_risk((30.1, -96.1), hazard)
    far = asset_risk((35.0, -100.0), hazard)
    assert near > far
