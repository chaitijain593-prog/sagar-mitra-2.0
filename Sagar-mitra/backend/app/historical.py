"""
Sagar Mitra - Phase 3: Historical Data Query Agent (Gemini Function Calling)
==============================================================================
Lets Gemini query the real historical Argo dataset directly and answer
questions like "when was the last marine heatwave near Ratnagiri?" or
generate trend graphs, e.g. "plot temperature over years".

Adapted from the notebook: uses app.data.store.final_dataset instead of a
bare global, and saves plots under ./static/plots (served by FastAPI's
StaticFiles mount) instead of /tmp, returning a URL the frontend can use
directly as an <img src>.
"""
import os
import uuid
from typing import Optional, cast
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from google.genai import types
from google.genai.types import FunctionDeclaration

from app.data import store
from app.advisory import generate_content, LITE_MODEL
from app.llm_cache import TTLCache, normalize_key

PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Full base URL so plot links are directly clickable/pasteable during testing.
# Set SAGAR_MITRA_BASE_URL in .env once deployed (e.g. https://your-app.onrender.com).
BASE_URL = os.environ.get("SAGAR_MITRA_BASE_URL", "http://127.0.0.1:8000")

# Progressively widened search radii (degrees) for region-scoped historical
# queries. Argo floats are open-ocean profiling instruments, not coastal
# sensors -- they don't operate right up against the shoreline, so a
# near-coast query point (e.g. [19.0, 72.8] near Mumbai) can have its
# nearest real profile 2-3 degrees away even though the dataset genuinely
# covers that part of the Arabian Sea. A single fixed ~2-degree box used to
# come up completely empty for exactly that kind of point. Trying wider
# boxes in order (instead of failing at the first one) is what lets a
# coastal query still find the closest real regional data.
_REGION_RADIUS_CANDIDATES = (2.0, 3.0, 5.0, 8.0, 12.0)


def _region_filtered(df: pd.DataFrame, region_lat: Optional[float],
                      region_lon: Optional[float]) -> tuple:
    """
    Filters `df` to a lat/lon bounding box around (region_lat, region_lon),
    trying _REGION_RADIUS_CANDIDATES in increasing order and stopping at
    the first radius that actually contains data.

    Returns (filtered_df, radius_used). radius_used is None when no region
    was given at all (the whole dataset is returned, unfiltered -- e.g. a
    global "when was the highest recorded temperature" question), or the
    widest radius tried if even that came up empty (so the caller can
    report exactly how far it searched instead of a bare "no data").
    """
    if region_lat is None or region_lon is None:
        return df, None
    for radius in _REGION_RADIUS_CANDIDATES:
        subset = df[(df["LATITUDE"].between(region_lat - radius, region_lat + radius)) &
                    (df["LONGITUDE"].between(region_lon - radius, region_lon + radius))]
        if not subset.empty:
            return subset, radius
    return df.iloc[0:0], _REGION_RADIUS_CANDIDATES[-1]


# ---------------------------------------------------------------------------
# TOOL FUNCTIONS (Gemini calls these automatically when needed)
# ---------------------------------------------------------------------------

def query_historical_extreme(parameter: str, mode: str, region_lat: Optional[float] = None,
                              region_lon: Optional[float] = None) -> dict:
    """
    Finds the historical max/min/last-occurrence of a parameter.
    parameter: one of 'TEMP','PSAL','PRES'
    mode: 'max' or 'min'
    """
    df, radius_used = _region_filtered(store.final_dataset, region_lat, region_lon)
    if df.empty or parameter not in df.columns:
        if radius_used is not None:
            return {"error": f"No matching data found within {radius_used:g} degrees of this region."}
        return {"error": "No matching data found."}

    column = cast(pd.Series, df[parameter])
    row = df.loc[column.idxmax()] if mode == "max" else df.loc[column.idxmin()]
    return {
        "value": float(row[parameter]),
        "date": str(row.get("JULD", "unknown")),
        "lat": float(row["LATITUDE"]), "lon": float(row["LONGITUDE"]),
        "search_radius_deg": radius_used,
    }


def get_yearly_trend(parameter: str, region_lat: Optional[float] = None,
                      region_lon: Optional[float] = None) -> dict:
    """Returns yearly average of a parameter for trend/graph questions."""
    df, radius_used = _region_filtered(store.final_dataset, region_lat, region_lon)
    if df.empty:
        return {"years": [], "values": [], "search_radius_deg": radius_used}
    df = df.copy()
    juld = cast(pd.Series, df["JULD"])
    df["YEAR"] = pd.to_datetime(juld).dt.year
    yearly = cast(pd.Series, df.groupby("YEAR")[parameter].mean()).dropna()
    return {"years": yearly.index.tolist(), "values": yearly.to_numpy().round(2).tolist(),
            "search_radius_deg": radius_used}


