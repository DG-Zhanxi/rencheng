"""Local transcription of CodeArts ten boundary checks, plus independent regression."""
from datetime import datetime,timedelta,timezone
from evidence_state import *
NOW=datetime(2026,11,16,12,tzinfo=timezone.utc)
def ev(source_id='S1',origin_id=None,state=OPEN,reviewed=True,available_at=None,expires_at=None,event_time=None,road_id='R1'):
    return Evidence(road_id,source_id,origin_id or source_id,event_time or NOW-timedelta(hours=1),available_at or NOW-timedelta(minutes=30),state,reviewed,expires_at or NOW+timedelta(hours=2))
def test_fresh_open():assert derive_state([ev()],NOW).state==OPEN
def test_future_and_unreviewed():
    assert derive_state([ev(available_at=NOW+timedelta(seconds=1))],NOW).state==UNKNOWN
    assert derive_state([ev(reviewed=False)],NOW).state==UNKNOWN
def test_reposts():assert derive_state([ev('S1','O1'),ev('S2','O1')],NOW).source_ids==('S1',)
def test_conflict():assert derive_state([ev('S1','O1'),ev('S2','O2',BLOCKED)],NOW).state==CONFLICT
def test_expired_open():assert derive_state([ev(expires_at=NOW)],NOW).state==UNKNOWN
def test_expired_blocked():assert derive_state([ev(),ev('S2','O2',BLOCKED,expires_at=NOW)],NOW).state==BLOCKED
def test_same_origin_conflict():
    t=NOW-timedelta(minutes=10)
    r=derive_state([ev('S1','O1',event_time=t,available_at=t),ev('S2','O1',BLOCKED,event_time=t,available_at=t),ev('S3','O2')],NOW)
    assert r.state==OPEN and r.source_ids==('S3',)
def test_mapping():assert derive_state([{'road_id':'R1','source_id':'S1','event_time':'2026-11-16T09:00:00Z','available_at':'2026-11-16T10:00:00Z','state':' BLOCKED ','reviewed':True}],NOW).state==BLOCKED
def test_multiple_roads():
    import pytest
    with pytest.raises(ValueError):derive_state([ev(),ev('S2',road_id='R2')],NOW)
def test_empty():assert derive_state([],NOW).state==UNKNOWN
def test_future_event_independent_regression():
    assert derive_state([ev(event_time=NOW+timedelta(hours=1))],NOW).state==UNKNOWN
