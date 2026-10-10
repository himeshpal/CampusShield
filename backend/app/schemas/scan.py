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


class ScanHostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    mac_address: str | None
    mac_vendor: str | None
    hostname: str | None
    os_guess: str | None
    ports: list[ScanPortOut]


class ScanDetail(ScanOut):
    hosts: list[ScanHostOut]