def plot_yearly_trend(parameter: str, region_lat: Optional[float] = None,
                       region_lon: Optional[float] = None) -> dict:
    """Generates and saves a trend graph, returns the file path + public URL."""
    data = get_yearly_trend(parameter, region_lat, region_lon)
    if not data["years"]:
        # Report honestly instead of saving a blank/empty chart image -- an
        # empty plot with a "chart generated" message would be worse than
        # no chart at all.
        radius = data.get("search_radius_deg")
        detail = f" within {radius:g} degrees of this region" if radius is not None else ""
        return {"error": f"No {parameter} data found{detail} to plot."}

    plt.figure(figsize=(8, 4))
    plt.plot(data["years"], data["values"], marker="o")
    plt.title(f"{parameter} Trend Over Years")
    plt.xlabel("Year")
    plt.ylabel(parameter)
    plt.grid(True)

    filename = f"{parameter}_trend_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(PLOTS_DIR, filename)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return {"file_path": path, "url": f"{BASE_URL}/static/plots/{filename}"}


def plot_category_distribution(parameter: str = "TEMP", region_lat: Optional[float] = None,
                                region_lon: Optional[float] = None) -> dict:
    """
    Generates a colored pie chart showing what % of historical SURFACE
    (<=30m) readings fall into each anomaly category (Cold / Normal / Warm /
    Hot), based on the real calibrated surface climatology. Use when user
    asks for a 'pie chart' or 'distribution' or 'breakdown' of conditions.
    """
    surface_df = cast(pd.DataFrame, store.final_dataset[store.final_dataset["PRES"] <= 30])  # surface-only, matches the climatology baseline
    df, _radius_used = _region_filtered(surface_df, region_lat, region_lon)
    mu = store.calibrated_clim["temp"]["mu"]
    sigma = store.calibrated_clim["temp"]["sigma"] or 0.9
    z = (df["TEMP"] - mu) / sigma

    labels = ["Cold (z<-1)", "Normal (-1..1)", "Warm (1..2)", "Hot (z>2)"]
    counts = [
        int((z < -1).sum()),
        int(((z >= -1) & (z <= 1)).sum()),
        int(((z > 1) & (z <= 2)).sum()),
        int((z > 2).sum()),
    ]
    colors = ["#4A90D9", "#7ED957", "#F5A623", "#D0021B"]

    present = [(l, c, col) for l, c, col in zip(labels, counts, colors) if c > 0]
    if not present:
        present = [("No data", 1, "#CCCCCC")]
    plot_labels = [p[0] for p in present]
    plot_counts = [p[1] for p in present]
    plot_colors = [p[2] for p in present]

    plt.figure(figsize=(7, 6))
    wedges, _, autotexts = plt.pie(
        plot_counts, colors=plot_colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.8,
    )
    plt.legend(wedges, plot_labels, title="Condition", loc="center left",
               bbox_to_anchor=(1.0, 0.5))
    plt.title(f"{parameter} Surface Condition Distribution")
    plt.tight_layout()

    filename = f"{parameter}_piechart_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(PLOTS_DIR, filename)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return {"file_path": path, "url": f"{BASE_URL}/static/plots/{filename}", "counts": dict(zip(labels, counts))}


TOOLS = [
    {
        "name": "query_historical_extreme",
        "description": "Find historical max/min value of a parameter (TEMP, PSAL, PRES), e.g. 'when was the last marine heatwave' or 'highest recorded salinity'.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {"type": "string", "enum": ["TEMP", "PSAL", "PRES"]},
                "mode": {"type": "string", "enum": ["max", "min"]},
                "region_lat": {"type": "number"},
                "region_lon": {"type": "number"},
            },
            "required": ["parameter", "mode"],
        },
    },
    {
        "name": "get_yearly_trend",
        "description": "Get yearly averages of a parameter over time for a region, for trend questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {"type": "string", "enum": ["TEMP", "PSAL", "PRES"]},
                "region_lat": {"type": "number"},
                "region_lon": {"type": "number"},
            },
            "required": ["parameter"],
        },
    },
    {
        "name": "plot_yearly_trend",
        "description": "Generate a graph image of a parameter's trend over years. Use when user asks for a 'graph', 'chart', or 'plot'.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {"type": "string", "enum": ["TEMP", "PSAL", "PRES"]},
                "region_lat": {"type": "number"},
                "region_lon": {"type": "number"},
            },
            "required": ["parameter"],
        },
    },
    {
        "name": "plot_category_distribution",
        "description": "Generate a colored PIE CHART showing the breakdown/distribution of ocean temperature conditions (Cold/Normal/Warm/Hot) as percentages. Use when user asks for a 'pie chart', 'distribution', or 'breakdown'.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameter": {"type": "string", "enum": ["TEMP"]},
                "region_lat": {"type": "number"},
                "region_lon": {"type": "number"},
            },
            "required": [],
        },
    },
]

