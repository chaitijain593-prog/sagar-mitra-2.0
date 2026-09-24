"""Deterministic hazard status derived from gathered live reports."""


def derive_hazard_status(boundary_report: str, ocean_report: str, hazard_report: dict) -> str:
    if boundary_report.startswith("ALERT"):
        return "HAZARDOUS"
    if "HAZARDOUS" in ocean_report.upper():
        return "HAZARDOUS"
    if hazard_report.get("cyclone_alert"):
        return "HAZARDOUS"
    if hazard_report.get("lightning_alert"):
        return "CAUTION"
    if boundary_report.startswith("UNVERIFIED"):
        return "CAUTION"
    return "SAFE"
