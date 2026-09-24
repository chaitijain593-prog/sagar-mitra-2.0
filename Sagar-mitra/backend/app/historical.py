"""
Sagar Mitra - Phase 3: Historical Data Query Agent (OpenAI Function Calling)
==============================================================================
Lets OpenAI query the real historical Argo dataset directly and answer
questions like "when was the last marine heatwave near Ratnagiri?" or
generate trend graphs, e.g. "plot temperature over years".

Adapted from the notebook: uses app.data.store.final_dataset instead of a
bare global. Plot images are rendered straight to an in-memory buffer and
returned as a base64 data: URI -- never written to disk -- so a query that
generates a new chart doesn't drop a new file under the (frontend-nested)
static/ tree on every request. That used to trigger local live-reload dev
tooling (e.g. VS Code Live Server watching the whole workspace) into
reloading the page mid-conversation, since backend/static/plots/ sits
inside the same directory tree the frontend is served from.
"""
import base64
import json
from io import BytesIO
from typing import Optional, cast
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from app.data import store
from app.db import query_argo_bbox
from app.db_store import get_hazard_mesh
from app.advisory import get_openai_client, LITE_MODEL
from app.llm_cache import TTLCache, normalize_key


def _fig_to_data_url() -> str:
    """Renders the current matplotlib figure to a base64 PNG data: URI and
    closes it -- no disk write, so nothing for a file watcher to see."""
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

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
# TOOL FUNCTIONS (OpenAI calls these automatically when needed)
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
    """Generates a trend graph, returns it as a base64 data: URL (no disk write -- see _fig_to_data_url)."""
    data = get_yearly_trend(parameter, region_lat, region_lon)
    if not data["years"]:
        # Report honestly instead of rendering a blank/empty chart image -- an
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

    data_url = _fig_to_data_url()
    # Real Chart.js series alongside the image -- lets the frontend render an
    # interactive line chart instead of only an <img> of the matplotlib plot.
    series = {
        "chart_type": "line",
        "parameter": parameter,
        "labels": [str(y) for y in data["years"]],
        "values": data["values"],
    }
    return {"url": data_url, "series": series}


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

    data_url = _fig_to_data_url()
    # Real Chart.js series alongside the image -- lets the frontend render an
    # interactive pie/doughnut chart instead of only an <img> of the matplotlib plot.
    series = {
        "chart_type": "pie",
        "parameter": parameter,
        "labels": plot_labels,
        "values": plot_counts,
    }
    return {"url": data_url, "counts": dict(zip(labels, counts)), "series": series}


# Raw hazard_mesh `type` values (see db_store.insert_hazard_point / main.py's
# HazardReportRequest) mapped to a human-readable label for the pie chart
# legend. Anything not in this map falls back to a title-cased version of
# the raw type instead of silently dropping it.
_HAZARD_TYPE_LABELS = {
    "net": "Ghost Nets",
    "oil_slick": "Oil Slick",
    "debris": "Floating Debris",
}


