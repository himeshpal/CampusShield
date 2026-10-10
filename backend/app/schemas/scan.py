from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Profile = Literal["quick", "standard", "deep"]


class ScanCreate(BaseModel):
    target: str = Field(min_length=7, max_length=43)
    profile: Profile = "standard"


class ProfileOut(BaseModel):
    key: Profile
    label: str
    description: str
    estimate: str
    command: str


class ScanOptions(BaseModel):
    profiles: list[ProfileOut]
    authorized_subnets: list[str]
    excluded: list[str]
    default_target: str


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    profile: Profile
    status: str
    phase: str | None
    progress: int
    triggered_by: str
    requested_by_name: str | None = None
    hosts_up: int
    open_ports: int = 0
    command: str | None = None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ScanPortOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port: int
    protocol: str
    service: str | None
    product: str | None
    version: str | None
    extra_info: str | None
    script_output: dict[str, str]


class HostAsset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_tag: str
    name: str | None
    status: str
    asset_type: str


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    severity: str
    title: str
    detail: str | None
    port: int | None
    cve_id: str | None
    points: float


class ScanHostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    mac_address: str | None
    mac_vendor: str | None
    hostname: str | None
    os_guess: str | None
    match_method: str | None  # mac | ip | new | ip_conflict
    asset: HostAsset | None
    ports: list[ScanPortOut]
    findings: list[FindingOut] = []
    risk_score: float | None = None  # the asset's score computed from this scan
    risk_band: str | None = None


class ScanDetail(ScanOut):
    hosts: list[ScanHostOut]
    matched: int = 0
    new_devices: int = 0
    ip_conflicts: int = 0
