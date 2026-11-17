"""CodeArts chat export, 2026-11-16. Formatting compacted; local review follows."""
from __future__ import annotations
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
OPEN, BLOCKED, UNKNOWN, CONFLICT = 'open', 'blocked', 'unknown', 'conflict'
VALID_STATES = frozenset({OPEN, BLOCKED, UNKNOWN})
@dataclass(frozen=True, slots=True)
class Evidence:
    road_id: str; source_id: str; origin_id: str
    event_time: datetime; available_at: datetime
    state: str; reviewed: bool = False; expires_at: datetime | None = None
@dataclass(frozen=True, slots=True)
class StateResult:
    state: str
    source_ids: tuple[str,...]
    reason: str
    def as_dict(self):
        return dict(state=self.state, source_ids=list(self.source_ids), reason=self.reason)
def _time(value, label):
    if isinstance(value,str):
        text=value.strip();text=text[:-1]+'+00:00' if text[-1:] in ('Z','z') else text
        value=datetime.fromisoformat(text)
    if not isinstance(value,datetime): raise TypeError(f'{label} must be datetime or ISO 8601 string')
    if value.tzinfo is None:return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
def _text(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError(f'{label} must be a non-empty string')
    return value.strip()
def _state(value,label):
    state=value.strip().lower() if isinstance(value,str) else ''
    if state not in VALID_STATES:raise ValueError(f'{label} invalid state')
    return state
def _coerce(item,index):
    label=f'evidence[{index}]'
    if isinstance(item,Evidence):item={k:getattr(item,k) for k in Evidence.__dataclass_fields__}
    if not isinstance(item,Mapping):raise TypeError(f'{label} must be Evidence or mapping')
    missing=[k for k in ('road_id','source_id','event_time','available_at','state') if k not in item]
    if missing:raise ValueError(f'{label} missing {missing}')
    source_id=_text(item['source_id'],f'{label}.source_id')
    origin,expires=item.get('origin_id'),item.get('expires_at');reviewed=item.get('reviewed',False)
    if not isinstance(reviewed,bool):raise TypeError(f'{label}.reviewed must be a bool')
    return Evidence(road_id=_text(item['road_id'],f'{label}.road_id'),source_id=source_id,
        origin_id=source_id if origin is None else _text(origin,f'{label}.origin_id'),
        event_time=_time(item['event_time'],f'{label}.event_time'),available_at=_time(item['available_at'],f'{label}.available_at'),
        state=_state(item['state'],f'{label}.state'),reviewed=reviewed,expires_at=None if expires is None else _time(expires,f'{label}.expires_at'))
def _ids(records):return tuple(sorted({r.source_id for r in records}))
def _reason(base,notes):return base+'; '+'; '.join(notes) if notes else base
def derive_state(evidence,as_of,*,road_id=None):
    now=_time(as_of,'as_of')
    if isinstance(evidence,(str,bytes,Mapping)):raise TypeError('evidence must be an iterable of records')
    records=[_coerce(item,index) for index,item in enumerate(evidence)]
    if road_id is None:
        roads={r.road_id for r in records}
        if len(roads)>1:raise ValueError('multiple roads found; pass road_id=...')
        road=next(iter(roads),None)
    else:road=_text(road_id,'road_id')
    scope=[r for r in records if r.road_id==road]
    if not scope:return StateResult(UNKNOWN,(),f'road {road!r} has no evidence as of {now.isoformat()}')
    future=sum(r.reviewed and (r.available_at>now or r.event_time>now) for r in scope);unreviewed=sum(not r.reviewed for r in scope)
    usable=[r for r in scope if r.reviewed and r.available_at<=now and r.event_time<=now]
    notes=[f'ignored {n} {kind} evidence' for n,kind in ((future,'future'),(unreviewed,'unreviewed')) if n]
    if not usable:return StateResult(UNKNOWN,(),_reason(f'no reviewed evidence as of {now.isoformat()}',notes))
    grouped={}
    for r in usable:grouped.setdefault(r.origin_id,[]).append(r)
    claims=[];bad=[]
    for origin,items in sorted(grouped.items()):
        latest=max((r.event_time,r.available_at) for r in items)
        tied=[r for r in items if (r.event_time,r.available_at)==latest]
        if len({r.state for r in tied})>1:bad.append(origin);continue
        rep=min(tied,key=lambda r:r.source_id);claims.append((rep,rep.expires_at is not None and rep.expires_at<=now))
    if bad:notes.append(f'excluded inconsistent origins {sorted(bad)}')
    fresh_open=[r for r,expired in claims if not expired and r.state==OPEN]
    fresh_blocked=[r for r,expired in claims if not expired and r.state==BLOCKED]
    stale_blocked=[r for r,expired in claims if expired and r.state==BLOCKED]
    stale_open=[r for r,expired in claims if expired and r.state==OPEN]
    if stale_open:notes.append(f'ignored {len(stale_open)} expired open evidence (never treated as open)')
    if fresh_open and fresh_blocked:return StateResult(CONFLICT,_ids(fresh_open+fresh_blocked),_reason(f'conflict as of {now.isoformat()}',notes))
    if fresh_blocked:return StateResult(BLOCKED,_ids(fresh_blocked),_reason('blocked by fresh sources',notes))
    if fresh_open and stale_blocked:return StateResult(BLOCKED,_ids(stale_blocked),_reason('expired blocked overrides fresh open (conservative)',notes))
    if fresh_open:return StateResult(OPEN,_ids(fresh_open),_reason('open by fresh sources',notes))
    if stale_blocked:return StateResult(BLOCKED,_ids(stale_blocked),_reason('only expired blocked (conservative)',notes))
    return StateResult(UNKNOWN,(),_reason(f'no fresh open or blocked evidence as of {now.isoformat()}',notes))
