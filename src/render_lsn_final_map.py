"""Render a final-map variant with GIS-correct geometry and light LSN2 styling."""

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
DEFAULT_SHORT_BASEMAP_OUTPUT = "data/output/lsn-north-america-final-short.svg"
DEFAULT_HAWAII_BASEMAP_OUTPUT = "data/output/lsn-north-america-final-hawaii.svg"
DEFAULT_CACHE_DIR = "data/reference"
DEFAULT_PIN_IMAGE = "data/assets/client-map/pin-na-map.svg"

WIDTH = 1731
HEIGHT = 1800
HAWAII_WIDTH = 380
HAWAII_HEIGHT = 300
PADDING_X = 105
PADDING_Y = 130
HAWAII_PADDING_X = 16
HAWAII_PADDING_Y = 16
HAWAII_DISPLAY_X = 330
HAWAII_DISPLAY_Y = 1415
HAWAII_DISPLAY_SCALE = 0.50
BACKGROUND_COLOR = "#ffffff"
LAND_FILL = "#d2d3d4"
DATA_COUNTRIES = ("US", "CA", "MX")
BASEMAP_COUNTRIES = ("US", "CA", "MX", "CU", "PR", "HT", "DO", "JM", "BS")
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
    "admin1": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip",
    "lakes": "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_lakes.zip",
}
MIN_VISIBLE_LAKE_AREA_M2 = 2_000_000_000

MAIN_VIEWPORT_EXTENT_LON_LAT = (-170.0, 9.0, -50.0, 84.0)
SHORT_MAP_COMPONENT_MAX_LAT = 66.5
SHORT_MAP_POINT_EXTENT_LON_LAT = (-170.0, 9.0, -50.0, SHORT_MAP_COMPONENT_MAX_LAT)
SHORT_MAP_MAX_SNAP_DISTANCE_M = 100_000
HAWAII_VIEWPORT_EXTENT_LON_LAT = (-163.0, 17.8, -154.0, 24.2)
HAWAII_EXCLUDE_EXTENT_LON_LAT = (-163.4, 17.2, -153.4, 24.8)

HAWAII_REGION = {
    "min_lon": -161.0,
    "max_lon": -154.0,
    "min_lat": 18.0,
    "max_lat": 23.8,
}
CARIBBEAN_REGION = {
    "min_lon": -90.0,
    "max_lon": -58.0,
    "min_lat": 14.8,
    "max_lat": 26.5,
}


def _is_in_region(value: float, min_value: float, max_value: float) -> bool:
    return min_value <= value <= max_value


def classify_map_region(lon: float, lat: float) -> str:
    if _is_in_region(lon, HAWAII_REGION["min_lon"], HAWAII_REGION["max_lon"]) and _is_in_region(
        lat, HAWAII_REGION["min_lat"], HAWAII_REGION["max_lat"]
    ):
        return "hawaii"
    if _is_in_region(lon, CARIBBEAN_REGION["min_lon"], CARIBBEAN_REGION["max_lon"]) and _is_in_region(
        lat, CARIBBEAN_REGION["min_lat"], CARIBBEAN_REGION["max_lat"]
    ):
        return "caribbean"
    return "mainland"


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
                    "map_region": classify_map_region(lon, lat),
                    "manager": row.get("account_manager", ""),
                    "date": row.get("install_date", ""),
                }
            )
    return deployments


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}" if path.suffix.lower() == ".svg" else f"data:image/png;base64,{encoded}"


def deployment_in_lon_lat_extent(deployment: dict[str, Any], extent: tuple[float, float, float, float]) -> bool:
    lon_min, lat_min, lon_max, lat_max = extent
    lon = _parse_float(str(deployment.get("lon")))
    lat = _parse_float(str(deployment.get("lat")))
    return lon is not None and lat is not None and lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def geometry_covers_point(geom: BaseGeometry, point: Point) -> bool:
    return geom.contains(point) or geom.touches(point)


def deployment_raw_point(deployment: dict[str, Any], transformer: Transformer) -> Point:
    px, py = transformer.transform(float(deployment["lon"]), float(deployment["lat"]))
    return Point(px, py)


