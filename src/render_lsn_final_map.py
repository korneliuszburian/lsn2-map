"""Render a final-map variant with GIS-correct geometry and light LSN styling."""

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
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, transform, unary_union


DEFAULT_INPUT = "data/output/clients_geocoded.csv"
DEFAULT_OUTPUT = "data/output/lsn-map-final.html"
DEFAULT_BASEMAP_OUTPUT = "data/output/lsn-north-america-final.svg"
DEFAULT_CACHE_DIR = "data/reference"
DEFAULT_PIN_IMAGE = "data/assets/client-map/pin-na-map.svg"

WIDTH = 1731
HEIGHT = 1800
PADDING_X = 105
PADDING_Y = 70
BACKGROUND_COLOR = "#ffffff"
LAND_FILL = "#d2d3d4"
COUNTRIES = ("US", "CA", "MX")
OUTLINE_COLOR = "rgba(255,255,255,.95)"
SUBDIVISION_COLOR = "rgba(255,255,255,.85)"
GRID_COLOR = "rgba(255,255,255,.12)"
GRID_SPACING_DEGREES = 10.0
GRID_STROKE_WIDTH = 0.8
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


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}" if path.suffix.lower() == ".svg" else f"data:image/png;base64,{encoded}"


def render_html(
    input_path: Path,
    cache_dir: Path,
    basemap_output: Path,
    pin_image: Path,
    title: str,
    grid_spacing: float,
    show_grid: bool,
) -> str:
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
    basemap_svg = render_basemap_svg(
        projected_admin0,
        projected_admin1,
        viewport,
        projected_union,
        transformer,
        grid_spacing=grid_spacing,
        show_grid=show_grid,
    )
    write_text(basemap_svg, basemap_output)

    projected_deployments = project_deployments(deployments, transformer, viewport, projected_union, display_union)
    basemap_data = "data:image/svg+xml;base64," + base64.b64encode(basemap_svg.encode("utf-8")).decode("ascii")
    pin_data = image_data_uri(pin_image)
    generated_at = datetime.now(timezone.utc).isoformat()

    replacements = {
        "__TITLE__": title,
        "__DEPLOYMENTS_JSON__": json.dumps(projected_deployments, ensure_ascii=True, separators=(",", ":")),
        "__MAP_IMAGE__": basemap_data,
        "__PIN_IMAGE__": pin_data,
        "__IMAGE_WIDTH__": str(WIDTH),
        "__IMAGE_HEIGHT__": str(HEIGHT),
        "__GENERATED_AT__": generated_at,
        "__SOURCE_CSV__": str(input_path),
        "__BASEMAP_SVG__": str(basemap_output),
        "__SOURCE_PIN__": str(pin_image),
        "__PIN_IS_SVG__": json.dumps(pin_image.suffix.lower() == ".svg"),
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
    name = str(
        row.get("admin")
        or row.get("ADMIN")
        or row.get("geonunit")
        or row.get("name")
        or ""
    )
    if name in ("United States of America", "United States"):
        return "US"
    if name == "Canada":
        return "CA"
    if name == "Mexico":
        return "MX"
    return ""


def filter_operational_geometry(geom: BaseGeometry) -> BaseGeometry:
    """Keep mainland North America and nearby extensions, but omit Hawaii."""
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
    projected_union: BaseGeometry,
    transformer: Transformer,
    grid_spacing: float = GRID_SPACING_DEGREES,
    show_grid: bool = False,
) -> str:
    country_paths: list[str] = []
    for _cc, geom in admin0:
        path = geometry_to_path(geom.simplify(5_000, preserve_topology=True), viewport)
        country_paths.append(
            f'<path class="country" d="{path}" fill="{LAND_FILL}" '
            f'stroke="{OUTLINE_COLOR}" stroke-width="1.3" stroke-linejoin="round"/>'
        )

    subdivision_paths: list[str] = []
    for _cc, geom in admin1:
        path = geometry_to_path(geom.simplify(4_000, preserve_topology=True), viewport)
        subdivision_paths.append(
            f'<path class="subdivision" d="{path}" fill="none" '
            f'stroke="{SUBDIVISION_COLOR}" stroke-width="1.1" stroke-linejoin="round"/>'
        )

    grid_paths: list[str] = []
    if show_grid:
        for path in build_grid_lines(
            projected_union=projected_union,
            transformer=transformer,
            spacing=grid_spacing,
            viewport=viewport,
        ):
            grid_paths.append(
                f'<path class="grid-line" d="{path}" fill="none" '
                f'stroke="{GRID_COLOR}" stroke-width="{GRID_STROKE_WIDTH}" stroke-dasharray="4 7"/>'
            )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BACKGROUND_COLOR}"/>
  <g id="countries">
    {''.join(country_paths)}
  </g>
  <g id="subdivisions">
    {''.join(subdivision_paths)}
  </g>
  <g id="grid">
    {''.join(grid_paths)}
  </g>
