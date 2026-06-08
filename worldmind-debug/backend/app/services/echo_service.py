from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.models.schemas import ThingEcho, ThingSummary


def _first_property(features: Dict[str, Any], names: Tuple[str, ...]) -> Optional[Any]:
    for name in names:
        feature = features.get(name)
        if isinstance(feature, dict):
            props = feature.get("properties")
            if isinstance(props, dict):
                if "value" in props:
                    return props["value"]
                for key in ("current", "state", name):
                    if key in props:
                        return props[key]
            elif props is not None:
                return props
    return None


class EchoService:
    def summarize_thing(self, thing_id: str, raw: Dict[str, Any]) -> ThingEcho:
        features = raw.get("features") if isinstance(raw, dict) else {}
        if not isinstance(features, dict):
            features = {}
        summary = ThingSummary(
            temperature=_first_property(features, ("temperature", "temp", "fermentation_temperature")),
            ph=_first_property(features, ("ph", "pH")),
            humidity=_first_property(features, ("humidity",)),
            updated_at=raw.get("modified") or raw.get("_modified") or raw.get("revision"),
        )
        return ThingEcho(thing_id=thing_id, raw=raw, summary=summary)
