from dataclasses import dataclass


@dataclass(frozen=True)
class CityPoint:
    name: str
    lat: float
    lng: float
