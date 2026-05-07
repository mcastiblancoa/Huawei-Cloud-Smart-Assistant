REGION_OVERRIDES: dict[str, str] = {
    "BSSINTL": "ap-southeast-1",
}

PROJECT_IDS: dict[str, str] = {
    "af-north-1": "ffd9e2abbbac4f888abd9f08b18dbc3d",
    "ap-southeast-1": "1724bd3fa7f745f79110f3ce49128ecb",
    "ap-southeast-3": "c03f2d01969044fc85baef46ba86a6ec",
    "cn-north-4": "a24fcb85b2204db7b2a90e48ebda08f5",
    "cn-south-1": "8358450edaa3433294d4f21fb22e5d3f",
    "la-north-2": "5785afdda6384c71ba92e8dd741b6ff8",
    "la-south-2": "ddee7698ac56487a9b6248f3567af49a",
    "me-east-1": "019dacb4116c733bbc10896f621443fe",
    "na-mexico-1": "4fde7221d82b4f7ca6b02ed0ca52d8b9",
    "sa-brazil-1": "b2ff2698ac56487a9b6248f3567af49a",
}


def resolve_region(service: str, default_region: str) -> str:
    return REGION_OVERRIDES.get(service.upper(), default_region)


def resolve_project_id(region: str, default_project_id: str | None) -> str | None:
    return PROJECT_IDS.get(region, default_project_id)


def needs_domain_id(service: str) -> bool:
    return service.upper() == "RMS"