def plot_hazard_category_distribution() -> dict:
    """
    Generates a pie chart of REAL crowdsourced hazard mesh reports (Feature
    7 -- db_store.get_hazard_mesh, TTL-filtered to the last 24h), broken
    down by hazard type -- distinct from plot_category_distribution above,
    which charts Argo *temperature* conditions, not hazard reports. Use
    when the user asks about 'hazard categories'/'hazard breakdown'/'types
    of hazards reported'.

    Called directly (no parameters, no region filter -- the hazard mesh is
    small enough to summarize in full) from _run_historical_query's
            deterministic fast path for this exact query shape, bypassing OpenAI's
    tool-selection call entirely; also registered in TOOLS below so OpenAI
    can still pick it for a differently-phrased hazard question.
    """
    reports = get_hazard_mesh()
    counts_by_type: dict = {}
    for report in reports:
        raw_type = report.get("type") or "unknown"
        counts_by_type[raw_type] = counts_by_type.get(raw_type, 0) + 1

    palette = ["#4A90D9", "#D0021B", "#F5A623", "#7ED957", "#a78bfa", "#f472b6"]
    present = [
        (_HAZARD_TYPE_LABELS.get(t, t.replace("_", " ").title()), c, palette[i % len(palette)])
        for i, (t, c) in enumerate(counts_by_type.items())
    ]
    if not present:
        present = [("No hazard reports in the last 24h", 1, "#CCCCCC")]
    plot_labels = [p[0] for p in present]
    plot_counts = [p[1] for p in present]
    plot_colors = [p[2] for p in present]

    plt.figure(figsize=(7, 6))
    wedges, _, autotexts = plt.pie(
        plot_counts, colors=plot_colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.8,
    )
    plt.legend(wedges, plot_labels, title="Hazard Type", loc="center left",
               bbox_to_anchor=(1.0, 0.5))
    plt.title("Crowdsourced Hazard Category Breakdown (last 24h)")
    plt.tight_layout()

    data_url = _fig_to_data_url()
    series = {
        "chart_type": "pie",
        "parameter": "hazard_type",
        "labels": plot_labels,
        "values": plot_counts,
    }
    return {"url": data_url, "counts": dict(zip(plot_labels, plot_counts)), "series": series}


def query_ocean_sql(lat_min: float, lat_max: float, lon_min: float, lon_max: float,
                     limit: int = 20) -> dict:
    """
    Feature 9 (Natural Language Text-to-SQL Deep Ocean Query Engine): runs a
    real parameterized SQL query (app.db.query_argo_bbox) against the
    SQLite argo_readings table for a lat/lon bounding box. Unlike this
    file's other TOOLS (which filter store.final_dataset with pandas in
    memory), this one is genuinely SQL, and was previously computed
    (db.query_argo_bbox) but never exposed to OpenAI's tool-selection layer.
    """
    df = query_argo_bbox(lat_min, lat_max, lon_min, lon_max, limit=limit)
    if df.empty:
        return {"error": f"No SQL rows found in the box lat[{lat_min},{lat_max}] lon[{lon_min},{lon_max}]."}
    cols = [c for c in ("LATITUDE", "LONGITUDE", "PRES", "TEMP", "PSAL", "JULD") if c in df.columns]
    rows = df[cols].head(limit).astype(object).where(df[cols].notna(), None).to_dict(orient="records")
    return {"row_count": int(len(df)), "rows": rows}


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
    {
        "name": "plot_hazard_category_distribution",
        "description": "Generate a pie chart breaking down CROWDSOURCED HAZARD reports (fishing nets, oil slicks, floating debris) by category from the live hazard mesh -- NOT ocean temperature. Use when user asks about 'hazard categories', 'hazard breakdown', or 'types of hazards reported'.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "query_ocean_sql",
        "description": "Run a direct SQL bounding-box query against the argo_readings SQLite table for a lat/lon region. Use for questions asking for raw rows/records in an area rather than an aggregate trend or extreme, e.g. 'show me readings near 15,72' or 'list ocean data in this box'.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat_min": {"type": "number"},
                "lat_max": {"type": "number"},
                "lon_min": {"type": "number"},
                "lon_max": {"type": "number"},
                "limit": {"type": "integer"},
            },
            "required": ["lat_min", "lat_max", "lon_min", "lon_max"],
        },
    },
]

_FUNCTION_MAP = {
    "query_historical_extreme": query_historical_extreme,
    "get_yearly_trend": get_yearly_trend,
    "plot_yearly_trend": plot_yearly_trend,
    "plot_category_distribution": plot_category_distribution,
    "plot_hazard_category_distribution": plot_hazard_category_distribution,
    "query_ocean_sql": query_ocean_sql,
}


_historical_cache = TTLCache(ttl_seconds=3600)  # historical archive data doesn't change minute to minute


