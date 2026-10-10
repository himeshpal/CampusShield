import ipaddress
import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AssetType = Literal[
    "server",
    "workstation",
    "wifi_ap",
    "iot_cctv",
    "iot_biometric",
    "printer",
    "network_device",
    "other",
]
AssetStatus = Literal["registered", "unregistered", "retired"]
Criterion = Annotated[int, Field(ge=1, le=3)]
ShortText = Annotated[str, Field(max_length=120)]

_MAC = re.compile(r"^[0-9a-f]{2}([:-]?)[0-9a-f]{2}(\1[0-9a-f]{2}){4}$")


def normalize_mac(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    mac = value.strip().lower()
    if not _MAC.match(mac):
        raise ValueError("MAC address must look like 3c:d9:2b:10:00:10")
    digits = re.sub(r"[^0-9a-f]", "", mac)
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


def normalize_ip(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        raise ValueError("Enter a valid IP address") from None


def criticality_level(total: int) -> str:
    # four criteria of 1-3 each -> 4..12
    return "high" if total >= 10 else "medium" if total >= 7 else "low"


class AssetFields(BaseModel):
    """Editable fields shared by create, update and register."""

    name: str = Field(min_length=2, max_length=120)
    hostname: ShortText | None = None
    asset_type: AssetType = "other"
    ip_address: str | None = None
    mac_address: str | None = None
    os_name: ShortText | None = None
    department: ShortText | None = None
    location: ShortText | None = None
    owner: ShortText | None = None
    notes: str | None = Field(default=None, max_length=2000)
    data_sensitivity: Criterion = 2
    service_dependency: Criterion = 2
    users_affected: Criterion = 2
    replaceability: Criterion = 2
    baseline_ports: list[Annotated[int, Field(ge=1, le=65535)]] = []

    @field_validator("ip_address")
    @classmethod
    def _ip(cls, v: str | None) -> str | None:
        return normalize_ip(v)

    @field_validator("mac_address")
    @classmethod
    def _mac(cls, v: str | None) -> str | None:
        return normalize_mac(v)

    @field_validator("baseline_ports")
    @classmethod
    def _ports(cls, v: list[int]) -> list[int]:
        return sorted(set(v))


class AssetUpdate(BaseModel):
    """Partial update; every field optional."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    hostname: ShortText | None = None
    asset_type: AssetType | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    os_name: ShortText | None = None
    department: ShortText | None = None
    location: ShortText | None = None
    owner: ShortText | None = None
    notes: str | None = Field(default=None, max_length=2000)
    data_sensitivity: Criterion | None = None
    service_dependency: Criterion | None = None
    users_affected: Criterion | None = None
    replaceability: Criterion | None = None
    baseline_ports: list[Annotated[int, Field(ge=1, le=65535)]] | None = None
    status: AssetStatus | None = None

    @field_validator("ip_address")
    @classmethod
    def _ip(cls, v: str | None) -> str | None:
        return normalize_ip(v)

    @field_validator("mac_address")
    @classmethod
    def _mac(cls, v: str | None) -> str | None:
        return normalize_mac(v)

    @field_validator("baseline_ports")
    @classmethod
    def _ports(cls, v: list[int] | None) -> list[int] | None:
        return sorted(set(v)) if v is not None else None


class ObservedPort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port: int
    protocol: str
    service: str | None
    product: str | None
    version: str | None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_tag: str
    name: str | None
    hostname: str | None
    asset_type: str
    status: AssetStatus
    ip_address: str | None
    mac_address: str | None
    mac_vendor: str | None
    os_name: str | None
    department: str | None
    location: str | None
    owner: str | None
    notes: str | None
    data_sensitivity: int
    service_dependency: int
    users_affected: int
    replaceability: int
    baseline_ports: list[int]
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    # derived
    criticality: int = 0
    criticality_level: str = "low"
    observed_ports: list[ObservedPort] | None = None  # from the latest scan that saw it
    last_scan_id: int | None = None


class Observation(BaseModel):
    scan_id: int
    scanned_at: datetime
    profile: str
    ip_address: str
    match_method: str | None
    ports: list[ObservedPort]


class AssetDetail(AssetOut):
    observations: list[Observation]


class AssetSummary(BaseModel):
    registered: int
    unregistered: int
    retired: int
    by_type: dict[str, int]
