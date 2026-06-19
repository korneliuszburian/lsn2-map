"""Render an LSN-styled North America map from real geographic boundaries.

This is the "correct coordinate" counterpart to render_lsn_map_options.py.
The basemap and deployment points are projected with the same CRS, so point
placement does not depend on a hand-drawn artwork transform.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests
from pyproj import Transformer
from shapely.geometry import GeometryCollection, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, transform, unary_union


DEFAULT_INPUT = "data/output/clients_geocoded.csv"
DEFAULT_OUTPUT = "data/output/lsn-map-geographic.html"
DEFAULT_BASEMAP_OUTPUT = "data/output/lsn-north-america-geographic.svg"
DEFAULT_CACHE_DIR = "data/reference"

WIDTH = 1731
HEIGHT = 1800
PADDING_X = 105
PADDING_Y = 70
COUNTRIES = ("US", "CA", "MX")
COUNTRY_COLORS = {"US": "#007f3d", "CA": "#345168", "MX": "#3f3f41"}
COUNTRY_NAMES = {"US": "United States", "CA": "Canada", "MX": "Mexico"}
LINE_COLOR = "rgba(255,255,255,.78)"
PROJECTION_NAME = "North America Albers Equal Area"
PROJECTION = (
    "+proj=aea +lat_1=20 +lat_2=60 +lat_0=40 +lon_0=-96 "
    "+datum=WGS84 +units=m +no_defs"
)

SOURCES = {
    "admin0": "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip",
    "admin1": "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_1_states_provinces.zip",
}


def read_deployments(path: Path) -> list[dict[str, Any]]:
    deployments: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat = _parse_float(row.get("latitude"))
            lon = _parse_float(row.get("longitude"))
            if lat is None or lon is None:
                continue
            deployments.append(
                {
                    "id": row.get("deployment_id", ""),
                    "name": row.get("client_name", ""),
                    "cc": row.get("country_code", ""),
                    "zip": row.get("postal_code_norm", ""),
                    "lat": lat,
                    "lon": lon,
                    "count": _parse_int(row.get("generator_count"), default=1),
                    "model": row.get("generator_model", ""),
                    "status": row.get("install_status", ""),
                    "region": row.get("service_region", ""),
                    "manager": row.get("account_manager", ""),
                    "date": row.get("install_date", ""),
                }
            )
    return deployments


def render_html(input_path: Path, cache_dir: Path, basemap_output: Path, title: str) -> str:
    deployments = read_deployments(input_path)
    if not deployments:
        raise ValueError(f"No geocoded deployments found in {input_path}")

    admin0, admin1 = load_boundaries(cache_dir)
    transformer = Transformer.from_crs("EPSG:4326", PROJECTION, always_xy=True)
    projected_admin0 = [(cc, project_geometry(geom, transformer)) for cc, geom in admin0]
    projected_admin1 = [(cc, project_geometry(geom, transformer)) for cc, geom in admin1]
    projected_union = unary_union([geom for _, geom in projected_admin0])
    display_union = projected_union.buffer(-12_000)
    if display_union.is_empty:
        display_union = projected_union
    viewport = build_viewport([geom for _, geom in projected_admin0])
    basemap_svg = render_basemap_svg(projected_admin0, projected_admin1, viewport)
    write_text(basemap_svg, basemap_output)

    projected_deployments = project_deployments(deployments, transformer, viewport, projected_union, display_union)
    svg_data = "data:image/svg+xml;base64," + base64.b64encode(basemap_svg.encode("utf-8")).decode("ascii")
    generated_at = datetime.now(timezone.utc).isoformat()

    replacements = {
        "__TITLE__": title,
        "__DEPLOYMENTS_JSON__": json.dumps(projected_deployments, ensure_ascii=True, separators=(",", ":")),
        "__MAP_IMAGE__": svg_data,
        "__IMAGE_WIDTH__": str(WIDTH),
        "__IMAGE_HEIGHT__": str(HEIGHT),
        "__GENERATED_AT__": generated_at,
        "__SOURCE_CSV__": str(input_path),
        "__BASEMAP_SVG__": str(basemap_output),
        "__PROJECTION__": PROJECTION_NAME,
    }
    html_text = HTML_TEMPLATE
    for marker, value in replacements.items():
        html_text = html_text.replace(marker, value)
    return html_text


def load_boundaries(cache_dir: Path) -> tuple[list[tuple[str, BaseGeometry]], list[tuple[str, BaseGeometry]]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    admin0_zip = download(SOURCES["admin0"], cache_dir / "ne_50m_admin_0_countries.zip")
    admin1_zip = download(SOURCES["admin1"], cache_dir / "ne_50m_admin_1_states_provinces.zip")

    admin0_gdf = gpd.read_file(admin0_zip)
    admin1_gdf = gpd.read_file(admin1_zip)

    admin0_rows: list[tuple[str, BaseGeometry]] = []
    for _, row in admin0_gdf.iterrows():
        cc = country_code(row)
        if cc not in COUNTRIES:
            continue
        geom = filter_operational_geometry(row.geometry)
        if not geom.is_empty:
            admin0_rows.append((cc, geom))

    admin1_rows: list[tuple[str, BaseGeometry]] = []
    for _, row in admin1_gdf.iterrows():
        cc = country_code(row)
        if cc not in COUNTRIES:
            continue
        geom = filter_operational_geometry(row.geometry)
        if not geom.is_empty:
            admin1_rows.append((cc, geom))

    if not admin0_rows:
        raise ValueError("Natural Earth admin0 selection returned no geometries")
    return admin0_rows, admin1_rows


def download(url: str, dest: Path) -> Path:
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    print(f"Downloading {url}", flush=True)
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def country_code(row: Any) -> str:
    for key in ("ISO_A2", "iso_a2", "adm0_a3", "ADM0_A3"):
        value = row.get(key)
        if value in ("US", "USA"):
            return "US"
        if value in ("CA", "CAN"):
            return "CA"
        if value in ("MX", "MEX"):
            return "MX"
    name = str(row.get("admin") or row.get("ADMIN") or row.get("geonunit") or row.get("name") or "")
    if name in ("United States of America", "United States"):
        return "US"
    if name == "Canada":
        return "CA"
    if name == "Mexico":
        return "MX"
    return ""


def filter_operational_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Keep mainland North America plus Alaska; drop Hawaii/Pacific outliers."""
    extent = box(-170, 14, -50, 84)

    def keep_polygon(poly: Polygon) -> bool:
        clipped = poly.intersection(extent)
        if clipped.is_empty:
            return False
        p = clipped.representative_point()
        if p.x < -140 and p.y < 45:
            return False
        return True

    polygons: list[Polygon] = []
    for poly in iter_polygons(geom):
        if keep_polygon(poly):
            clipped = poly.intersection(extent)
            polygons.extend(iter_polygons(clipped))

    if not polygons:
        return GeometryCollection()
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)