</svg>
"""


def build_grid_lines(
    projected_union: BaseGeometry,
    transformer: Transformer,
    spacing: float,
    viewport: dict[str, float],
) -> list[str]:
    lines: list[str] = []
    if spacing <= 0:
        return lines

    margin = max((viewport["maxx"] - viewport["minx"]) * 0.03, 10_000)
    union_bounds = projected_union.bounds
    clip_bounds = box(
        union_bounds[0] - margin,
        union_bounds[1] - margin,
        union_bounds[2] + margin,
        union_bounds[3] + margin,
    )

    lon_min, lon_max = -170.0, -50.0
    lat_min, lat_max = 14.0, 84.0

    for lon in _frange(lon_min, lon_max + 0.0001, 1.0):
        if not _is_grid_line(lon, lon_min, spacing):
            continue
        points = [transformer.transform(lon, lat) for lat in _frange(lat_min, lat_max + 0.0001, 0.5)]
        if len(points) < 2:
            continue
        path = geometry_to_path(LineString(points).intersection(clip_bounds), viewport)
        if path:
            lines.append(path)

    for lat in _frange(lat_min, lat_max + 0.0001, 1.0):
        if not _is_grid_line(lat, lat_min, spacing):
            continue
        points = [transformer.transform(lon, lat) for lon in _frange(lon_min, lon_max + 0.0001, 0.5)]
        if len(points) < 2:
            continue
        path = geometry_to_path(LineString(points).intersection(clip_bounds), viewport)
        if path:
            lines.append(path)

    return lines


def _frange(start: float, stop: float, step: float) -> list[float]:
    out: list[float] = []
    value = start
    while value <= stop + 1e-12:
        out.append(round(value, 12))
        value += step
    return out


def _is_grid_line(value: float, origin: float, spacing: float) -> bool:
    return abs((value - origin) / spacing - round((value - origin) / spacing)) < 1e-6


def geometry_to_path(geom: BaseGeometry, viewport: dict[str, float]) -> str:
    if geom.is_empty:
        return ""
    if isinstance(geom, LineString):
        return line_to_path(geom.coords, viewport)
    if isinstance(geom, MultiLineString):
        return " ".join(
            line_to_path(line.coords, viewport)
            for line in geom.geoms
            if not line.is_empty
        )
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
        commands.append(("M" if i == 0 else "L") + f"{sx:.1f},{sy:.1f}")
    commands.append("Z")
    return " ".join(commands)


def line_to_path(coords: Any, viewport: dict[str, float]) -> str:
    commands: list[str] = []
    for i, (x, y, *_) in enumerate(coords):
        sx, sy = to_svg_point(float(x), float(y), viewport)
        commands.append(("M" if i == 0 else "L") + f"{sx:.1f},{sy:.1f}")
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
    parser = argparse.ArgumentParser(description="Render GIS-correct final LSN map")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to clients_geocoded.csv")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path")
    parser.add_argument("--basemap-output", default=DEFAULT_BASEMAP_OUTPUT, help="Generated SVG basemap path")
    parser.add_argument("--pin-image", default=DEFAULT_PIN_IMAGE, help="Pin marker image used in Pins mode")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Cache directory for Natural Earth zips")
    parser.add_argument("--grid-spacing", type=float, default=GRID_SPACING_DEGREES, help="Graticule spacing in degrees")
    parser.add_argument("--no-grid", action="store_false", dest="show_grid", help="Disable graticule lines")
    parser.set_defaults(show_grid=False)
    parser.add_argument("--title", default="LSN North America - Final GIS Map", help="Title shown in the prototype")
    args = parser.parse_args()

    html_text = render_html(
        Path(args.input),
        Path(args.cache_dir),
        Path(args.basemap_output),
        Path(args.pin_image),
        args.title,
        grid_spacing=args.grid_spacing,
        show_grid=args.show_grid,
    )
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
  <style>
    :root {
      --bg: #ffffff;
      --ink: #1e2c2a;
      --muted: #5f6d66;
      --line: rgba(30, 44, 42, .14);
      --panel: rgba(255, 255, 255, .92);
      --point-fill: #00875a;
      --point-stroke: #005f48;
      --hot-fill: rgba(47, 159, 98, 0.28);
      --hot-stroke: rgba(0, 128, 73, 0.62);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body, #map { height: 100%; margin: 0; }
    body { background: var(--bg); color: var(--ink); overflow: hidden; }
    #map { position: fixed; inset: 0; background: #ffffff; }
    .leaflet-container { background: #ffffff; font-family: inherit; }
    .leaflet-image-layer { image-rendering: auto; }
    .hud {
      position: fixed;
      z-index: 800;
      left: 16px;
      top: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 9px;
      background: var(--panel);
      box-shadow: 0 20px 48px rgba(15, 23, 42, .12);
      backdrop-filter: blur(16px) saturate(1.2);
    }
    .title {
      padding: 0 6px 0 2px;
      min-width: 210px;
    }
    .title h1 {
      margin: 0;
      font-size: 15px;
      line-height: 1.2;
      letter-spacing: 0;
      font-weight: 700;
    }
    .title p {
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
    }
    .modebar, .toolbar { display: flex; gap: 6px; flex-wrap: wrap; }
    .mode-btn, .tool-btn {
      appearance: none;
      height: 33px;
      border: 1px solid rgba(30, 44, 42, .14);
      border-radius: 8px;
      background: rgba(255,255,255,.95);
      color: #24342e;
      padding: 0 11px;
      font: inherit;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }
    .mode-btn.active {
      background: #00875a;
      color: #fff;
      border-color: #00875a;
    }
    .toolbar { margin-left: auto; }
    .leaflet-control-zoom {
      border: 1px solid rgba(30, 44, 42, .14) !important;
      box-shadow: 0 14px 34px rgba(15, 23, 42, .16) !important;
    }
    .leaflet-map-error { pointer-events: none; }
    .leaflet-control-zoom a {

      border: 0 !important;
      background: rgba(255,255,255,.96) !important;
      color: #1e2c2a !important;
    }
    @media (max-width: 920px) {
      .hud { right: 16px; flex-wrap: wrap; }
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="hud" aria-label="map controls">
    <div class="title">
      <h1>__TITLE__</h1>
      <p><span id="headerCount">0</span> deployments · __PROJECTION__</p>
    </div>
    <nav class="modebar" aria-label="Visualization modes">
      <button class="mode-btn active" data-mode="hot-zones">Hot-zones</button>
      <button class="mode-btn" data-mode="points">Points</button>
      <button class="mode-btn" data-mode="pins">Pins</button>
      <button class="mode-btn" data-mode="flags">Flags</button>
    </nav>
    <div class="toolbar">
      <button class="tool-btn" id="fitBtn" title="Fit map view">Fit</button>
      <button class="tool-btn" id="fullscreenBtn" title="Fullscreen">Fullscreen</button>
    </div>
  </div>
  <script>
    const generatedAt = "__GENERATED_AT__";
    const sourceCsv = "__SOURCE_CSV__";
    const sourcePin = "__SOURCE_PIN__";
    const basemapSvg = "__BASEMAP_SVG__";
    const deployments = __DEPLOYMENTS_JSON__;
    const mapImage = "__MAP_IMAGE__";
    const pinImage = "__PIN_IMAGE__";
    const pinIsSvg = __PIN_IS_SVG__;
    const imageSize = { width: __IMAGE_WIDTH__, height: __IMAGE_HEIGHT__ };
    const projectionName = "__PROJECTION__";

    const format = new Intl.NumberFormat("en-US");
    const hotZoneConfig = {
      distance: 80,
      minRadius: 22,
      maxRadius: 120,
      baseRadius: 16,
      factor: 8.4,
      fill: "rgba(47, 159, 98, 0.28)",
      stroke: "rgba(0, 128, 73, 0.62)",
      lineWidth: 1.3
    };

    function escapeHtml(value) {
      return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
    }

    function popupHtml(d) {
      const rows = [
        ["Deployment", d.id],
        ["Country", d.cc],
        ["Postal", d.zip],
        ["Status", d.status],
        ["Model", d.model],
        ["Manager", d.manager],
        ["Install date", d.date]
      ];
      return `<strong>${escapeHtml(d.name || "Deployment")}</strong><div style="margin-top:6px;color:rgba(255,255,255,.78);font-size:12px">${escapeHtml(d.id) || "&nbsp;"}</div>` +
        rows.map(([k, v]) => `<div style="margin-top:8px"><div style=\"font-size:11px;color:rgba(255,255,255,.55);font-weight:700;text-transform:uppercase;letter-spacing:.6px\">${escapeHtml(k)}</div><div>${escapeHtml(v)}</div></div>`).join("");
    }

    function initFinalMap() {
    const map = L.map("map", {
      crs: L.CRS.Simple,
      minZoom: -1.7,
      maxZoom: 3.3,
      wheelPxPerZoomLevel: 75,
      zoomControl: true,
      attributionControl: false,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false
    });

    const bounds = [[0, 0], [imageSize.height, imageSize.width]];
    L.imageOverlay(mapImage, bounds, { interactive: false }).addTo(map);

    const projected = deployments.map(d => ({
      ...d,
      latlng: L.latLng(imageSize.height - d.y, d.x)
    }));

    const hotZones = buildHotZones(projected, hotZoneConfig.distance);

    fitMap();

    function fitMap() {
      const leftPadding = 16;
      const rightPadding = 16;
      const bottomPadding = 16;
      const topPadding = 16;
      const isDesktop = window.innerWidth >= 920;
      map.fitBounds(bounds, {
        paddingTopLeft: [leftPadding, topPadding],
        paddingBottomRight: [isDesktop ? (window.innerWidth > 1200 ? 390 : 220) : rightPadding, bottomPadding],
        animate: false
      });
    }

    class MapPointLayer extends L.Layer {
      constructor(points) {
        super();
        this.points = points;
        this.mode = "hot-zones";
        this.pinImage = new Image();
        this.pinImageLoaded = false;
        this.pinImage.onload = () => {
          this.pinImageLoaded = true;
          this.draw();
        };
        this.pinImage.src = pinImage;
      }
      onAdd(mapInstance) {
        this.map = mapInstance;
        this.canvas = L.DomUtil.create("canvas", "point-canvas leaflet-zoom-animated");
        this.ctx = this.canvas.getContext("2d");
        mapInstance.getPanes().overlayPane.appendChild(this.canvas);
        L.DomEvent.on(this.canvas, "click", this.onClick, this);
        mapInstance.on("resize viewreset zoomend moveend", this.reset, this);
        this.reset();
      }
      onRemove(mapInstance) {
        L.DomEvent.off(this.canvas, "click", this.onClick, this);
        mapInstance.off("resize viewreset zoomend moveend", this.reset, this);
        this.canvas.remove();
      }
      setMode(mode) {
        this.mode = mode;
        this.draw();
      }
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
      }
      pointToCanvas(d) {
        return this.map.latLngToLayerPoint(d.latlng).subtract(this.topLeft);
      }
      draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.viewport.x, this.viewport.y);
        if (this.mode === "hot-zones") {
          this.drawHotZones(ctx);
          this.drawPoints(ctx);
          return;
        }
        if (this.mode === "points") this.drawPoints(ctx);
        if (this.mode === "pins") this.drawPins(ctx);
        if (this.mode === "flags") this.drawFlags(ctx);
      }
      drawHotZones(ctx) {
        const zoom = this.map.getZoom();
        const baseStroke = Math.max(1, Math.min(2.4, 1.4 + zoom * 0.2));
        ctx.save();
        ctx.setLineDash([4, 4]);
        ctx.globalAlpha = 0.9;
        for (const zone of hotZones) {
          const p = this.pointToCanvas(zone);
          if (p.x < -zone.radius - 20 || p.y < -zone.radius - 20 || p.x > this.viewport.x + zone.radius + 20 || p.y > this.viewport.y + zone.radius + 20) {
            continue;
          }
          ctx.beginPath();
          ctx.fillStyle = hotZoneConfig.fill;
          ctx.strokeStyle = hotZoneConfig.stroke;
          ctx.lineWidth = baseStroke;
          ctx.arc(p.x, p.y, zone.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
        ctx.restore();
      }
      drawPoints(ctx) {
        const zoom = this.map.getZoom();
        const radius = Math.max(2.2, Math.min(3.2, 2.4 + zoom * 0.2));
        ctx.save();
        for (const d of this.points) {
          const p = this.pointToCanvas(d);
          if (p.x < -20 || p.y < -20 || p.x > this.viewport.x + 20 || p.y > this.viewport.y + 20) continue;
          ctx.beginPath();
          ctx.fillStyle = "rgba(0,135,90,0.9)";
          ctx.strokeStyle = "rgba(0,95,72,0.98)";
          ctx.lineWidth = 1;
          ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
        ctx.restore();
      }
      drawPins(ctx) {
        const zoom = this.map.getZoom();
        const maxSize = Math.max(10, Math.min(15, 11 + zoom * 1.1));
        const ratio = this.pinImageLoaded ? 1 : 0;
        for (const d of this.points) {
          const p = this.pointToCanvas(d);
          if (p.x < -35 || p.y < -35 || p.x > this.viewport.x + 35 || p.y > this.viewport.y + 35) continue;
          const w = maxSize;
          const h = maxSize * (pinIsSvg ? 1.45 : 1.45);
          if (ratio) {
            ctx.drawImage(this.pinImage, p.x - w * 0.5, p.y - h, w, h);
            continue;
          }
          ctx.save();
          ctx.beginPath();
          ctx.fillStyle = "#00a06b";
          ctx.strokeStyle = "rgba(255,255,255,0.95)";
          ctx.lineWidth = 1;
          ctx.arc(p.x, p.y - (h * 0.15), Math.max(1.6, maxSize * 0.16), 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        }
      }
      drawFlags(ctx) {
        const zoom = this.map.getZoom();
        const h = Math.max(8, Math.min(13, 9.6 + zoom * 0.5));
        const w = h * 0.98;
        for (const d of this.points) {
          const p = this.pointToCanvas(d);
          if (p.x < -22 || p.y < -28 || p.x > this.viewport.x + 22 || p.y > this.viewport.y + 22) continue;
          const top = p.y - h - 4;
          const centerX = p.x - w * 0.18;
          const flagColor = "#00a06b";
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x, top + h * 0.8);
          ctx.strokeStyle = "#dce5dc";
          ctx.lineWidth = 1.4;
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(centerX, top);
          ctx.lineTo(centerX + w, top + h * 0.18);
          ctx.lineTo(centerX + w, top + h * 0.72);
          ctx.lineTo(centerX, top + h);
          ctx.closePath();
          ctx.fillStyle = flagColor;
          ctx.fill();
          ctx.strokeStyle = "rgba(255,255,255,0.85)";
          ctx.lineWidth = 0.9;
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(p.x, p.y + 2.5, 2.0, 0, Math.PI * 2);
          ctx.fillStyle = "#fff";
          ctx.fill();
          ctx.strokeStyle = "rgba(0,95,72,0.45)";
          ctx.stroke();
        }
      }
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
        const threshold = 18;
        if (nearest && nearestDist <= threshold) {
          const popup = L.popup({ closeButton: false, offset: [0, -8] })
            .setLatLng(nearest.latlng)
            .setContent(popupHtml(nearest))
            .openOn(this.map);
        }
      }
    }

    function buildHotZones(points, distancePx) {
      const cellSize = distancePx;
      const cells = new Map();
      const parent = [...Array(points.length).keys()];
      const rank = new Array(points.length).fill(1);
      const clusters = [];

      const getCell = (point) => [Math.floor(point.x / cellSize), Math.floor(point.y / cellSize)];
      const key = (cx, cy) => `${cx}|${cy}`;

      points.forEach((point, idx) => {
        const [cx, cy] = getCell(point);
        const cellKey = key(cx, cy);
        const ids = cells.get(cellKey) || [];
        ids.push(idx);
        cells.set(cellKey, ids);

        for (let ox = -1; ox <= 1; ox++) {
          for (let oy = -1; oy <= 1; oy++) {
            const nearby = cells.get(key(cx + ox, cy + oy)) || [];
            for (const otherIdx of nearby) {
              if (otherIdx >= idx) continue;
              const dx = points[otherIdx].x - point.x;
              const dy = points[otherIdx].y - point.y;
              if (dx * dx + dy * dy <= distancePx * distancePx) {
                union(parent, rank, idx, otherIdx);
              }
            }
          }
        }
      });

      for (let i = 0; i < points.length; i++) {
        const root = find(parent, i);
        clusters[root] = clusters[root] || { count: 0, x: 0, y: 0 };
        clusters[root].count += 1;
        clusters[root].x += points[i].x;
        clusters[root].y += points[i].y;
      }

      return Object.values(clusters)
        .filter(Boolean)
        .map((entry) => {
          const cx = entry.x / entry.count;
          const cy = entry.y / entry.count;
          const radius = Math.min(
            hotZoneConfig.maxRadius,
            Math.max(
              hotZoneConfig.minRadius,
              hotZoneConfig.baseRadius + Math.sqrt(entry.count) * hotZoneConfig.factor
            )
          );
          return {
            x: cx,
            y: cy,
            radius,
            count: entry.count
          };
        })
        .sort((a, b) => b.radius - a.radius);
    }

    function find(parent, x) {
      if (parent[x] === x) return x;
      parent[x] = find(parent, parent[x]);
      return parent[x];
    }
    function union(parent, rank, a, b) {
      const rootA = find(parent, a);
      const rootB = find(parent, b);
      if (rootA === rootB) return;
      if (rank[rootA] < rank[rootB]) {
        parent[rootA] = rootB;
      } else if (rank[rootA] > rank[rootB]) {
        parent[rootB] = rootA;
      } else {
        parent[rootB] = rootA;
        rank[rootA] += 1;
      }
    }

    const pointLayer = new MapPointLayer(projected);
    pointLayer.addTo(map);

    let activeMode = "hot-zones";
    const pointsInside = projected.filter(d => d.insideViewport).length;
    document.getElementById("headerCount").textContent = format.format(projected.length);

    function setMode(mode) {
      activeMode = mode;
      pointLayer.setMode(mode);
      document.querySelectorAll(".mode-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.mode === mode);
      });
    }

    document.querySelectorAll(".mode-btn").forEach(btn =>
      btn.addEventListener("click", () => setMode(btn.dataset.mode))
    );

    document.getElementById("fitBtn").addEventListener("click", fitMap);
    document.getElementById("fullscreenBtn").addEventListener("click", async () => {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
      else await document.exitFullscreen();
      setTimeout(() => map.invalidateSize(), 180);
      setTimeout(() => fitMap(), 220);
    });

    map.on("resize", () => {
      setTimeout(() => fitMap(), 60);
    });

    setMode("hot-zones");
    window.__LSN_MAP_FINAL_PROOF__ = {
      generatedAt,
      sourceCsv,
      sourcePin,
      basemapSvg,
      projectionName,
      renderer: "gis-final-light-canvas",
      rows: deployments.length,
      plotted: projected.length,
      mode: activeMode,
      insideViewport: pointsInside,
      rawInsideBasemap: projected.filter(d => d.insideBasemap).length,
      displayAdjusted: projected.filter(d => d.displayAdjusted).length,
      pointLayer: "canvas"
    };

  }

  if (typeof L === "undefined" || typeof L.map !== "function") {
    const status = document.createElement("div");
    status.className = "leaflet-map-error";
    status.innerHTML = `<div>Leaflet library failed to load.<br/>Please check network access to CDN and reload.</div>`;
    status.style.cssText = "position:fixed;inset:16px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.9);border:1px solid rgba(30,44,42,.2);border-radius:10px;padding:12px;z-index:1000;max-width:420px;font:600 13px/1.35 Inter, sans-serif;color:#1e2c2a;text-align:center;";
    status.style.boxShadow = "0 14px 34px rgba(15,23,42,.12)";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    document.body.appendChild(status);
  } else {
    try {
      initFinalMap();
    } catch (error) {
      const errorStatus = document.createElement("div");
      errorStatus.className = "leaflet-map-error";
      errorStatus.innerHTML = `<div>Map init error: ${error.message}</div>`;
      errorStatus.style.cssText = "position:fixed;inset:16px;display:flex;align-items:center;justify-content:center;background:rgba(255,245,245,.95);border:1px solid #fca5a5;border-radius:10px;padding:12px;z-index:1000;max-width:420px;font:600 13px/1.35 Inter, sans-serif;color:#7f1d1d;text-align:center;";
      errorStatus.style.boxShadow = "0 14px 34px rgba(15,23,42,.12)";
      errorStatus.setAttribute("role", "status");
      errorStatus.setAttribute("aria-live", "assertive");
      document.body.appendChild(errorStatus);
      throw error;
    }
  }


  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
