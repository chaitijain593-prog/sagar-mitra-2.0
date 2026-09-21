"""
Sagar Mitra / ORCA - Offline "Morning Dispatch"
====================================================================
Every other endpoint in this backend assumes a live connection for each
individual query. This module is different on purpose: it builds ONE
downloadable pre-departure briefing (a PDF + a spoken audio version) that a
fisherman generates once, while still online in port, then reads or plays
back later with no connectivity at sea.

Reuses the exact same live-data tools graph.py's dispatch_node already
calls for every /api/orchestrate request (see _fetch_common_signals there)
plus regional_scan.py's zone ranking -- run ONCE here instead of once per
chat turn. Narration goes through the same Gemini synthesis call every
other advisory uses (advisory.synthesize_advisory), and falls back to the
same deterministic, no-LLM-call formatter (response_formatter.py) that the
rest of the pipeline already relies on when Gemini is unavailable -- so a
quota hit the morning a boat is leaving port still produces a usable
briefing instead of nothing at all.

Install dependency:
    pip install reportlab
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.boundary_toool import check_maritime_boundary
from app.satellite_tool import get_live_ocean_conditions
from app.pfz_tool import get_nearest_pfz
from app.chlorophyll_tool import get_chlorophyll_data
from app.weather_alert_tool import get_weather_hazard_alerts
from app.regional_scan import scan_favorable_regions, format_regional_scan
from app.advisory import synthesize_advisory
from app.response_formatter import format_fallback_advisory
from app.voice import synthesize_speech

# Same static/ mount main.py already serves (see main.py's StaticFiles
# mount and historical.py's identical PLOTS_DIR / voice.py's AUDIO_DIR
# pattern) -- no new server config needed for these files to be reachable.
DISPATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dispatch")
os.makedirs(DISPATCH_DIR, exist_ok=True)

BASE_URL = os.environ.get("SAGAR_MITRA_BASE_URL", "http://127.0.0.1:8000")

_HAZARD_FALLBACK = {
    "lightning_alert": False, "lightning_detail": "Hazard data unavailable.",
    "cyclone_alert": False, "cyclone_detail": "Hazard data unavailable.",
    "summary": "Hazard data unavailable.",
}

_BRAND_NAVY = colors.HexColor("#0f2540")
_BRAND_CYAN = colors.HexColor("#0f6ea3")


def _forecast_label(day_offset: int, target_hour: Optional[int]) -> str:
    """Same date/time labeling main.py's run_orchestration uses for
    `forecast_for`, so a dispatch generated for "tomorrow morning" is
    clearly marked as such rather than looking like live/current data."""
    hour = target_hour if target_hour is not None else 8
    target_date = (date.today() + timedelta(days=max(day_offset, 0))).isoformat()
    return f"{target_date} {hour:02d}:00"


def _fetch_dispatch_signals(lat: float, lon: float, day_offset: int, target_hour: Optional[int]) -> dict:
    """Fires the same 5 common live-data lookups graph.py's dispatch_node
    fetches on every chat turn, plus a regional favorability scan, all
    concurrently (I/O-bound calls -- same thread-pool pattern used
    throughout this backend) since a dispatch is generated once, not
    per-query, so there's no reason to pay for them serially."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            "boundary_report": pool.submit(check_maritime_boundary, lat, lon),
            "ocean_report": pool.submit(get_live_ocean_conditions, lat, lon,
                                         day_offset=day_offset, target_hour=target_hour),
            "pfz_report": pool.submit(get_nearest_pfz, lat, lon),
            "chlorophyll_report": pool.submit(get_chlorophyll_data, lat, lon),
            "hazard_report": pool.submit(get_weather_hazard_alerts, lat, lon,
                                          day_offset=day_offset, target_hour=target_hour),
            "regional_zones": pool.submit(scan_favorable_regions, 5),
        }
        signals = {}
        for key, future in futures.items():
            try:
                signals[key] = future.result()
            except Exception as e:
                print(f"[dispatch] '{key}' fetch failed: {e}")
                signals[key] = dict(_HAZARD_FALLBACK) if key == "hazard_report" else (
                    [] if key == "regional_zones" else f"Data unavailable: {e}"
                )
        return signals


