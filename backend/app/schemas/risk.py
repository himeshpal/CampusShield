from datetime import datetime

from pydantic import BaseModel


class TopAsset(BaseModel):
    id: int
    asset_tag: str
    name: str | None
    status: str
    score: float
    band: str


class RiskDriver(BaseModel):
    key: str
    label: str
    points: int  # summed over all assessed assets, before the criticality multiplier
    share: float  # of all points, 0..1


class RiskSummary(BaseModel):
    bands: dict[str, int]
    assessed: int
    average: float | None
    top: list[TopAsset]
    drivers: list[RiskDriver] = []


class RiskPoint(BaseModel):
    score: float
    band: str
    computed_at: datetime
    scan_id: int | None


class RiskModel(BaseModel):
    version: int
    formula: str
    components: list[dict]
    multiplier: str
    bands: list[dict]
    cvss_points: list[dict]
    service_weights: list[dict]
    other_port_points: int
    cves: list[dict]
    end_of_life: list[dict]
    script_findings: list[dict]
    limitations: list[str]