def iter_polygons(geom: BaseGeometry) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if isinstance(geom, GeometryCollection):
        out: list[Polygon] = []
        for part in geom.geoms:
            out.extend(iter_polygons(part))
        return out
    return []


def project_geometry(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    return transform(transformer.transform, geom)


def build_viewport(geometries: list[BaseGeometry]) -> dict[str, float]:
    minx, miny, maxx, maxy = unary_union(geometries).bounds
    scale = min((WIDTH - PADDING_X * 2) / (maxx - minx), (HEIGHT - PADDING_Y * 2) / (maxy - miny))
    rendered_width = (maxx - minx) * scale
    rendered_height = (maxy - miny) * scale
    offset_x = (WIDTH - rendered_width) / 2 - minx * scale
    offset_y = (HEIGHT - rendered_height) / 2 + maxy * scale
    return {
        "minx": minx,
        "miny": miny,
        "maxx": maxx,
        "maxy": maxy,
        "scale": scale,
        "offset_x": offset_x,
        "offset_y": offset_y,
    }


def to_svg_point(x: float, y: float, viewport: dict[str, float]) -> tuple[float, float]:
    return x * viewport["scale"] + viewport["offset_x"], viewport["offset_y"] - y * viewport["scale"]


def render_basemap_svg(
    admin0: list[tuple[str, BaseGeometry]],
    admin1: list[tuple[str, BaseGeometry]],
    viewport: dict[str, float],
) -> str:
    country_paths = []
    for cc, geom in admin0:
        path = geometry_to_path(geom.simplify(5_000, preserve_topology=True), viewport)
        country_paths.append(
            f'<path class="country country-{cc}" d="{path}" fill="{COUNTRY_COLORS[cc]}" '
            'stroke="#ffffff" stroke-width="1.7" stroke-linejoin="round"/>'
        )

    subdivision_paths = []
    for cc, geom in admin1:
        path = geometry_to_path(geom.simplify(4_000, preserve_topology=True), viewport)
        subdivision_paths.append(
            f'<path class="subdivision subdivision-{cc}" d="{path}" fill="none" '
            'stroke="rgba(255,255,255,.72)" stroke-width="1.15" stroke-linejoin="round"/>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>
  <g id="countries">
    {''.join(country_paths)}
  </g>
  <g id="subdivisions">
    {''.join(subdivision_paths)}
  </g>
</svg>
"""


def geometry_to_path(geom: BaseGeometry, viewport: dict[str, float]) -> str:
    parts: list[str] = []
    for poly in iter_polygons(geom):
        parts.append(ring_to_path(poly.exterior.coords, viewport))
        for interior in poly.interiors:
            parts.append(ring_to_path(interior.coords, viewport))
    return " ".join(parts)


def ring_to_path(coords: Any, viewport: dict[str, float]) -> str:
    commands: list[str] = []
    for i, (x, y, *_) in enumerate(coords):
        sx, sy = to_svg_point(float(x), float(y), viewport)
        command = "M" if i == 0 else "L"
        commands.append(f"{command}{sx:.1f},{sy:.1f}")
    commands.append("Z")
    return " ".join(commands)


def project_deployments(
    deployments: list[dict[str, Any]],
    transformer: Transformer,
    viewport: dict[str, float],
    projected_union: BaseGeometry,
    display_union: BaseGeometry,
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for d in deployments:
        px, py = transformer.transform(float(d["lon"]), float(d["lat"]))
        raw_point = Point(px, py)
        inside_basemap = projected_union.contains(raw_point)
        display_adjusted = not inside_basemap
        display_point = nearest_points(display_union, raw_point)[0] if display_adjusted else raw_point
        sx, sy = to_svg_point(display_point.x, display_point.y, viewport)
        raw_sx, raw_sy = to_svg_point(px, py, viewport)
        inside_viewport = 0 <= sx <= WIDTH and 0 <= sy <= HEIGHT
        projected.append(
            {
                **d,
                "x": round(sx, 3),
                "y": round(sy, 3),
                "rawX": round(raw_sx, 3),
                "rawY": round(raw_sy, 3),
                "leafletY": round(HEIGHT - sy, 3),
                "insideViewport": bool(inside_viewport),
                "insideBasemap": bool(inside_basemap),
                "displayAdjusted": bool(display_adjusted),
            }
        )
    return projected


def write_text(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_int(value: str | None, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Render GIS-correct LSN styled map prototype")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to clients_geocoded.csv")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path")
    parser.add_argument("--basemap-output", default=DEFAULT_BASEMAP_OUTPUT, help="Generated SVG basemap path")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Cache directory for Natural Earth zips")
    parser.add_argument("--title", default="LSN North America - Geographic", help="Title shown in the prototype")
    args = parser.parse_args()

    html_text = render_html(Path(args.input), Path(args.cache_dir), Path(args.basemap_output), args.title)
    write_text(html_text, Path(args.output))
    print(f"Rendered {args.output} from {args.input}")
    print(f"Generated basemap {args.basemap_output}")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
  <style>
    :root {
      --bg: #eef3f1;
      --ink: #17231f;
      --muted: #687873;
      --line: rgba(23, 35, 31, .14);
      --panel: rgba(255, 255, 255, .88);
      --green: #007f3d;
      --blue: #345168;
      --charcoal: #3f3f41;
      --amber: #f59e0b;
      --red: #ef4444;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body, #map { height: 100%; margin: 0; }
    body { background: var(--bg); color: var(--ink); overflow: hidden; }
    #map { position: fixed; inset: 0; background: #f8faf9; }
    .leaflet-container { background: #f8faf9; font-family: inherit; }
    .point-canvas { pointer-events: auto; }
    .leaflet-control-zoom { border: 0 !important; box-shadow: 0 14px 34px rgba(15, 23, 42, .14) !important; }
    .leaflet-control-zoom a {
      border: 1px solid rgba(23, 35, 31, .12) !important;
      background: rgba(255,255,255,.9) !important;
      color: var(--ink) !important;
      backdrop-filter: blur(12px);
    }
    .topbar {
      position: fixed;
      z-index: 600;
      left: 24px;
      top: 20px;
      right: 320px;
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 58px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 20px 60px rgba(15, 23, 42, .14);
      backdrop-filter: blur(18px) saturate(1.25);
    }
    .brand { min-width: 278px; padding: 0 8px 0 4px; }
    .brand h1 { margin: 0; font-size: 19px; line-height: 1.05; letter-spacing: 0; }
    .brand p { margin: 5px 0 0; color: var(--muted); font-size: 12px; line-height: 1.2; font-weight: 650; }
    .modebar, .toolbar { display: flex; gap: 6px; flex-wrap: wrap; }
    .toolbar { margin-left: auto; flex-wrap: nowrap; }
    .mode-btn, .tool-btn {
      appearance: none;
      height: 38px;
      border: 1px solid rgba(23,35,31,.13);
      border-radius: 8px;
      background: rgba(255,255,255,.78);
      color: #24362e;
      padding: 0 13px;
      font: inherit;
      font-size: 12px;
      font-weight: 760;
      cursor: pointer;
      white-space: nowrap;
    }
    .mode-btn.active { background: var(--green); color: #fff; border-color: var(--green); }
    .tool-btn { min-width: 42px; padding: 0 11px; }
    .panel {
      position: fixed;
      z-index: 590;
      right: 24px;
      top: 20px;
      width: 284px;
      max-height: calc(100vh - 40px);
      overflow: auto;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 20px 60px rgba(15, 23, 42, .14);
      backdrop-filter: blur(18px) saturate(1.25);
    }
    .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
    .metric {
      min-height: 78px;
      border: 1px solid rgba(23,35,31,.10);
      border-radius: 8px;
      background: rgba(255,255,255,.62);
      padding: 10px;
    }
    .metric-label { margin-bottom: 6px; color: var(--muted); font-size: 10px; font-weight: 820; text-transform: uppercase; letter-spacing: 0; }
    .metric-value { font-size: 22px; line-height: 1; font-weight: 820; letter-spacing: 0; }
    .metric-note { margin-top: 5px; color: var(--muted); font-size: 11px; font-weight: 620; }
    .legend-title { margin: 14px 0 8px; color: #24362e; font-size: 11px; font-weight: 820; text-transform: uppercase; letter-spacing: 0; }
    .legend-row { display: flex; justify-content: space-between; gap: 12px; margin: 8px 0 4px; font-size: 12px; }
    .legend-left { display: flex; align-items: center; gap: 7px; min-width: 0; }
    .legend-left span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .dot { width: 9px; height: 9px; border-radius: 999px; flex: 0 0 auto; }
    .bar { height: 4px; overflow: hidden; border-radius: 999px; background: rgba(23,35,31,.08); }
    .bar span { display: block; height: 100%; border-radius: 999px; }
    .popup { min-width: 240px; color: #fff; }
    .leaflet-popup-content-wrapper, .leaflet-popup-tip {
      background: rgba(23, 35, 31, .96);
      color: #fff;
      border-radius: 8px;
      box-shadow: 0 18px 40px rgba(15, 23, 42, .22);
    }
    .leaflet-popup-content { margin: 14px; }
    .popup h2 { margin: 0; font-size: 15px; line-height: 1.2; letter-spacing: 0; }
    .popup-sub { margin-top: 5px; color: rgba(255,255,255,.68); font-size: 12px; }
    .popup-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 12px;
      margin-top: 12px;
      padding-top: 11px;
      border-top: 1px solid rgba(255,255,255,.12);
    }
    .popup-label { color: rgba(255,255,255,.55); font-size: 10px; font-weight: 760; text-transform: uppercase; letter-spacing: 0; }
    .popup-value { margin-top: 2px; color: #fff; font-size: 12px; font-weight: 680; }
    @media (max-width: 980px) {
      .topbar { right: 20px; left: 20px; top: 16px; align-items: flex-start; flex-wrap: wrap; }
      .toolbar { margin-left: 0; }
      .panel { right: 20px; left: 20px; top: auto; bottom: 16px; width: auto; max-height: 34vh; }
      .brand { min-width: 100%; }
    }
    @media (max-width: 620px) {
      .modebar { display: grid; grid-template-columns: 1fr 1fr; width: 100%; }
      .mode-btn { width: 100%; }
      .panel { display: none; }
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <header class="topbar">
    <div class="brand">
      <h1>__TITLE__</h1>
      <p><span id="headerCount">0</span> deployments · __PROJECTION__</p>
    </div>
    <nav class="modebar" aria-label="Visualization modes">
      <button class="mode-btn active" data-mode="points">Exact Points</button>
      <button class="mode-btn" data-mode="clusters">Clusters</button>
      <button class="mode-btn" data-mode="heat">Heatmap</button>
      <button class="mode-btn" data-mode="hybrid">Heat + Points</button>
    </nav>
    <div class="toolbar">
      <button class="tool-btn" id="fitBtn" title="Fit map" aria-label="Fit map">Fit</button>
      <button class="tool-btn" id="fullscreenBtn" title="Fullscreen" aria-label="Fullscreen">Full</button>
    </div>
  </header>
  <aside class="panel" aria-label="Map summary">
    <div class="metrics">
      <div class="metric"><div class="metric-label">Deployments</div><div class="metric-value" id="totalDeployments">0</div><div class="metric-note">mapped rows</div></div>
      <div class="metric"><div class="metric-label">Raw On Land</div><div class="metric-value" id="insideBasemap">0</div><div class="metric-note" id="insideBasemapNote">before snap</div></div>
      <div class="metric"><div class="metric-label">Countries</div><div class="metric-value" id="countryTotal">0</div><div class="metric-note">US / CA / MX</div></div>
      <div class="metric"><div class="metric-label">Mode</div><div class="metric-value" id="modeLabel">Points</div><div class="metric-note">active view</div></div>
    </div>
    <div class="legend-title">Country</div>
    <div id="countryLegend"></div>
    <div class="legend-title">Status</div>
    <div id="statusLegend"></div>
  </aside>
  <script>
    const generatedAt = "__GENERATED_AT__";
    const sourceCsv = "__SOURCE_CSV__";
    const basemapSvg = "__BASEMAP_SVG__";
    const projectionName = "__PROJECTION__";
    const deployments = __DEPLOYMENTS_JSON__;
    const mapImage = "__MAP_IMAGE__";
    const imageSize = { width: __IMAGE_WIDTH__, height: __IMAGE_HEIGHT__ };
    const format = new Intl.NumberFormat("en-US");
    const statusColors = {
      "Deployed": "#10b981",
      "Service Due": "#f59e0b",
      "Planned": "#6366f1",
      "Decommissioned": "#ef4444",
      "Under Maintenance": "#f59e0b",
      "Inactive": "#ef4444"
    };
    const countryColors = { US: "#007f3d", CA: "#345168", MX: "#3f3f41" };
    const modeLabels = { points: "Points", clusters: "Clusters", heat: "Heat", hybrid: "Hybrid" };
    function escapeHtml(value) {
      return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    }
    function popupHtml(d) {
      const rows = [
        ["Deployment", d.id],
        ["Country", d.cc],
        ["Postal", d.zip],
        ["Status", d.status],
        ["Model", d.model],
        ["Region", d.region],
        ["Manager", d.manager],
        ["Install date", d.date]
      ];
      return `<div class="popup"><h2>${escapeHtml(d.name)}</h2><div class="popup-sub">${escapeHtml(d.id)} | ${escapeHtml(d.region)}</div><div class="popup-grid">${rows.map(([k,v]) => `<div><div class="popup-label">${escapeHtml(k)}</div><div class="popup-value">${escapeHtml(v)}</div></div>`).join("")}</div></div>`;
    }
    const map = L.map("map", {
      crs: L.CRS.Simple,
      minZoom: -1.7,
      maxZoom: 2.8,
      zoomSnap: 0.1,
      wheelPxPerZoomLevel: 80,
      zoomControl: false,
      attributionControl: false,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false
    });
    L.control.zoom({ position: "topright" }).addTo(map);
    const bounds = [[0, 0], [imageSize.height, imageSize.width]];
    L.imageOverlay(mapImage, bounds, { interactive: false }).addTo(map);
    function fitMap() {
      const wide = window.innerWidth > 980;
      const compact = window.innerWidth <= 620;
      map.fitBounds(bounds, {
        paddingTopLeft: [24, wide ? 104 : 140],
        paddingBottomRight: [wide ? 330 : 24, wide || compact ? 36 : 230]
      });
    }
    fitMap();
    let resizeFitTimer = null;
    map.on("resize", () => {
      window.clearTimeout(resizeFitTimer);
      resizeFitTimer = window.setTimeout(fitMap, 120);
    });
    const projected = deployments.map(d => ({ ...d, latlng: L.latLng(imageSize.height - d.y, d.x) }));
    const heatPoints = projected.map(d => [d.latlng.lat, d.x, Math.max(0.3, Math.min(1.2, Number(d.count || 1) / 3))]);
    function clusterPoints(points) {
      const clusters = new Map();
      for (const d of points) {
        const key = `${Math.round(d.x / 58)}|${Math.round(d.y / 58)}|${d.cc}`;
        const entry = clusters.get(key) || { x: 0, y: 0, count: 0, cc: d.cc, lat: 0, lng: 0 };
        entry.x += d.x;
        entry.y += d.y;
        entry.lat += d.latlng.lat;
        entry.lng += d.latlng.lng;
        entry.count += 1;
        clusters.set(key, entry);
      }
      return [...clusters.values()].map(entry => ({
        ...entry,
        x: entry.x / entry.count,
        y: entry.y / entry.count,
        latlng: L.latLng(entry.lat / entry.count, entry.lng / entry.count)
      }));
    }
    const clustered = clusterPoints(projected);
    const CanvasPointLayer = L.Layer.extend({
      initialize(points) {
        this.points = points;
        this.mode = "points";
      },
      onAdd(mapInstance) {
        this.map = mapInstance;
        this.canvas = L.DomUtil.create("canvas", "point-canvas leaflet-zoom-animated");
        this.ctx = this.canvas.getContext("2d");
        mapInstance.getPanes().overlayPane.appendChild(this.canvas);
        L.DomEvent.on(this.canvas, "click", this.onClick, this);
        mapInstance.on("resize viewreset zoomend moveend", this.reset, this);
        this.reset();
      },
      onRemove(mapInstance) {
        L.DomEvent.off(this.canvas, "click", this.onClick, this);
        mapInstance.off("resize viewreset zoomend moveend", this.reset, this);
        this.canvas.remove();
      },
      setMode(mode) {
        this.mode = mode;
        if (this.ctx) this.draw();
      },
      reset() {
        const size = this.map.getSize();
        const topLeft = this.map.containerPointToLayerPoint([0, 0]);
        this.topLeft = topLeft;
        L.DomUtil.setPosition(this.canvas, topLeft);
        const ratio = window.devicePixelRatio || 1;
        this.canvas.width = Math.round(size.x * ratio);
        this.canvas.height = Math.round(size.y * ratio);
        this.canvas.style.width = `${size.x}px`;
        this.canvas.style.height = `${size.y}px`;
        this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        this.viewport = size;
        this.draw();
      },
      pointToCanvas(d) {
        return this.map.latLngToLayerPoint(d.latlng).subtract(this.topLeft);
      },
      draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.viewport.x, this.viewport.y);
        if (this.mode === "clusters") this.drawClusters(ctx);
        else this.drawPoints(ctx);
      },
      drawPoints(ctx) {
        const zoom = this.map.getZoom();
        const radius = Math.max(2.1, Math.min(5.2, 3.1 + zoom * 0.55));
        ctx.save();
        ctx.lineWidth = 1.25;
        for (const d of this.points) {
          const p = this.pointToCanvas(d);
          if (p.x < -20 || p.y < -20 || p.x > this.viewport.x + 20 || p.y > this.viewport.y + 20) continue;
          ctx.beginPath();
          ctx.fillStyle = statusColors[d.status] || "#10b981";
          ctx.strokeStyle = "rgba(255,255,255,.92)";
          ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
        ctx.restore();
      },
      drawClusters(ctx) {
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        for (const entry of clustered) {
          const p = this.pointToCanvas(entry);
          if (p.x < -40 || p.y < -40 || p.x > this.viewport.x + 40 || p.y > this.viewport.y + 40) continue;
          const radius = Math.max(9, Math.min(24, 6 + Math.sqrt(entry.count) * 2.6));
          ctx.beginPath();
          ctx.fillStyle = countryColors[entry.cc] || "#10b981";
          ctx.globalAlpha = 0.88;
          ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.lineWidth = 2;
          ctx.strokeStyle = "rgba(255,255,255,.95)";
          ctx.stroke();
          if (entry.count > 1) {
            ctx.fillStyle = "#fff";
            ctx.font = `850 ${Math.max(10, Math.min(13, radius * 0.58))}px Inter, system-ui, sans-serif`;
            ctx.fillText(format.format(entry.count), p.x, p.y + 0.5);
          }
        }
        ctx.restore();
      },
      onClick(event) {
        const clickPoint = this.map.latLngToLayerPoint(event.latlng);
        let nearest = null;
        let nearestDist = Infinity;
        for (const d of this.points) {
          const point = this.map.latLngToLayerPoint(d.latlng);
          const dist = point.distanceTo(clickPoint);
          if (dist < nearestDist) {
            nearest = d;
            nearestDist = dist;
          }
        }
        if (nearest && nearestDist <= 18) {
          L.popup({ closeButton: true, offset: [0, -6] })
            .setLatLng(nearest.latlng)
            .setContent(popupHtml(nearest))
            .openOn(this.map);
        }
      }
    });
    const heatLayer = L.heatLayer(heatPoints, {
      radius: 24,
      blur: 18,
      maxZoom: 0.4,
      minOpacity: 0.2,
      gradient: { 0.18: "#6ee7b7", 0.42: "#22c55e", 0.68: "#f59e0b", 1.0: "#ef4444" }
    });
    const pointLayer = new CanvasPointLayer(projected);
    function setMode(mode) {
      for (const layer of [pointLayer, heatLayer]) map.removeLayer(layer);
      if (mode === "points") { pointLayer.setMode("points"); pointLayer.addTo(map); }
      if (mode === "clusters") { pointLayer.setMode("clusters"); pointLayer.addTo(map); }
      if (mode === "heat") heatLayer.addTo(map);
      if (mode === "hybrid") { heatLayer.addTo(map); pointLayer.setMode("points"); pointLayer.addTo(map); }
      document.querySelectorAll(".mode-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.mode === mode));
      document.getElementById("modeLabel").textContent = modeLabels[mode];
    }
    function countBy(key) {
      return deployments.reduce((acc, d) => {
        acc[d[key]] = (acc[d[key]] || 0) + 1;
        return acc;
      }, {});
    }
    function renderLegend(id, counts, colorFn) {
      const max = Math.max(...Object.values(counts));
      document.getElementById(id).innerHTML = Object.entries(counts).sort((a,b) => b[1] - a[1]).map(([label, value]) => {
        const width = Math.max(4, Math.round(value / max * 100));
        const color = colorFn(label);
        return `<div class="legend-row"><div class="legend-left"><span class="dot" style="background:${color}"></span><span>${escapeHtml(label)}</span></div><strong>${format.format(value)}</strong></div><div class="bar"><span style="width:${width}%;background:${color}"></span></div>`;
      }).join("");
    }
    document.getElementById("headerCount").textContent = format.format(projected.length);
    document.getElementById("totalDeployments").textContent = format.format(projected.length);
    document.getElementById("insideBasemap").textContent = format.format(projected.filter(d => d.insideBasemap).length);
    document.getElementById("insideBasemapNote").textContent = `${format.format(projected.filter(d => d.displayAdjusted).length)} display adjusted`;
    document.getElementById("countryTotal").textContent = format.format(Object.keys(countBy("cc")).length);
    renderLegend("countryLegend", countBy("cc"), label => countryColors[label] || "#64748b");
    renderLegend("statusLegend", countBy("status"), label => statusColors[label] || "#64748b");
    document.querySelectorAll(".mode-btn").forEach(btn => btn.addEventListener("click", () => setMode(btn.dataset.mode)));
    document.getElementById("fitBtn").addEventListener("click", fitMap);
    document.getElementById("fullscreenBtn").addEventListener("click", async () => {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
      else await document.exitFullscreen();
      setTimeout(() => map.invalidateSize(), 200);
    });
    setMode("points");
    window.__LSN_MAP_PROOF__ = {
      generatedAt,
      sourceCsv,
      basemapSvg,
      projectionName,
      renderer: "gis-projected-basemap-canvas-points",
      rows: deployments.length,
      plotted: projected.length,
      insideViewport: projected.filter(d => d.insideViewport).length,
      rawInsideBasemap: projected.filter(d => d.insideBasemap).length,
      displayAdjusted: projected.filter(d => d.displayAdjusted).length,
      markerIcons: document.querySelectorAll(".leaflet-marker-icon").length,
      pointCanvas: document.querySelectorAll("canvas.point-canvas").length,
      zoomAnimation: false
    };
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