def sagar_mitra_historical_query(user_message: str, persona: str = "Researcher",
                                  language: str = "English", model: str = LITE_MODEL) -> dict:
    """
    Answers historical/trend questions using function calling against the
    real dataset. Returns a dict: {reply, mode, plot_url (if a graph was made)}.

    Cached by (message, persona, language): identical/near-identical
    questions against data that hasn't changed are served from cache
    instead of spending another call. Only ONE OpenAI call per question now
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

    if fn_name == "plot_hazard_category_distribution":
        breakdown = ", ".join(f"{k}: {v}" for k, v in result.get("counts", {}).items())
        return (f"Hazard category breakdown from the last 24h of crowdsourced reports: {breakdown}. "
                f"Chart: {result.get('url')}")

    if fn_name == "query_ocean_sql":
        rows = result.get("rows", [])
        preview = "; ".join(
            f"({r.get('LATITUDE')}, {r.get('LONGITUDE')}) TEMP={r.get('TEMP')} PSAL={r.get('PSAL')}"
            for r in rows[:5]
        )
        return f"SQL query matched {result.get('row_count')} row(s) in argo_readings. First results: {preview}"

    return str(result)


# Narrow, hazard-specific phrasing -- deliberately doesn't overlap with the
# broader generic "pie chart"/"distribution"/"breakdown" wording that
# plot_category_distribution's TOOL description already owns, so a plain
# "pie chart of temperature" request still goes through OpenAI's normal
# tool-selection instead of being hijacked into the hazard breakdown.
_HAZARD_BREAKDOWN_KEYWORDS = ("hazard categories", "hazard breakdown", "hazard distribution", "hazard types")

# Narrow to phrasings that specifically name temperature/SST -- NOT the
# broader "yearly"/"trend of"/"historical" keywords planner.py routes to
# this agent, since those could legitimately ask about salinity, pressure,
# etc. OpenAI's normal tool-selection below already picks the right
# parameter for those; this fast path only short-circuits the unambiguous
# temperature case.
_SST_TREND_KEYWORDS = ("sea surface temperature", "sst", "temperature trend")


def _run_historical_query(user_message: str, model: str) -> dict:
    text_lower = user_message.lower()
    if any(kw in text_lower for kw in _HAZARD_BREAKDOWN_KEYWORDS):
        result = plot_hazard_category_distribution()
        reply = _format_tool_result("plot_hazard_category_distribution", {}, result)
        return {"reply": reply, "mode": "historical", "plot_url": result.get("url"), "series": result.get("series")}

    if any(kw in text_lower for kw in _SST_TREND_KEYWORDS):
        result = plot_yearly_trend(parameter="TEMP")
        reply = _format_tool_result("plot_yearly_trend", {"parameter": "TEMP"}, result)
        return {"reply": reply, "mode": "historical", "plot_url": result.get("url"), "series": result.get("series")}

    response = get_openai_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "You are ORCA's historical ocean-data tool selector. Call the ONE tool that "
                "best answers the user's question. Never guess numbers; always call a tool first."
            )},
            {"role": "user", "content": user_message},
        ],
        tools=[{"type": "function", "function": tool} for tool in TOOLS],
        tool_choice="required",
        temperature=0,
    )
    message = response.choices[0].message
    if not message.tool_calls:
        return {"reply": message.content or "", "mode": "historical", "plot_url": None, "series": None}

    tool_call = message.tool_calls[0]
    fn_name = tool_call.function.name
    if fn_name not in _FUNCTION_MAP:
        raise ValueError(f"OpenAI requested unknown historical tool: {fn_name}")
    fn_args = json.loads(tool_call.function.arguments or "{}")
    result = _FUNCTION_MAP[fn_name](**fn_args)

    reply = _format_tool_result(fn_name, fn_args, result)
    is_chart_tool = fn_name in ("plot_yearly_trend", "plot_category_distribution", "plot_hazard_category_distribution")
    plot_url = result.get("url") if is_chart_tool else None
    series = result.get("series") if is_chart_tool else None
    return {"reply": reply, "mode": "historical", "plot_url": plot_url, "series": series}