def filter_deployments_for_short_basemap(
    deployments: list[dict[str, Any]],
    transformer: Transformer,
    full_union: BaseGeometry,
    short_union: BaseGeometry,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for deployment in deployments:
        point = deployment_raw_point(deployment, transformer)
        was_on_full_basemap = geometry_covers_point(full_union, point)
        remains_on_short_basemap = geometry_covers_point(short_union, point)
        too_far_to_snap = point.distance(short_union) > SHORT_MAP_MAX_SNAP_DISTANCE_M
        if not remains_on_short_basemap and too_far_to_snap:
            continue
        if was_on_full_basemap and not remains_on_short_basemap:
            continue
        filtered.append(deployment)
    return filtered


def render_html(
    input_path: Path,
    cache_dir: Path,
    basemap_output: Path,
    short_basemap_output: Path,
    hawaii_basemap_output: Path,
    pin_image: Path,
    title: str,
    grid_spacing: float,
    show_grid: bool,
) -> str:
    deployments = read_deployments(input_path)
    if not deployments:
        raise ValueError(f"No geocoded deployments found in {input_path}")

    transformer = Transformer.from_crs("EPSG:4326", PROJECTION, always_xy=True)
    admin0, admin1, lakes = load_boundaries(cache_dir)

    main_extent = projected_extent_box(transformer, *MAIN_VIEWPORT_EXTENT_LON_LAT)
    short_extent = main_extent
    hawaii_extent = projected_extent_box(transformer, *HAWAII_VIEWPORT_EXTENT_LON_LAT)
    hawaii_cutout = projected_extent_box(transformer, *HAWAII_EXCLUDE_EXTENT_LON_LAT)

    projected_admin0 = project_boundaries(admin0, transformer, main_extent, cutout=hawaii_cutout, simplify_m=2_500)
    projected_admin1 = project_boundaries(admin1, transformer, main_extent, cutout=hawaii_cutout, simplify_m=900)
    projected_lakes = filter_visible_lakes(
        project_boundaries(lakes, transformer, main_extent, cutout=hawaii_cutout, simplify_m=1_200)
    )
    short_projected_admin0 = project_boundaries(
        admin0,
        transformer,
        short_extent,
        cutout=hawaii_cutout,
        simplify_m=2_500,
        component_max_lat=SHORT_MAP_COMPONENT_MAX_LAT,
    )
    short_projected_admin1 = project_boundaries(
        admin1,
        transformer,
        short_extent,
        cutout=hawaii_cutout,
        simplify_m=900,
        component_max_lat=SHORT_MAP_COMPONENT_MAX_LAT,
    )
    short_projected_lakes = filter_visible_lakes(
        project_boundaries(
            lakes,
            transformer,
            short_extent,
            cutout=hawaii_cutout,
            simplify_m=1_200,
            component_max_lat=SHORT_MAP_COMPONENT_MAX_LAT,
        )
    )
    hawaii_admin0 = project_boundaries(admin0, transformer, hawaii_extent, simplify_m=1_200)
    hawaii_admin1 = project_boundaries(admin1, transformer, hawaii_extent, simplify_m=600)
    hawaii_lakes = filter_visible_lakes(project_boundaries(lakes, transformer, hawaii_extent, simplify_m=600))

    projected_union = unary_union([geom for _, geom in projected_admin0])
    short_projected_union = unary_union([geom for _, geom in short_projected_admin0])
    hawaii_projected_union = unary_union([geom for _, geom in hawaii_admin0]) if hawaii_admin0 else None
    projected_land_mask = land_without_lakes(projected_union, projected_lakes)
    short_projected_land_mask = land_without_lakes(short_projected_union, short_projected_lakes)
    hawaii_projected_land_mask = (
        land_without_lakes(hawaii_projected_union, hawaii_lakes) if hawaii_projected_union else None
    )
    display_union = projected_land_mask.buffer(-12_000)
    if display_union.is_empty:
        display_union = projected_land_mask
    short_display_union = short_projected_land_mask.buffer(-12_000)
    if short_display_union.is_empty:
        short_display_union = short_projected_land_mask
    hawaii_display_union: BaseGeometry
    if hawaii_projected_land_mask:
        hawaii_display_union = hawaii_projected_land_mask.buffer(-4_000)
        if hawaii_display_union.is_empty:
            hawaii_display_union = hawaii_projected_land_mask
    else:
        hawaii_display_union = None

    viewport = build_viewport([geom for _, geom in projected_admin0], WIDTH, HEIGHT)
    short_viewport = build_viewport([geom for _, geom in short_projected_admin0], WIDTH, HEIGHT)
    hawaii_viewport = (
        build_viewport([geom for _, geom in hawaii_admin0], HAWAII_WIDTH, HAWAII_HEIGHT, HAWAII_PADDING_X, HAWAII_PADDING_Y)
        if hawaii_admin0
        else None
    )

    basemap_svg = render_basemap_svg(
        projected_admin0,
        projected_admin1,
        projected_lakes,
        viewport,
        projected_union,
        transformer,
        grid_spacing=grid_spacing,
        show_grid=show_grid,
        width=WIDTH,
        height=HEIGHT,
    )
    short_basemap_svg = render_basemap_svg(
        short_projected_admin0,
        short_projected_admin1,
        short_projected_lakes,
        short_viewport,
        short_projected_union,
        transformer,
        grid_spacing=grid_spacing,
        show_grid=show_grid,
        width=WIDTH,
        height=HEIGHT,
    )

    hawaii_basemap_svg = ""
    if hawaii_admin0 and hawaii_viewport is not None:
        hawaii_basemap_svg = render_basemap_svg(
            hawaii_admin0,
            hawaii_admin1,
            hawaii_lakes,
            hawaii_viewport,
            hawaii_projected_union,
            transformer,
            grid_spacing=0,
            show_grid=False,
            width=HAWAII_WIDTH,
            height=HAWAII_HEIGHT,
        )
        basemap_svg = inject_hawaii_display_inset(basemap_svg, hawaii_basemap_svg)
        short_basemap_svg = inject_hawaii_display_inset(short_basemap_svg, hawaii_basemap_svg)
        write_text(hawaii_basemap_svg, hawaii_basemap_output)
    else:
        write_text(basemap_svg, hawaii_basemap_output)
    basemap_no_lakes_svg = render_basemap_svg(
        projected_admin0,
        projected_admin1,
        [],
        viewport,
        projected_union,
        transformer,
        grid_spacing=grid_spacing,
        show_grid=show_grid,
        width=WIDTH,
        height=HEIGHT,
    )
    short_basemap_no_lakes_svg = render_basemap_svg(
        short_projected_admin0,
        short_projected_admin1,
        [],
        short_viewport,
        short_projected_union,
        transformer,
        grid_spacing=grid_spacing,
        show_grid=show_grid,
        width=WIDTH,
        height=HEIGHT,
    )
    if hawaii_admin0 and hawaii_viewport is not None:
        hawaii_basemap_no_lakes_svg = render_basemap_svg(
            hawaii_admin0,
            hawaii_admin1,
            [],
            hawaii_viewport,
            hawaii_projected_union,
            transformer,
            grid_spacing=0,
            show_grid=False,
            width=HAWAII_WIDTH,
            height=HAWAII_HEIGHT,
        )
        basemap_no_lakes_svg = inject_hawaii_display_inset(basemap_no_lakes_svg, hawaii_basemap_no_lakes_svg)
        short_basemap_no_lakes_svg = inject_hawaii_display_inset(short_basemap_no_lakes_svg, hawaii_basemap_no_lakes_svg)
    write_text(basemap_svg, basemap_output)
    write_text(short_basemap_svg, short_basemap_output)

    main_deployments = [d for d in deployments if d.get("map_region") != "hawaii"]
    hawaii_deployments = [d for d in deployments if d.get("map_region") == "hawaii"]
    short_main_deployments = [
        d for d in main_deployments
        if deployment_in_lon_lat_extent(d, SHORT_MAP_POINT_EXTENT_LON_LAT)
    ]
    short_main_deployments = filter_deployments_for_short_basemap(
        short_main_deployments,
        transformer,
        projected_land_mask,
        short_projected_land_mask,
    )

    projected_deployments = project_deployments(
        main_deployments,
        transformer,
        viewport,
        projected_land_mask,
        display_union,
    )
    projected_short_deployments = project_deployments(
        short_main_deployments,
        transformer,
        short_viewport,
        short_projected_land_mask,
        short_display_union,
    )
    projected_hawaii_deployments = project_deployments(
        hawaii_deployments,
        transformer,
        hawaii_viewport or viewport,
        hawaii_projected_land_mask or projected_land_mask,
        hawaii_display_union or display_union,
        width=HAWAII_WIDTH,
        height=HAWAII_HEIGHT,
    ) if hawaii_viewport else []
    projected_hawaii_deployments = relocate_hawaii_deployments(projected_hawaii_deployments)
    basemap_data = "data:image/svg+xml;base64," + base64.b64encode(basemap_svg.encode("utf-8")).decode("ascii")
    short_basemap_data = "data:image/svg+xml;base64," + base64.b64encode(short_basemap_svg.encode("utf-8")).decode("ascii")
    basemap_no_lakes_data = (
        "data:image/svg+xml;base64," + base64.b64encode(basemap_no_lakes_svg.encode("utf-8")).decode("ascii")
    )
    short_basemap_no_lakes_data = (
        "data:image/svg+xml;base64," + base64.b64encode(short_basemap_no_lakes_svg.encode("utf-8")).decode("ascii")
    )
    hawaii_basemap_data = (
        "data:image/svg+xml;base64," + base64.b64encode(hawaii_basemap_svg.encode("utf-8")).decode("ascii")
        if hawaii_basemap_svg
        else basemap_data
    )
    pin_data = image_data_uri(pin_image)
    generated_at = datetime.now(timezone.utc).isoformat()

    replacements = {
        "__TITLE__": title,
        "__MAIN_DEPLOYMENTS_JSON__": json.dumps(projected_deployments, ensure_ascii=True, separators=(",", ":")),
        "__HAWAII_DEPLOYMENTS_JSON__": json.dumps(projected_hawaii_deployments, ensure_ascii=True, separators=(",", ":")),
        "__SHORT_MAIN_DEPLOYMENTS_JSON__": json.dumps(
            projected_short_deployments,
            ensure_ascii=True,
            separators=(",", ":"),
        ),
        "__SHORT_HAWAII_DEPLOYMENTS_JSON__": json.dumps(
            projected_hawaii_deployments,
            ensure_ascii=True,
            separators=(",", ":"),
        ),
        "__MAP_IMAGE__": basemap_data,
        "__SHORT_MAP_IMAGE__": short_basemap_data,
        "__MAP_NO_LAKES_IMAGE__": basemap_no_lakes_data,
        "__SHORT_MAP_NO_LAKES_IMAGE__": short_basemap_no_lakes_data,
        "__HAWAII_MAP_IMAGE__": hawaii_basemap_data,
        "__PIN_IMAGE__": pin_data,
        "__IMAGE_WIDTH__": str(WIDTH),
        "__IMAGE_HEIGHT__": str(HEIGHT),
        "__HAWAII_IMAGE_WIDTH__": str(HAWAII_WIDTH),
        "__HAWAII_IMAGE_HEIGHT__": str(HAWAII_HEIGHT),
        "__GENERATED_AT__": generated_at,
        "__SOURCE_CSV__": str(input_path),
        "__BASEMAP_SVG__": str(basemap_output),
        "__SHORT_BASEMAP_SVG__": str(short_basemap_output),
        "__HAWAII_BASEMAP_SVG__": str(hawaii_basemap_output),
        "__SOURCE_PIN__": str(pin_image),
        "__PIN_IS_SVG__": json.dumps(pin_image.suffix.lower() == ".svg"),
        "__PROJECTION__": PROJECTION_NAME,
    }
    html_text = HTML_TEMPLATE
    for marker, value in replacements.items():
        html_text = html_text.replace(marker, value)
    return html_text


def load_boundaries(
    cache_dir: Path,
) -> tuple[list[tuple[str, BaseGeometry]], list[tuple[str, BaseGeometry]], list[tuple[str, BaseGeometry]]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    admin0_zip = download(SOURCES["admin0"], cache_dir / "ne_50m_admin_0_countries.zip")
    admin1_zip = download(SOURCES["admin1"], cache_dir / "ne_10m_admin_1_states_provinces.zip")
    lakes_zip = download(SOURCES["lakes"], cache_dir / "ne_10m_lakes.zip")

    admin0_gdf = gpd.read_file(admin0_zip)
    admin1_gdf = gpd.read_file(admin1_zip)
    lakes_gdf = gpd.read_file(lakes_zip)

    admin0_rows: list[tuple[str, BaseGeometry]] = []
    for _, row in admin0_gdf.iterrows():
        cc = country_code(row)
        if cc not in BASEMAP_COUNTRIES:
            continue
        admin0_rows.append((cc, row.geometry))

    admin1_rows: list[tuple[str, BaseGeometry]] = []
    for _, row in admin1_gdf.iterrows():
        cc = country_code(row)
        if cc not in DATA_COUNTRIES:
            continue
        admin1_rows.append((cc, row.geometry))

    lake_rows: list[tuple[str, BaseGeometry]] = []
    for _, row in lakes_gdf.iterrows():
        if row.geometry.is_empty:
            continue
        lake_rows.append(("water", row.geometry))

    if not admin0_rows:
        raise ValueError("Natural Earth admin0 selection returned no geometries")
    return admin0_rows, admin1_rows, lake_rows


def download(url: str, dest: Path) -> Path:
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    print(f"Downloading {url}", flush=True)
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def projected_extent_box(
    transformer: Transformer,
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
) -> BaseGeometry:
    edge_points: list[tuple[float, float]] = []
    steps = 96
    for i in range(steps + 1):
        t = i / steps
        lon = lon_min + (lon_max - lon_min) * t
        lat = lat_min + (lat_max - lat_min) * t
        edge_points.append((lon, lat_min))
        edge_points.append((lon, lat_max))
        edge_points.append((lon_min, lat))
        edge_points.append((lon_max, lat))
    projected_points = [transformer.transform(lon, lat) for lon, lat in edge_points]
    xs = [p[0] for p in projected_points]
    ys = [p[1] for p in projected_points]
    return box(min(xs), min(ys), max(xs), max(ys))


def filter_components_north_of(geom: BaseGeometry, max_lat: float) -> BaseGeometry:
    if geom.is_empty:
        return geom
    if isinstance(geom, Polygon):
        return geom if geom.representative_point().y <= max_lat else GeometryCollection()
    if isinstance(geom, MultiPolygon):
        kept = [part for part in geom.geoms if part.representative_point().y <= max_lat]
        return MultiPolygon(kept) if kept else GeometryCollection()
    if isinstance(geom, GeometryCollection):
        kept = [filter_components_north_of(part, max_lat) for part in geom.geoms]
        kept = [part for part in kept if not part.is_empty]
        return unary_union(kept) if kept else GeometryCollection()
    return geom


def project_boundaries(
    rows: list[tuple[str, BaseGeometry]],
    transformer: Transformer,
    extent_box: BaseGeometry,
    cutout: BaseGeometry | None = None,
    simplify_m: float = 5_000,
    simplify_preserve: bool = True,
    component_max_lat: float | None = None,
) -> list[tuple[str, BaseGeometry]]:
    out: list[tuple[str, BaseGeometry]] = []
    for cc, geom in rows:
        if geom.is_empty:
            continue
        source_geom = filter_components_north_of(geom, component_max_lat) if component_max_lat is not None else geom
        if source_geom.is_empty:
            continue
        projected = project_geometry(source_geom, transformer)
        clipped = projected.intersection(extent_box)
        if cutout is not None:
            clipped = clipped.difference(cutout)
        if clipped.is_empty:
            continue
        simplified = clipped.simplify(simplify_m, preserve_topology=simplify_preserve)
        if simplified.is_empty:
            continue
        out.append((cc, simplified))
    return out


def filter_visible_lakes(rows: list[tuple[str, BaseGeometry]]) -> list[tuple[str, BaseGeometry]]:
    return [(kind, geom) for kind, geom in rows if not geom.is_empty and geom.area >= MIN_VISIBLE_LAKE_AREA_M2]


def land_without_lakes(land: BaseGeometry, lakes: list[tuple[str, BaseGeometry]]) -> BaseGeometry:
    lake_union = unary_union([geom for _, geom in lakes if not geom.is_empty])
    if lake_union.is_empty:
        return land
    dry_land = land.difference(lake_union)
    return dry_land if not dry_land.is_empty else land


def country_code(row: Any) -> str:
    for key in ("ISO_A2", "iso_a2", "adm0_a3", "ADM0_A3"):
        value = row.get(key)
        if value in ("US", "USA"):
            return "US"
        if value in ("CA", "CAN"):
            return "CA"
        if value in ("MX", "MEX"):
            return "MX"
        if value in ("CU", "CUB"):
            return "CU"
        if value in ("PR", "PRI"):
            return "PR"
        if value in ("HT", "HTI"):
            return "HT"
        if value in ("DO", "DOM"):
            return "DO"
        if value in ("JM", "JAM"):
            return "JM"
        if value in ("BS", "BHS"):
            return "BS"
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
    if name == "Cuba":
        return "CU"
    if name == "Puerto Rico":
        return "PR"
    if name == "Haiti":
        return "HT"
    if name == "Dominican Republic":
        return "DO"
    if name == "Jamaica":
        return "JM"
    if name == "Bahamas":
        return "BS"
    return ""


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


def build_viewport(
    geometries: list[BaseGeometry],
    width: int = WIDTH,
    height: int = HEIGHT,
    padding_x: int = PADDING_X,
    padding_y: int = PADDING_Y,
) -> dict[str, float]:
    minx, miny, maxx, maxy = unary_union(geometries).bounds
    if maxx == minx or maxy == miny:
        raise ValueError("Projected geometry has zero extent; cannot build viewport")
    scale = min((width - padding_x * 2) / (maxx - minx), (height - padding_y * 2) / (maxy - miny))
    rendered_width = (maxx - minx) * scale
    rendered_height = (maxy - miny) * scale
    offset_x = (width - rendered_width) / 2 - minx * scale
    offset_y = (height - rendered_height) / 2 + maxy * scale
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
    lakes: list[tuple[str, BaseGeometry]] | None,
    viewport: dict[str, float],
    projected_union: BaseGeometry,
    transformer: Transformer,
    grid_spacing: float = GRID_SPACING_DEGREES,
    show_grid: bool = False,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> str:
    country_paths: list[str] = []
    for _cc, geom in admin0:
        path = geometry_to_path(geom.simplify(1_800, preserve_topology=True), viewport)
        country_paths.append(
            f'<path class="country" d="{path}" fill="{LAND_FILL}" '
            f'fill-rule="evenodd" clip-rule="evenodd" stroke="{OUTLINE_COLOR}" '
            f'stroke-width="0.75" stroke-linejoin="round"/>'
        )

    lake_paths: list[str] = []
    for _kind, geom in lakes or []:
        path = geometry_to_path(geom.simplify(500, preserve_topology=True), viewport)
        if not path:
            continue
        lake_paths.append(
            f'<path class="water" d="{path}" fill="{BACKGROUND_COLOR}" '
            f'stroke="{BACKGROUND_COLOR}" stroke-width="0.35" stroke-linejoin="round"/>'
        )

    subdivision_paths: list[str] = []
    for _cc, geom in admin1:
        path = geometry_to_path(geom.simplify(600, preserve_topology=True), viewport)
        subdivision_paths.append(
            f'<path class="subdivision" d="{path}" fill="none" '
            f'stroke="{SUBDIVISION_COLOR}" stroke-width="0.55" stroke-linejoin="round"/>'
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

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}"/>
  <g id="countries">
    {''.join(country_paths)}
  </g>
  <g id="water">
    {''.join(lake_paths)}
  </g>
  <g id="subdivisions">
    {''.join(subdivision_paths)}
  </g>
  <g id="grid">
    {''.join(grid_paths)}
  </g>
</svg>
"""


def inject_hawaii_display_inset(main_svg: str, hawaii_svg: str) -> str:
    inner = svg_inner_without_background(hawaii_svg)
    if not inner:
        return main_svg
    inset = (
        f'<g id="hawaii-display-inset" transform="translate({HAWAII_DISPLAY_X} {HAWAII_DISPLAY_Y}) '
        f'scale({HAWAII_DISPLAY_SCALE})">\n{inner}\n  </g>'
    )
    return main_svg.replace("</svg>", f"  {inset}\n</svg>")


def svg_inner_without_background(svg_text: str) -> str:
    start = svg_text.find("<g id=\"countries\">")
    end = svg_text.rfind("</svg>")
    if start < 0 or end < 0 or end <= start:
        return ""
    return svg_text[start:end].strip()


def relocate_hawaii_deployments(deployments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relocated: list[dict[str, Any]] = []
    for point in deployments:
        x = _parse_float(str(point.get("x")))
        y = _parse_float(str(point.get("y")))
        raw_x = _parse_float(str(point.get("rawX")))
        raw_y = _parse_float(str(point.get("rawY")))
        if x is None or y is None:
            continue
        moved = {
            **point,
            "x": round(HAWAII_DISPLAY_X + x * HAWAII_DISPLAY_SCALE, 3),
            "y": round(HAWAII_DISPLAY_Y + y * HAWAII_DISPLAY_SCALE, 3),
            "displayRelocated": True,
        }
        if raw_x is not None and raw_y is not None:
            moved["rawX"] = round(HAWAII_DISPLAY_X + raw_x * HAWAII_DISPLAY_SCALE, 3)
            moved["rawY"] = round(HAWAII_DISPLAY_Y + raw_y * HAWAII_DISPLAY_SCALE, 3)
        relocated.append(moved)
    return relocated


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
    width: int = WIDTH,
    height: int = HEIGHT,
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
        inside_viewport = 0 <= sx <= width and 0 <= sy <= height
        projected.append(
            {
                **d,
                "x": round(sx, 3),
                "y": round(sy, 3),
                "rawX": round(raw_sx, 3),
                "rawY": round(raw_sy, 3),
                "screenY": round(sy, 3),
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
    parser = argparse.ArgumentParser(description="Render GIS-correct final LSN2 map")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to clients_geocoded.csv")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path")
    parser.add_argument("--basemap-output", default=DEFAULT_BASEMAP_OUTPUT, help="Generated SVG basemap path")
    parser.add_argument(
        "--short-basemap-output",
        default=DEFAULT_SHORT_BASEMAP_OUTPUT,
        help="Generated SVG basemap path for the clipped short-map variant",
    )
    parser.add_argument(
        "--hawaii-basemap-output",
        default=DEFAULT_HAWAII_BASEMAP_OUTPUT,
        help="Generated SVG inset basemap for Hawaii",
    )
    parser.add_argument("--pin-image", default=DEFAULT_PIN_IMAGE, help="Pin marker image used in Pins mode")
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Cache directory for Natural Earth zips")
    parser.add_argument("--grid-spacing", type=float, default=GRID_SPACING_DEGREES, help="Graticule spacing in degrees")
    parser.add_argument("--no-grid", action="store_false", dest="show_grid", help="Disable graticule lines")
    parser.set_defaults(show_grid=False)
    parser.add_argument("--title", default="Version 2.0 - LSN2 Map", help="Title shown in the prototype")
    args = parser.parse_args()

    html_text = render_html(
        Path(args.input),
        Path(args.cache_dir),
        Path(args.basemap_output),
        Path(args.short_basemap_output),
        Path(args.hawaii_basemap_output),
        Path(args.pin_image),
        args.title,
        grid_spacing=args.grid_spacing,
        show_grid=args.show_grid,
    )
    write_text(html_text, Path(args.output))
    print(f"Rendered {args.output} from {args.input}")
    print(f"Generated basemap {args.basemap_output}")
    print(f"Generated short basemap {args.short_basemap_output}")
    print(f"Generated Hawaiian inset basemap {args.hawaii_basemap_output}")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <style>
    :root {
      --bg: #ffffff;
      --ink: #18231f;
      --muted: #53655f;
      --line: rgba(22, 34, 30, .17);
      --panel: rgba(255, 255, 255, .94);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body, #stage { width: 100%; height: 100%; margin: 0; }
    body { background: var(--bg); color: var(--ink); overflow: hidden; }
    #stage { position: fixed; inset: 0; overflow: hidden; cursor: grab; touch-action: none; }
    #stage:active { cursor: grabbing; }
    #mapImage {
      position: absolute;
      left: 0;
      top: 0;
      width: __IMAGE_WIDTH__px;
      height: __IMAGE_HEIGHT__px;
      max-width: none;
      transform-origin: 0 0;
      user-select: none;
      pointer-events: none;
    }
    #hotCanvas, #pinCanvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }
    .hud {
      position: fixed;
      z-index: 20;
      left: 16px;
      top: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      box-shadow: 0 20px 42px rgba(9, 18, 14, .12);
      backdrop-filter: blur(14px);
    }
    .title { min-width: 170px; padding-left: 2px; }
    .title h1 { margin: 0; font-size: 15px; line-height: 1.2; font-weight: 700; }
    .modebar, .toolbar, .framebar { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
    .mode-btn, .tool-btn {
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      height: 33px;
      padding: 0 11px;
      font: inherit;
      font-size: 11px;
      font-weight: 700;
      color: #1f2f2b;
      background: rgba(255, 255, 255, .97);
      cursor: pointer;
      white-space: nowrap;
    }
    .mode-btn.active, .tool-btn.active, .tool-btn:active {
      background: #00875a;
      color: #fff;
      border-color: #00875a;
    }
    .toolbar { margin-left: auto; }
    .pin-popup {
      position: fixed;
      z-index: 30;
      min-width: 220px;
      max-width: 280px;
      border-radius: 10px;
      background: rgba(25, 32, 29, .96);
      color: #fff;
      box-shadow: 0 16px 36px rgba(20, 16, 8, .28);
      padding: 11px 13px;
      font-size: 12px;
      transform: translate(-50%, -112%);
      pointer-events: none;
      display: none;
    }
    .pin-popup h2 { margin: 0 0 7px; font-size: 14px; line-height: 1.2; }
    .pin-popup p { margin: 4px 0 0; color: rgba(255,255,255,.78); }
    @media (max-width: 760px) {
      .hud { right: 16px; left: 16px; flex-wrap: wrap; }
      .title { min-width: 180px; }
      .toolbar { margin-left: 0; }
    }
  </style>
</head>
<body>
  <main id="stage" aria-label="LSN2 North America map">
    <img id="mapImage" alt="" draggable="false" src="__MAP_IMAGE__">
    <canvas id="hotCanvas"></canvas>
    <canvas id="pinCanvas"></canvas>
  </main>
  <div class="hud" aria-label="map controls">
    <div class="title">
      <h1>__TITLE__</h1>
    </div>
    <nav class="modebar" aria-label="Layer toggles">
      <button class="mode-btn active" id="hotZonesToggle" type="button">Hot Zones</button>
      <button class="mode-btn active" id="pinsToggle" type="button">Pins</button>
      <button class="mode-btn" id="pointsToggle" type="button">Points</button>
    </nav>
    <div class="toolbar">
      <div class="framebar" aria-label="Map frame">
        <button class="tool-btn active" id="fullFrameBtn" type="button">Full map</button>
        <button class="tool-btn" id="shortFrameBtn" type="button">Short map</button>
      </div>
      <div class="framebar" aria-label="Water layer">
        <button class="tool-btn active" id="lakesBtn" type="button">Lakes</button>
        <button class="tool-btn" id="noLakesBtn" type="button">No lakes</button>
      </div>
      <button class="tool-btn" id="zoomInBtn" type="button">Zoom +</button>
      <button class="tool-btn" id="zoomOutBtn" type="button">Zoom -</button>
      <button class="tool-btn" id="fitBtn" type="button">Fit</button>
      <button class="tool-btn" id="fullscreenBtn" type="button">Fullscreen</button>
    </div>
  </div>
  <div id="popup" class="pin-popup"></div>
  <script>
    const generatedAt = "__GENERATED_AT__";
    const sourceCsv = "__SOURCE_CSV__";
    const sourcePin = "__SOURCE_PIN__";
    const basemapSvg = "__BASEMAP_SVG__";
    const shortBasemapSvg = "__SHORT_BASEMAP_SVG__";
    const hawaiiBasemapSvg = "__HAWAII_BASEMAP_SVG__";
    const mainDeployments = __MAIN_DEPLOYMENTS_JSON__;
    const hawaiiDeployments = __HAWAII_DEPLOYMENTS_JSON__;
    const shortMainDeployments = __SHORT_MAIN_DEPLOYMENTS_JSON__;
    const shortHawaiiDeployments = __SHORT_HAWAII_DEPLOYMENTS_JSON__;
    const mainMapImage = "__MAP_IMAGE__";
    const shortMapImage = "__SHORT_MAP_IMAGE__";
    const mainMapNoLakesImage = "__MAP_NO_LAKES_IMAGE__";
    const shortMapNoLakesImage = "__SHORT_MAP_NO_LAKES_IMAGE__";
    const hawaiiMapImage = "__HAWAII_MAP_IMAGE__";
    const pinImage = "__PIN_IMAGE__";
    const pinIsSvg = __PIN_IS_SVG__;
    const imageSize = { width: __IMAGE_WIDTH__, height: __IMAGE_HEIGHT__ };
    const hawaiiImageSize = { width: __HAWAII_IMAGE_WIDTH__, height: __HAWAII_IMAGE_HEIGHT__ };
    const projectionName = "__PROJECTION__";

    const MAX_ZOOM_SCALE = 9;
    const HOT_ZONES_FADE_START_SCALE = 7.1;
    const HOT_ZONES_FADE_END_SCALE = MAX_ZOOM_SCALE;
    const HOTZONE_DISTANCE = 82;
    const HOTZONE_MIN_RADIUS = 14;
    const HOTZONE_MAX_RADIUS = 72;
    const HOTZONE_BASE_RADIUS = 12;
    const HOTZONE_SCALE = 5.2;
    const HOTZONE_SCREEN_CELL = 64;
    const HOTZONE_MIN_CLUSTER_COUNT = 3;
    const HOTZONE_FILL = "rgba(0, 167, 81, 0.23)";
    const HOTZONE_STROKE = "rgba(0, 127, 61, 0.62)";
    const ZOOM_STEP = 1.18;
    const PIN_ANIMATION_DURATION = 520;
    const PIN_STAGGER_MAX = 250;
    const POINT_RADIUS_BASE = 2.2;
    const POINT_RADIUS_STEP = 0.08;

    const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pinDuration = prefersReducedMotion ? 30 : PIN_ANIMATION_DURATION;
    const pinDelayMax = prefersReducedMotion ? 0 : PIN_STAGGER_MAX;

    const stage = document.getElementById("stage");
    const mapImageEl = document.getElementById("mapImage");
    const hotCanvas = document.getElementById("hotCanvas");
    const pinCanvas = document.getElementById("pinCanvas");
    const hotCtx = hotCanvas.getContext("2d");
    const pinCtx = pinCanvas.getContext("2d");
    const popup = document.getElementById("popup");
    const pinImg = new Image();
    pinImg.src = pinImage;

    const layerState = { hotZonesEnabled: true, pinsEnabled: true, pointsEnabled: false };
    const mapFrames = {
      full: {
        label: "Full map",
        mapVariant: "generated_full_basemap",
        basemapSvg,
        images: { lakes: mainMapImage, noLakes: mainMapNoLakesImage },
        mainDeployments,
        hawaiiDeployments
      },
      short: {
        label: "Short map",
        mapVariant: "generated_clipped_basemap",
        basemapSvg: shortBasemapSvg,
        images: { lakes: shortMapImage, noLakes: shortMapNoLakesImage },
        mainDeployments: shortMainDeployments,
        hawaiiDeployments: shortHawaiiDeployments
      }
    };
    const frameProfiles = {
      full: {
        label: mapFrames.full.label,
        basemapSvg: mapFrames.full.basemapSvg,
        mapVariant: "generated_full_basemap",
        visiblePoints: mapFrames.full.mainDeployments.length + mapFrames.full.hawaiiDeployments.length,
        excludedPoints: 0
      },
      short: {
        label: mapFrames.short.label,
        basemapSvg: mapFrames.short.basemapSvg,
        mapVariant: "generated_clipped_basemap",
        visiblePoints: mapFrames.short.mainDeployments.length + mapFrames.short.hawaiiDeployments.length,
        excludedPoints: Math.max(
          0,
          mapFrames.full.mainDeployments.length + mapFrames.full.hawaiiDeployments.length -
            (mapFrames.short.mainDeployments.length + mapFrames.short.hawaiiDeployments.length)
        )
      }
    };
    let activeFrame = "full";
    let activeWater = "lakes";
    let transform = d3.zoomIdentity;
    let viewport = { width: 0, height: 0, ratio: 1 };
    let fitScale = 1;
    let raf = null;
    let pinRevealStart = performance.now();

    let mainPoints = [];
    let hawaiiPoints = [];
    let allPoints = [];

    function preparePoints(deployments) {
      return (deployments || [])
      .filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y))
      .map((d) => ({ ...d, _pinDelay: hashDeterministicDelay(d.id, d.zip, d.cc) }));
    }

    function activateFrameData(frameId) {
      const frame = mapFrames[frameId] || mapFrames.full;
      document.body.dataset.mapFrame = frameId;
      document.body.dataset.waterLayer = activeWater;
      mapImageEl.src = frame.images[activeWater] || frame.images.lakes;
      mainPoints = preparePoints(frame.mainDeployments);
      hawaiiPoints = preparePoints(frame.hawaiiDeployments);
      allPoints = mainPoints.concat(hawaiiPoints);
      startPinReveal();
    }

    activateFrameData(activeFrame);

    function resizeCanvas(canvas, ctx) {
      const rect = stage.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      viewport = { width: rect.width, height: rect.height, ratio };
      canvas.width = Math.max(1, Math.round(rect.width * ratio));
      canvas.height = Math.max(1, Math.round(rect.height * ratio));
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function resizeAll() {
      resizeCanvas(hotCanvas, hotCtx);
      resizeCanvas(pinCanvas, pinCtx);
    }

    function activeStageRect() {
      const rect = stage.getBoundingClientRect();
      return {
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom)
      };
    }

    function fitTransform() {
      const padX = Math.min(72, Math.max(20, viewport.width * 0.035));
      const padY = Math.min(56, Math.max(20, viewport.height * 0.035));
      const k = Math.min((viewport.width - padX * 2) / imageSize.width, (viewport.height - padY * 2) / imageSize.height);
      const x = (viewport.width - imageSize.width * k) / 2;
      const y = (viewport.height - imageSize.height * k) / 2;
      fitScale = k;
      return d3.zoomIdentity.translate(x, y).scale(k);
    }

    function frameProof() {
      const frame = mapFrames[activeFrame] || mapFrames.full;
      const fullPointCount = (mapFrames.full.mainDeployments.length || 0) + (mapFrames.full.hawaiiDeployments.length || 0);
      const framePointCount = (frame.mainDeployments.length || 0) + (frame.hawaiiDeployments.length || 0);
      return {
        id: activeFrame,
        label: frame.label,
        basemapSvg: frame.basemapSvg,
        mapVariant: frame.mapVariant,
        waterLayer: activeWater,
        stage: activeStageRect(),
        visiblePoints: framePointCount,
        excludedPoints: Math.max(0, fullPointCount - framePointCount),
        visibleMapRect: { x: 0, y: 0, width: imageSize.width, height: imageSize.height }
      };
    }

    function currentScale() {
      return Math.max(0.001, transform.k);
    }

    function relativeZoom() {
      return Math.max(1, transform.k / Math.max(0.001, fitScale));
    }

    function hotZoneOpacity() {
      if (transform.k <= HOT_ZONES_FADE_START_SCALE) return 1;
      if (transform.k >= HOT_ZONES_FADE_END_SCALE) return 0;
      const progress = (transform.k - HOT_ZONES_FADE_START_SCALE) / (HOT_ZONES_FADE_END_SCALE - HOT_ZONES_FADE_START_SCALE);
      return 1 - (progress * progress * (3 - 2 * progress));
    }

    function applyTransform() {
      mapImageEl.style.transform = `translate(${transform.x}px, ${transform.y}px) scale(${transform.k})`;
      draw();
    }

    function requestDraw() {
      if (raf !== null) return;
      raf = requestAnimationFrame(() => {
        raf = null;
        draw();
      });
    }

    function mapToScreen(point) {
      return {
        x: transform.applyX(point.x),
        y: transform.applyY(point.y)
      };
    }

    function draw() {
      hotCtx.clearRect(0, 0, viewport.width, viewport.height);
      pinCtx.clearRect(0, 0, viewport.width, viewport.height);
      if (layerState.hotZonesEnabled && hotZoneOpacity() > 0) {
        drawHotZones(hotCtx);
      }
      if (layerState.pointsEnabled) {
        drawPoints(pinCtx);
      }
      if (layerState.pinsEnabled) {
        const pending = drawPins(pinCtx, performance.now());
        if (pending) requestDraw();
      }
    }

    function buildScreenHotZones() {
      if (!allPoints.length) return [];
      const buckets = new Map();
      const mobileFactor = viewport.width < 760 ? 0.56 : 1;
      const cell = (HOTZONE_SCREEN_CELL * mobileFactor) / currentScale();
      const minClusterCount = viewport.width < 760 || relativeZoom() >= 2.2 ? 2 : HOTZONE_MIN_CLUSTER_COUNT;
      for (const point of allPoints) {
        const p = mapToScreen(point);
        if (p.x < -120 || p.y < -120 || p.x > viewport.width + 120 || p.y > viewport.height + 120) continue;
        const key = `${Math.floor(point.x / cell)}|${Math.floor(point.y / cell)}`;
        const entry = buckets.get(key) || { count: 0, x: 0, y: 0 };
        entry.count += 1;
        entry.x += point.x;
        entry.y += point.y;
        buckets.set(key, entry);
      }
      return [...buckets.values()]
        .filter((entry) => entry.count >= minClusterCount)
        .map((entry) => {
          const screenRadius = Math.min(
            HOTZONE_MAX_RADIUS,
            Math.max(HOTZONE_MIN_RADIUS, HOTZONE_BASE_RADIUS + Math.sqrt(entry.count) * HOTZONE_SCALE)
          );
          const radius = screenRadius / currentScale();
          return { x: entry.x / entry.count, y: entry.y / entry.count, radius, screenRadius, count: entry.count };
        })
        .sort((a, b) => b.screenRadius - a.screenRadius);
    }

    function drawHotZones(ctx) {
      const clusters = this.buildScreenHotZones ? this.buildScreenHotZones() : buildScreenHotZones();
      if (!clusters.length) return;
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);
      ctx.setLineDash([3, 4]);
      ctx.globalAlpha = hotZoneOpacity();
      for (const zone of clusters) {
        ctx.beginPath();
        ctx.fillStyle = HOTZONE_FILL;
        ctx.strokeStyle = HOTZONE_STROKE;
        ctx.lineWidth = 1.15 / currentScale();
        ctx.setLineDash([4 / currentScale(), 5 / currentScale()]);
        ctx.arc(zone.x, zone.y, zone.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawPoints(ctx) {
      const screenRadius = Math.max(1.8, Math.min(3.2, POINT_RADIUS_BASE + Math.log2(relativeZoom()) * POINT_RADIUS_STEP));
      const radius = screenRadius / currentScale();
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);
      for (const point of allPoints) {
        const p = mapToScreen(point);
        if (p.x < -18 || p.y < -18 || p.x > viewport.width + 18 || p.y > viewport.height + 18) continue;
        ctx.beginPath();
        ctx.fillStyle = "#00875a";
        ctx.strokeStyle = "rgba(0, 95, 72, 0.98)";
        ctx.lineWidth = 0.8 / currentScale();
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawPins(ctx, now) {
      const pinH = 16;
      const pinW = pinH * 0.63;
      let pending = false;
      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);
      for (const point of allPoints) {
        const p = mapToScreen(point);
        if (p.x < -35 || p.y < -44 || p.x > viewport.width + 35 || p.y > viewport.height + 35) continue;
        const delay = Number.isFinite(point._pinDelay) ? point._pinDelay : 0;
        const revealRaw = pinRevealStart === null ? 1 : (now - pinRevealStart - delay) / pinDuration;
        const reveal = Math.min(1, Math.max(0, revealRaw));
        if (reveal < 1) pending = true;
        if (reveal <= 0) continue;
        const eased = 1 - Math.pow(1 - reveal, 2);
        const scale = 0.78 + 0.22 * eased;
        const alpha = 0.16 + 0.84 * eased;
        const drop = (1 - eased) * 8;
        const markerZoom = 1 + Math.log2(relativeZoom()) * 0.08;
        const drawW = pinW * scale * markerZoom / currentScale();
        const drawH = pinH * scale * markerZoom / currentScale();
        ctx.save();
        ctx.globalAlpha = alpha;
        if (pinImg.complete && pinImg.naturalWidth > 0) {
          ctx.drawImage(pinImg, point.x - drawW / 2, point.y - drawH + drop / currentScale(), drawW, drawH);
        } else {
          ctx.beginPath();
          ctx.fillStyle = "#00a06b";
          ctx.strokeStyle = "#29445b";
          ctx.lineWidth = 1.4 / currentScale();
          ctx.arc(point.x, point.y - 6 / currentScale(), 4.2 * scale / currentScale(), 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
        ctx.restore();
      }
      ctx.restore();
      if (!pending && pinRevealStart !== null) pinRevealStart = null;
      return pending;
    }

    function startPinReveal() {
      pinRevealStart = performance.now();
      requestDraw();
    }

    function handleZoom(event) {
      transform = event.transform;
      applyTransform();
    }

    const zoom = d3.zoom()
      .scaleExtent([0.18, MAX_ZOOM_SCALE])
      .touchable(() => true)
      .filter((event) => !event.button)
      .on("zoom", handleZoom);

    const stageSelection = d3.select(stage).call(zoom);

    function setTransform(next, animate = false) {
      transform = next;
      if (animate && !prefersReducedMotion) {
        stageSelection.transition().duration(220).ease(d3.easeCubicOut).call(zoom.transform, next);
      } else {
        stageSelection.call(zoom.transform, next);
        applyTransform();
      }
    }

    function rebuildControls() {
      document.getElementById("hotZonesToggle").classList.toggle("active", layerState.hotZonesEnabled);
      document.getElementById("pinsToggle").classList.toggle("active", layerState.pinsEnabled);
      document.getElementById("pointsToggle").classList.toggle("active", layerState.pointsEnabled);
      document.getElementById("fullFrameBtn").classList.toggle("active", activeFrame === "full");
      document.getElementById("shortFrameBtn").classList.toggle("active", activeFrame === "short");
      document.getElementById("lakesBtn").classList.toggle("active", activeWater === "lakes");
      document.getElementById("noLakesBtn").classList.toggle("active", activeWater === "noLakes");
    }

    function setFrame(frame) {
      if (!mapFrames[frame]) return;
      activeFrame = frame;
      activateFrameData(frame);
      rebuildControls();
      window.requestAnimationFrame(() => {
        resizeAll();
        setTransform(fitTransform(), true);
        if (window.__LSN_MAP_FINAL_PROOF__) window.__LSN_MAP_FINAL_PROOF__.activeFrame = frameProof();
      });
    }

    function setWater(waterLayer) {
      if (!["lakes", "noLakes"].includes(waterLayer)) return;
      activeWater = waterLayer;
      activateFrameData(activeFrame);
      rebuildControls();
      requestDraw();
      if (window.__LSN_MAP_FINAL_PROOF__) window.__LSN_MAP_FINAL_PROOF__.activeFrame = frameProof();
    }

    function onLayerStateUpdate(next) {
      const previousPinsEnabled = layerState.pinsEnabled;
      layerState.hotZonesEnabled = next.hotZonesEnabled;
      layerState.pinsEnabled = next.pinsEnabled;
      layerState.pointsEnabled = next.pointsEnabled;
      rebuildControls();
      if (!previousPinsEnabled && layerState.pinsEnabled) startPinReveal();
      else requestDraw();
    }

    function buildHotZones(points, distancePx, mapWidth, mapHeight) {
      const validPoints = Array.isArray(points) ? points.filter((point) => Number.isFinite(point?.x) && Number.isFinite(point?.y)) : [];
      if (!validPoints.length) return [];
      const cellSize = distancePx;
      const cells = new Map();
      const parent = [...Array(validPoints.length).keys()];
      const rank = new Array(validPoints.length).fill(1);
      const clusters = [];
      const getCell = (point) => [Math.floor(point.x / cellSize), Math.floor(point.y / cellSize)];
      const key = (cx, cy) => `${cx}|${cy}`;
      validPoints.forEach((point, idx) => {
        const [cx, cy] = getCell(point);
        const ids = cells.get(key(cx, cy)) || [];
        ids.push(idx);
        cells.set(key(cx, cy), ids);
        for (let ox = -1; ox <= 1; ox++) {
          for (let oy = -1; oy <= 1; oy++) {
            const nearby = cells.get(key(cx + ox, cy + oy)) || [];
            for (const otherIdx of nearby) {
              if (otherIdx >= idx) continue;
              const dx = validPoints[otherIdx].x - point.x;
              const dy = validPoints[otherIdx].y - point.y;
              if (dx * dx + dy * dy <= distancePx * distancePx) union(parent, rank, idx, otherIdx);
            }
          }
        }
      });
      for (let i = 0; i < validPoints.length; i++) {
        const root = find(parent, i);
        clusters[root] = clusters[root] || { count: 0, x: 0, y: 0 };
        clusters[root].count += 1;
        clusters[root].x += validPoints[i].x;
        clusters[root].y += validPoints[i].y;
      }
      return Object.values(clusters).filter(Boolean).map((entry) => ({
        x: entry.x / entry.count,
        y: entry.y / entry.count,
        radius: Math.min(HOTZONE_MAX_RADIUS, Math.max(HOTZONE_MIN_RADIUS, HOTZONE_BASE_RADIUS + Math.sqrt(entry.count) * HOTZONE_SCALE)),
        count: entry.count
      }));
    }

    function hashDeterministicDelay(...parts) {
      let seed = 0;
      for (const part of parts) {
        const value = String(part ?? "");
        for (let i = 0; i < value.length; i++) seed = (seed * 31 + value.charCodeAt(i)) >>> 0;
      }
      return seedDelay(seed) % (pinDelayMax + 1);
    }
    function seedDelay(seed) {
      let value = (seed ^ 0x5bd1e995) >>> 0;
      value ^= value << 13;
      value ^= value >>> 17;
      value ^= value << 5;
      return value & 0xffff;
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
      if (rank[rootA] < rank[rootB]) parent[rootA] = rootB;
      else if (rank[rootA] > rank[rootB]) parent[rootB] = rootA;
      else {
        parent[rootB] = rootA;
        rank[rootA] += 1;
      }
    }

    document.getElementById("hotZonesToggle").addEventListener("click", () => {
      onLayerStateUpdate({ ...layerState, hotZonesEnabled: !layerState.hotZonesEnabled });
    });
    document.getElementById("pinsToggle").addEventListener("click", () => {
      onLayerStateUpdate({ ...layerState, pinsEnabled: !layerState.pinsEnabled });
    });
    document.getElementById("pointsToggle").addEventListener("click", () => {
      onLayerStateUpdate({ ...layerState, pointsEnabled: !layerState.pointsEnabled });
    });
    document.getElementById("fullFrameBtn").addEventListener("click", () => setFrame("full"));
    document.getElementById("shortFrameBtn").addEventListener("click", () => setFrame("short"));
    document.getElementById("lakesBtn").addEventListener("click", () => setWater("lakes"));
    document.getElementById("noLakesBtn").addEventListener("click", () => setWater("noLakes"));
    document.getElementById("fitBtn").addEventListener("click", () => setTransform(fitTransform(), true));
    document.getElementById("zoomInBtn").addEventListener("click", () => setTransform(transform.scale(ZOOM_STEP), true));
    document.getElementById("zoomOutBtn").addEventListener("click", () => setTransform(transform.scale(1 / ZOOM_STEP), true));
    document.getElementById("fullscreenBtn").addEventListener("click", async () => {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
      else await document.exitFullscreen();
      setTimeout(() => {
        resizeAll();
        setTransform(fitTransform(), true);
      }, 180);
    });
    function handleViewportChange() {
      resizeAll();
      applyTransform();
    }
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("orientationchange", handleViewportChange);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", handleViewportChange);
      window.visualViewport.addEventListener("scroll", handleViewportChange);
    }
    pinImg.onload = requestDraw;

    resizeAll();
    setTransform(fitTransform(), false);
    startPinReveal();
    rebuildControls();
    window.__LSN_MAP_FINAL_PROOF__ = {
      generatedAt,
      sourceCsv,
      sourcePin,
      basemapSvg,
      hawaiiBasemapSvg,
      projectionName,
      renderer: "d3-gis-final-single-transform-canvas",
      rows: mainDeployments.length + hawaiiDeployments.length,
      activeFrame: frameProof(),
      frameProfiles,
      waterLayer: activeWater,
      mainRows: mainPoints.length,
      hawaiiRows: hawaiiPoints.length,
      points: allPoints.length,
      plottedMain: mainPoints.length,
      plottedHawaii: hawaiiPoints.length,
      hotZonesEnabled: layerState.hotZonesEnabled,
      pinsEnabled: layerState.pinsEnabled,
      pointsEnabled: layerState.pointsEnabled,
      pointLayer: "canvas",
      hotZoneClustering: "screen-space",
      hotZoneFadeStartScale: HOT_ZONES_FADE_START_SCALE,
      hotZoneFadeEndScale: HOT_ZONES_FADE_END_SCALE,
      hasHawaiiInset: false
    };
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