def _build_agent_reports(signals: dict) -> dict:
    """Structured {section: text} dict, keyed exactly like
    response_formatter.AGENT_DISPLAY_NAMES so format_fallback_advisory can
    render it directly if Gemini synthesis isn't available below."""
    hazard = signals.get("hazard_report") or _HAZARD_FALLBACK
    zones = signals.get("regional_zones") or []
    return {
        "navigation": signals.get("ocean_report") or "Sea state data unavailable.",
        "fishing": f"{signals.get('pfz_report', '')} | {signals.get('chlorophyll_report', '')}",
        "compliance": signals.get("boundary_report") or "Boundary data unavailable.",
        "hazard": f"{hazard['lightning_detail']} {hazard['cyclone_detail']}",
        "regional": format_regional_scan(zones),
    }


def _build_narrative(agent_reports: dict, persona: str, language: str) -> tuple[str, bool]:
    """Returns (narrative_text, degraded). Tries the same Gemini synthesis
    path every live advisory uses; on any failure (quota/outage) falls back
    to the deterministic, per-section formatter instead of blocking dispatch
    generation entirely -- exactly the pattern graph.py's synthesizer_node
    already uses for the live chat flow."""
    raw_report = "\n\n".join(v for v in agent_reports.values() if v)
    try:
        narrative = synthesize_advisory(
            raw_report=raw_report,
            persona=persona,
            language=language,
            user_message="Prepare my Morning Dispatch briefing before I leave port today.",
        )
        return narrative, False
    except Exception as e:
        print(f"[dispatch] Gemini synthesis unavailable, using deterministic fallback: {e}")
        return format_fallback_advisory(agent_reports, language=language, degraded=True), True


def _render_pdf(lat: float, lon: float, signals: dict, narrative: str,
                 forecast_label: str) -> str:
    filename = f"dispatch_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(DISPATCH_DIR, filename)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DispatchTitle", parent=styles["Title"], textColor=_BRAND_NAVY)
    heading_style = ParagraphStyle("DispatchHeading", parent=styles["Heading2"],
                                    textColor=_BRAND_CYAN, spaceBefore=14, spaceAfter=4)
    body_style = ParagraphStyle("DispatchBody", parent=styles["BodyText"], leading=15)
    meta_style = ParagraphStyle("DispatchMeta", parent=styles["BodyText"], textColor=colors.grey, fontSize=9)
    footer_style = ParagraphStyle("DispatchFooter", parent=styles["Italic"], textColor=colors.grey, fontSize=8)

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                             leftMargin=2 * cm, rightMargin=2 * cm)
    story = [
        Paragraph("Sagar Mitra — Morning Dispatch", title_style),
        Paragraph(
            f"Location: [{lat}, {lon}] &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Generated: {date.today().isoformat()} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Covers: {forecast_label}",
            meta_style,
        ),
        Spacer(1, 12),
        Paragraph("Today's Briefing", heading_style),
    ]
    for para in narrative.split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), body_style))
            story.append(Spacer(1, 6))

    story.append(Paragraph("Sea State &amp; Tides", heading_style))
    story.append(Paragraph(signals.get("ocean_report") or "Data unavailable.", body_style))

    story.append(Paragraph("Nearest Fishing Zone", heading_style))
    story.append(Paragraph(signals.get("pfz_report") or "Data unavailable.", body_style))
    if signals.get("chlorophyll_report"):
        story.append(Paragraph(signals["chlorophyll_report"], body_style))

    story.append(Paragraph("Hazard Alerts", heading_style))
    hazard = signals.get("hazard_report") or _HAZARD_FALLBACK
    story.append(Paragraph(f"{hazard['lightning_detail']} {hazard['cyclone_detail']}", body_style))

    story.append(Paragraph("Boundary &amp; Compliance", heading_style))
    story.append(Paragraph(signals.get("boundary_report") or "Data unavailable.", body_style))

    zones = signals.get("regional_zones") or []
    story.append(Paragraph("Top Favorable Zones Today", heading_style))
    if zones:
        table_data = [["#", "Zone", "Chlorophyll (mg/m3)", "SST (C)", "ML Confidence"]]
        for i, z in enumerate(zones, 1):
            ml = f"{z['ml_confidence_pct']}%" if z.get("ml_confidence_pct") is not None else "N/A"
            table_data.append([
                str(i), z.get("name", "Unnamed"),
                str(z.get("chlorophyll_mgm3")), str(z.get("sst_c")), ml,
            ])
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No regional zone data available right now.", body_style))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Generated while online, for offline reference at sea. Conditions can change -- "
        "re-check ORCA once connectivity returns.",
        footer_style,
    ))

    doc.build(story)
    return f"{BASE_URL}/static/dispatch/{filename}"


