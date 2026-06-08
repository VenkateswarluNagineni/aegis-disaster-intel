from datetime import datetime

from aegis.schema import HazardEvent, HazardType


def test_dedup_key_is_stable():
    ev = HazardEvent(
        source="usgs",
        source_id="ak0231",
        hazard_type=HazardType.EARTHQUAKE,
        latitude=61.2,
        longitude=-149.9,
        observed_at=datetime(2026, 6, 8, 0, 0, 0),
        magnitude=4.5,
    )
    assert ev.dedup_key == "usgs:ak0231"