_FUNCTION_MAP = {
    "query_historical_extreme": query_historical_extreme,
    "get_yearly_trend": get_yearly_trend,
    "plot_yearly_trend": plot_yearly_trend,
    "plot_category_distribution": plot_category_distribution,
}


_historical_cache = TTLCache(ttl_seconds=3600)  # historical archive data doesn't change minute to minute


def sagar_mitra_historical_query(user_message: str, persona: str = "Researcher",
                                  language: str = "English", model: str = LITE_MODEL) -> dict:
    """
    Answers historical/trend questions using function calling against the
    real dataset. Returns a dict: {reply, mode, plot_url (if a graph was made)}.

    Cached by (message, persona, language): identical/near-identical
    questions against data that hasn't changed are served from cache
    instead of spending another call. Only ONE Gemini call per question now
    (tool selection, on the lite model -- see advisory.LITE_MODEL): the
    numeric result is formatted into plain text in Python rather than with a
    second "phrase this nicely" call, since app/graph.py's top-level
    synthesizer already does that localization/persona pass once for the
    whole combined response -- a dedicated phrasing call here would just be
    translating the same numbers twice, in two separate model calls.
    """
    cache_key = normalize_key(user_message, persona, language)
    cached = _historical_cache.get(cache_key)
    if cached is not None:
        return cached
    result = _run_historical_query(user_message, model)
    if result.get("reply"):  # never cache an empty/failed result
        _historical_cache.set(cache_key, result)
    return result


def _format_tool_result(fn_name: str, fn_args: dict, result: dict) -> str:
    """Plain-Python (no LLM call) formatting of a tool's raw numeric result
    into a sentence the top-level synthesizer can localize/phrase later."""
    if "error" in result:
        return result["error"]

    if fn_name == "query_historical_extreme":
        mode = fn_args.get("mode", "value")
        parameter = fn_args.get("parameter", "value")
        return (f"Historical {mode} {parameter}: {result.get('value')}, recorded on "
                f"{result.get('date')} near ({result.get('lat')}, {result.get('lon')}).")

    if fn_name == "get_yearly_trend":
        parameter = fn_args.get("parameter", "value")
        pairs = ", ".join(f"{y}: {v}" for y, v in zip(result.get("years", []), result.get("values", [])))
        if pairs:
            return f"Yearly {parameter} averages -- {pairs}."
        radius = result.get("search_radius_deg")
        detail = f" within {radius:g} degrees of this region" if radius is not None else " for this region"
        return f"No yearly {parameter} data found{detail}."

    if fn_name == "plot_yearly_trend":
        parameter = fn_args.get("parameter", "value")
        return f"Generated a {parameter} trend chart over the available years: {result.get('url')}"

    if fn_name == "plot_category_distribution":
        breakdown = ", ".join(f"{k}: {v}" for k, v in result.get("counts", {}).items())
        return f"Generated a condition-distribution chart ({breakdown}): {result.get('url')}"

    return str(result)


def _run_historical_query(user_message: str, model: str) -> dict:
    tool = types.Tool(function_declarations=cast(list[FunctionDeclaration], TOOLS))
    config = types.GenerateContentConfig(
        tools=[tool],
        system_instruction=(
            "You are ORCA's historical ocean-data tool selector. Call the ONE tool that "
            "best answers the user's question. Never guess numbers - always call a tool first."
        ),
    )

    response = generate_content(model=model, contents=user_message, config=config)

    if not response.candidates or not response.candidates[0].content:
        return {"reply": response.text or "", "mode": "historical", "plot_url": None}

    call_content = response.candidates[0].content
    parts = call_content.parts
    if not parts:
        return {"reply": response.text or "", "mode": "historical", "plot_url": None}
    part = parts[0]
    if part.function_call and part.function_call.name:
        fn_name = part.function_call.name
        fn_args = dict(part.function_call.args or {})
        result = _FUNCTION_MAP[fn_name](**fn_args)

        reply = _format_tool_result(fn_name, fn_args, result)
        plot_url = result.get("url") if fn_name in ("plot_yearly_trend", "plot_category_distribution") else None
        return {"reply": reply, "mode": "historical", "plot_url": plot_url}

    return {"reply": response.text or "", "mode": "historical", "plot_url": None}