def _render_audio(narrative: str, language: str) -> Optional[str]:
    """Spoken version of the exact same narrative text used in the PDF.
    Returns None (not an exception) on failure -- a dispatch with a PDF but
    no audio is still useful; the caller should never fail the whole
    request just because TTS hit a quota (same policy main.py's
    /api/voice/orchestrate already applies to advisory audio)."""
    try:
        audio_bytes = synthesize_speech(narrative, language=language)
    except Exception as e:
        print(f"[dispatch] audio synthesis failed, returning PDF-only dispatch: {e}")
        return None
    filename = f"dispatch_{uuid.uuid4().hex[:8]}.wav"
    path = os.path.join(DISPATCH_DIR, filename)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return f"{BASE_URL}/static/dispatch/{filename}"


def generate_morning_dispatch(
    lat: float,
    lon: float,
    persona: str = "Fisherman",
    language: str = "English",
    day_offset: int = 0,
    target_hour: Optional[int] = 8,
) -> dict:
    """
    Builds today's (or a future day's) Morning Dispatch for (lat, lon): a
    PDF report plus a spoken audio version, both saved under
    static/dispatch/ and returned as public URLs the frontend can hand
    straight to a download link / <audio> element.

    Meant to be called ONCE, while still online in port, before a vessel
    loses connectivity -- see main.py's POST /api/dispatch/generate.

    Returns:
        {
          "pdf_url": str,
          "audio_url": str | None,      # None if TTS failed -- PDF is still returned
          "narrative": str,             # the plain-text briefing used for both PDF and audio
          "degraded": bool,             # True if Gemini synthesis was unavailable
          "coordinates": [lat, lon],
          "generated_at": str,          # ISO date this dispatch was generated
          "forecast_for": str,          # date + hour the briefing's conditions describe
        }
    """
    signals = _fetch_dispatch_signals(lat, lon, day_offset, target_hour)
    agent_reports = _build_agent_reports(signals)
    narrative, degraded = _build_narrative(agent_reports, persona, language)
    forecast_label = _forecast_label(day_offset, target_hour)

    pdf_url = _render_pdf(lat, lon, signals, narrative, forecast_label)
    audio_url = _render_audio(narrative, language)

    return {
        "pdf_url": pdf_url,
        "audio_url": audio_url,
        "narrative": narrative,
        "degraded": degraded,
        "coordinates": [lat, lon],
        "generated_at": date.today().isoformat(),
        "forecast_for": forecast_label,
    }


if __name__ == "__main__":
    # Test coordinate off the Ratnagiri coast
    result = generate_morning_dispatch(16.99, 73.30)
    print({k: v for k, v in result.items() if k != "narrative"})
    print("Narrative preview:", result["narrative"][:300])
