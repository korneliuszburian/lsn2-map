"""Render a standalone Leaflet prototype on the supplied LSN map artwork."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INPUT = "data/output/clients_geocoded.csv"
DEFAULT_MAP_IMAGE = "data/assets/client-map/new-na-map.svg"
DEFAULT_PIN_IMAGE = "data/assets/client-map/pin-na-map.svg"
DEFAULT_OUTPUT = "data/output/lsn-map-options.html"


def read_png_size(path: Path) -> tuple[int, int]:
    """Read PNG dimensions without adding an image-processing dependency."""
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Expected PNG image: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def read_svg_size(path: Path) -> tuple[float, float]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', text)
    if viewbox_match:
        values = [float(part) for part in re.split(r"[\s,]+", viewbox_match.group(1).strip()) if part]
        if len(values) == 4:
            return values[2], values[3]
    width_match = re.search(r'width=["\']([0-9.]+)', text)
    height_match = re.search(r'height=["\']([0-9.]+)', text)
    if width_match and height_match:
        return float(width_match.group(1)), float(height_match.group(1))
    raise ValueError(f"Could not read SVG dimensions from {path}")


def read_image_size(path: Path) -> tuple[float, float]:
    if path.suffix.lower() == ".svg":
        return read_svg_size(path)
    return read_png_size(path)


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    if path.suffix.lower() == ".svg":
        return f"data:image/svg+xml;base64,{encoded}"
    return f"data:image/png;base64,{encoded}"


def read_deployments(path: Path) -> list[dict[str, object]]:
    """Read matched deployment rows from the geocoded CSV export."""
    deployments: list[dict[str, object]] = []
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


def render_html(input_path: Path, map_image_path: Path, pin_image_path: Path, title: str) -> str:
    deployments = read_deployments(input_path)
    if not deployments:
        raise ValueError(f"No geocoded deployments found in {input_path}")

    width, height = read_image_size(map_image_path)
    generated_at = datetime.now(timezone.utc).isoformat()
    map_profile = build_map_profile(width, height)

    replacements = {
        "__TITLE__": title,
        "__DEPLOYMENTS_JSON__": json.dumps(deployments, ensure_ascii=True, separators=(",", ":")),
        "__MAP_IMAGE__": image_data_uri(map_image_path),
        "__PIN_IMAGE__": image_data_uri(pin_image_path),
        "__PIN_IS_SVG__": json.dumps(pin_image_path.suffix.lower() == ".svg"),
        "__IMAGE_WIDTH__": str(width),
        "__IMAGE_HEIGHT__": str(height),
        "__MAP_PROFILE_JSON__": json.dumps(map_profile, ensure_ascii=True, separators=(",", ":")),
        "__GENERATED_AT__": generated_at,
        "__SOURCE_CSV__": str(input_path),
        "__SOURCE_MAP__": str(map_image_path),
        "__SOURCE_PIN__": str(pin_image_path),
    }

    html = HTML_TEMPLATE
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return html


def write_html(html: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def build_map_profile(width: float, height: float) -> dict[str, object]:
    scale_x = width / 1731
    scale_y = height / 1800

    def point(x: float, y: float, radius: float) -> dict[str, float]:
        return {
            "x": round(x * scale_x, 3),
            "y": round(y * scale_y, 3),
            "radius": round(radius * (scale_x + scale_y) / 2, 3),
        }

    return {
        "projection": {
            "lonMin": -170,
            "lonMax": -50,
            "latMin": 14,
            "latMax": 72,
            "imageLeft": round(135 * scale_x, 3),
            "imageRight": round(1585 * scale_x, 3),
            "imageTop": round(125 * scale_y, 3),
            "imageBottom": round(1660 * scale_y, 3),
        },
        "regionAnchors": {
            "Canada North": point(880, 285, 150),
            "Canada West": point(635, 500, 118),
            "Canada Central": point(875, 555, 112),
            "Canada East": point(1180, 610, 120),
            "Pacific Northwest": point(525, 735, 86),
            "West Coast": point(500, 1050, 92),
            "Mountain": point(700, 955, 110),
            "Midwest": point(925, 910, 110),
            "Northeast": point(1235, 820, 96),
            "Southeast": point(1095, 1140, 112),
            "South Central": point(850, 1150, 105),
            "Mexico North": point(735, 1330, 78),
            "Mexico West": point(680, 1435, 68),
            "Mexico Central": point(780, 1465, 98),
            "Mexico South": point(940, 1580, 92),
        },
    }


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
    parser = argparse.ArgumentParser(description="Render LSN map comparison prototype")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to clients_geocoded.csv")
    parser.add_argument("--map-image", default=DEFAULT_MAP_IMAGE, help="Path to browser-ready SVG/PNG artwork")
    parser.add_argument("--pin-image", default=DEFAULT_PIN_IMAGE, help="Path to browser-ready SVG/PNG pin")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path")
    parser.add_argument("--title", default="LSN North America", help="Title shown in the prototype")
    args = parser.parse_args()

    input_path = Path(args.input)
    map_image_path = Path(args.map_image)
    pin_image_path = Path(args.pin_image)
    output_path = Path(args.output)

    html = render_html(input_path, map_image_path, pin_image_path, args.title)
    write_html(html, output_path)
    print(f"Rendered {output_path} from {input_path}")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ - Map Options</title>
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
      --violet: #6366f1;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }
    html, body, #map { height: 100%; margin: 0; }
    body { background: var(--bg); color: var(--ink); overflow: hidden; }
    #map { position: fixed; inset: 0; background: #f8faf9; }

    .leaflet-container { background: #f8faf9; font-family: inherit; }
    .leaflet-image-layer { image-rendering: auto; }
    .marker-canvas { pointer-events: auto; }
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

    .brand { min-width: 214px; padding: 0 8px 0 4px; }
    .brand h1 { margin: 0; font-size: 20px; line-height: 1.05; letter-spacing: 0; }
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
      transition: transform .16s ease, background .16s ease, border-color .16s ease;
      white-space: nowrap;
    }
    .mode-btn:hover, .tool-btn:hover { transform: translateY(-1px); border-color: rgba(0,127,61,.34); }
    .mode-btn.active { background: var(--green); color: #fff; border-color: var(--green); }
    .tool-btn { min-width: 42px; padding: 0 11px; }

    .panel {
      position: fixed;
      z-index: 590;
      right: 24px;
      top: 20px;
      width: 272px;
      max-height: calc(100vh - 40px);
      overflow: auto;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: 0 20px 60px rgba(15, 23, 42, .14);
      backdrop-filter: blur(18px) saturate(1.25);
    }

    .metrics {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }
    .metric {
      min-height: 78px;
      border: 1px solid rgba(23,35,31,.10);
      border-radius: 8px;
      background: rgba(255,255,255,.62);
      padding: 10px;
    }
    .metric-label {
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 10px;
      font-weight: 820;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .metric-value { font-size: 22px; line-height: 1; font-weight: 820; letter-spacing: 0; }
    .metric-note { margin-top: 5px; color: var(--muted); font-size: 11px; font-weight: 620; }

    .legend-title {
      margin: 14px 0 8px;
      color: #24362e;
      font-size: 11px;
      font-weight: 820;
      text-transform: uppercase;
      letter-spacing: 0;
    }
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
      <p><span id="headerCount">0</span> deployments</p>
    </div>
    <nav class="modebar" aria-label="Visualization modes">
      <button class="mode-btn active" data-mode="points">Pins</button>
      <button class="mode-btn" data-mode="regions">Regions</button>
      <button class="mode-btn" data-mode="badges">Flags</button>
      <button class="mode-btn" data-mode="heat">Heatmap</button>
      <button class="mode-btn" data-mode="hybrid">Heat + Pins</button>
    </nav>
    <div class="toolbar">
      <button class="tool-btn" id="fitBtn" title="Fit map" aria-label="Fit map">Fit</button>
      <button class="tool-btn" id="fullscreenBtn" title="Fullscreen" aria-label="Fullscreen">Full</button>
    </div>
  </header>

  <aside class="panel" aria-label="Map summary">
    <div class="metrics">
      <div class="metric"><div class="metric-label">Deployments</div><div class="metric-value" id="totalDeployments">0</div><div class="metric-note">mapped rows</div></div>
      <div class="metric"><div class="metric-label">Generators</div><div class="metric-value" id="totalGenerators">0</div><div class="metric-note">total count</div></div>
      <div class="metric"><div class="metric-label">Countries</div><div class="metric-value" id="countryTotal">0</div><div class="metric-note">US / CA / MX</div></div>
      <div class="metric"><div class="metric-label">Mode</div><div class="metric-value" id="modeLabel">Pins</div><div class="metric-note">active view</div></div>
    </div>
    <div class="legend-title">Status</div>
    <div id="statusLegend"></div>
    <div class="legend-title">Country</div>
    <div id="countryLegend"></div>
  </aside>

  <script>
    const generatedAt = "__GENERATED_AT__";
    const sourceCsv = "__SOURCE_CSV__";
    const sourceMap = "__SOURCE_MAP__";
    const sourcePin = "__SOURCE_PIN__";
    const deployments = __DEPLOYMENTS_JSON__;
    const mapImage = "__MAP_IMAGE__";
    const pinImage = "__PIN_IMAGE__";
    const pinIsSvg = __PIN_IS_SVG__;
    const imageSize = { width: __IMAGE_WIDTH__, height: __IMAGE_HEIGHT__ };
    const mapProfile = __MAP_PROFILE_JSON__;
    const projection = mapProfile.projection;
    const statusColors = {
      "Deployed": "#10b981",
      "Service Due": "#f59e0b",
      "Planned": "#6366f1",
      "Decommissioned": "#ef4444",
      "Under Maintenance": "#f59e0b",
      "Inactive": "#ef4444"
    };
    const countryColors = { US: "#007f3d", CA: "#345168", MX: "#3f3f41" };
    const modeLabels = { points: "Pins", regions: "Regions", badges: "Flags", heat: "Heat", hybrid: "Hybrid" };
    const format = new Intl.NumberFormat("en-US");
    const regionAnchors = mapProfile.regionAnchors;
    const pinIcon = new Image();
    let pinReady = false;
    pinIcon.onload = () => {
      pinReady = true;
      if (window.__markerCanvasLayer) window.__markerCanvasLayer.draw();
    };
    pinIcon.src = pinImage;

    function project(lon, lat) {
      const xRatio = (lon - projection.lonMin) / (projection.lonMax - projection.lonMin);
      const yRatio = (projection.latMax - lat) / (projection.latMax - projection.latMin);
      const x = projection.imageLeft + xRatio * (projection.imageRight - projection.imageLeft);
      const y = projection.imageTop + yRatio * (projection.imageBottom - projection.imageTop);
      return [x, y];
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function hashString(value) {
      let hash = 2166136261;
      const text = String(value ?? "");
      for (let i = 0; i < text.length; i += 1) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
      }
      return hash >>> 0;
    }

    function regionProject(d) {
      const anchor = regionAnchors[d.region];
      if (!anchor) return [...project(d.lon, d.lat), "lat_lon_fallback"];
      const hash = hashString(`${d.id}|${d.zip}|${d.region}`);
      const angle = ((hash % 360) / 180) * Math.PI;
      const spread = Math.sqrt(((hash >>> 8) % 1000) / 1000);
      const ring = 0.3 + spread * 0.7;
      const x = anchor.x + Math.cos(angle) * anchor.radius * ring;
      const y = anchor.y + Math.sin(angle) * anchor.radius * 0.62 * ring;
      return [x, y, "region_anchor"];
    }

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

    function regionPopupHtml(entry) {
      const rows = [
        ["Region", entry.region],
        ["Country", entry.cc],
        ["Deployments", format.format(entry.count)],
        ["Generators", format.format(entry.generators)],
        ["Top status", entry.topStatus],
        ["Placement", "Regional overview"]
      ];
      return `<div class="popup"><h2>${escapeHtml(entry.region)}</h2><div class="popup-sub">${escapeHtml(entry.cc)} | ${format.format(entry.count)} deployments</div><div class="popup-grid">${rows.map(([k,v]) => `<div><div class="popup-label">${escapeHtml(k)}</div><div class="popup-value">${escapeHtml(v)}</div></div>`).join("")}</div></div>`;
    }

    const map = L.map("map", {
      crs: L.CRS.Simple,
      minZoom: -1.6,
      maxZoom: 2.6,
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

    const projected = deployments.map(d => {
      const [pointRawX, pointRawY] = project(d.lon, d.lat);
      const pointX = clamp(pointRawX, 8, imageSize.width - 8);
      const pointY = clamp(pointRawY, 8, imageSize.height - 8);
      const pointLeafletY = imageSize.height - pointY;
      const [rawX, rawY, placement] = regionProject(d);
      const x = clamp(rawX, 8, imageSize.width - 8);
      const y = clamp(rawY, 8, imageSize.height - 8);
      const leafletY = imageSize.height - y;
      return {
        ...d,
        pointRawX,
        pointRawY,
        pointX,
        pointY,
        pointLeafletY,
        pointClamped: pointX !== pointRawX || pointY !== pointRawY,
        pointLatlng: L.latLng(pointLeafletY, pointX),
        rawX,
        rawY,
        x,
        y,
        leafletY,
        placement,
        clamped: x !== rawX || y !== rawY,
        latlng: L.latLng(leafletY, x)
      };
    });

    function buildRegionHeatPoints(points) {
      const groups = new Map();
      for (const d of points) {
        const key = `${d.region}|${d.cc}`;
        const entry = groups.get(key) || { count: 0, x: 0, y: 0 };
        entry.count += 1;
        entry.x += d.x;
        entry.y += d.leafletY;
        groups.set(key, entry);
      }
      return [...groups.values()].map(entry => [
        entry.y / entry.count,
        entry.x / entry.count,
        Math.max(0.5, Math.min(1.6, entry.count / 55))
      ]);
    }

    const heatPoints = buildRegionHeatPoints(projected);

    const CanvasMarkerLayer = L.Layer.extend({
      initialize(points) {
        this.points = points;
        this.mode = "points";
      },
      onAdd(mapInstance) {
        this.map = mapInstance;
        this.canvas = L.DomUtil.create("canvas", "marker-canvas leaflet-zoom-animated");
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
      exactPointToCanvas(d) {
        return this.pointToCanvas(d);
      },
      draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.viewport.x, this.viewport.y);
        if (this.mode === "points") this.drawExactPoints(ctx);
        else if (this.mode === "badges") this.drawExactFlags(ctx);
        else this.drawRegionBubbles(ctx);
      },
      drawExactPoints(ctx) {
        const zoom = this.map.getZoom();
        const radius = Math.max(2.1, Math.min(5.2, 3.1 + zoom * 0.55));
        const pinHeight = Math.max(13, Math.min(24, 17 + zoom * 1.3));
        const pinWidth = pinHeight * 0.63;
        ctx.save();
        ctx.lineWidth = 1.25;
        for (const d of this.points) {
          const p = this.exactPointToCanvas(d);
          if (p.x < -20 || p.y < -20 || p.x > this.viewport.x + 20 || p.y > this.viewport.y + 20) continue;
          if (pinReady) {
            ctx.drawImage(pinIcon, p.x - pinWidth / 2, p.y - pinHeight + 2, pinWidth, pinHeight);
          } else {
            ctx.beginPath();
            ctx.fillStyle = statusColors[d.status] || "#10b981";
            ctx.strokeStyle = "rgba(255,255,255,.92)";
            ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
          }
        }
        ctx.restore();
      },
      groupByRegion() {
        const groups = new Map();
        for (const d of this.points) {
          const key = `${d.region}|${d.cc}`;
          const entry = groups.get(key) || { region: d.region, cc: d.cc, count: 0, generators: 0, x: 0, y: 0, lat: 0, lng: 0, statuses: {} };
          const p = this.pointToCanvas(d);
          entry.count += 1;
          entry.generators += Number(d.count || 0);
          entry.x += p.x;
          entry.y += p.y;
          entry.lat += d.latlng.lat;
          entry.lng += d.latlng.lng;
          entry.statuses[d.status] = (entry.statuses[d.status] || 0) + 1;
          groups.set(key, entry);
        }
        return [...groups.values()].map(entry => {
          const topStatus = Object.entries(entry.statuses).sort((a, b) => b[1] - a[1])[0]?.[0] || "";
          return {
            ...entry,
            x: entry.x / entry.count,
            y: entry.y / entry.count,
            latlng: L.latLng(entry.lat / entry.count, entry.lng / entry.count),
            topStatus
          };
        });
      },
      bubbleRadius(entry) {
        return Math.max(15, Math.min(36, 9 + Math.sqrt(entry.count) * 2.4));
      },
      drawRegionBubbles(ctx) {
        const groups = this.groupByRegion();
        ctx.save();
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        for (const entry of groups) {
          const radius = this.bubbleRadius(entry);
          ctx.beginPath();
          ctx.fillStyle = countryColors[entry.cc] || "#10b981";
          ctx.globalAlpha = 0.86;
          ctx.arc(entry.x, entry.y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = "rgba(255,255,255,.95)";
          ctx.stroke();
          ctx.beginPath();
          ctx.fillStyle = "rgba(255,255,255,.94)";
          ctx.arc(entry.x + radius * 0.34, entry.y - radius * 0.34, Math.max(4, radius * 0.18), 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#fff";
          ctx.font = `850 ${Math.max(11, Math.min(15, radius * 0.42))}px Inter, system-ui, sans-serif`;
          ctx.fillText(format.format(entry.count), entry.x, entry.y + 0.5);
        }
        ctx.restore();
      },
      drawExactFlags(ctx) {
        const zoom = this.map.getZoom();
        const flagHeight = Math.max(9, Math.min(17, 11 + zoom * 1.1));
        const flagWidth = flagHeight * 1.22;
        const poleHeight = flagHeight + 8;
        ctx.save();
        for (const d of this.points) {
          const p = this.exactPointToCanvas(d);
          if (p.x < -24 || p.y < -28 || p.x > this.viewport.x + 24 || p.y > this.viewport.y + 24) continue;
          const x = p.x;
          const y = p.y;
          const flagX = x + 1;
          const flagY = y - poleHeight;
          ctx.beginPath();
          ctx.moveTo(x, y - poleHeight + 1);
          ctx.lineTo(x, y + 2);
          ctx.lineWidth = 2.8;
          ctx.strokeStyle = "rgba(255,255,255,.9)";
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(x, y - poleHeight + 1);
          ctx.lineTo(x, y + 2);
          ctx.lineWidth = 1.35;
          ctx.strokeStyle = "rgba(63,63,65,.64)";
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(flagX, flagY);
          ctx.lineTo(flagX + flagWidth, flagY + flagHeight * 0.08);
          ctx.lineTo(flagX + flagWidth * 0.78, flagY + flagHeight * 0.5);
          ctx.lineTo(flagX + flagWidth, flagY + flagHeight * 0.92);
          ctx.lineTo(flagX, flagY + flagHeight);
          ctx.closePath();
          ctx.fillStyle = statusColors[d.status] || countryColors[d.cc] || "#10b981";
          ctx.fill();
          ctx.lineWidth = 1.1;
          ctx.strokeStyle = "rgba(255,255,255,.92)";
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x, y + 2.5, 2.4, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(255,255,255,.95)";
          ctx.fill();
          ctx.strokeStyle = "rgba(63,63,65,.35)";
          ctx.stroke();
        }
        ctx.restore();
      },
      roundRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
      },
      onClick(event) {
        const clickPoint = this.map.latLngToLayerPoint(event.latlng);
        if (this.mode === "points" || this.mode === "badges") {
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
          const threshold = this.mode === "badges" ? 20 : 18;
          const offset = this.mode === "badges" ? [8, -16] : [0, -6];
          if (nearest && nearestDist <= threshold) {
            L.popup({ closeButton: true, offset })
              .setLatLng(nearest.latlng)
              .setContent(popupHtml(nearest))
              .openOn(this.map);
          }
          return;
        }
        const groups = this.groupByRegion();
        for (const entry of groups) {
          const groupPoint = this.map.latLngToLayerPoint(entry.latlng);
          const hitRadius = this.mode === "badges" ? 34 : this.bubbleRadius(entry) + 8;
          if (groupPoint.distanceTo(clickPoint) <= hitRadius) {
            L.popup({ closeButton: true, offset: [0, -8] })
              .setLatLng(entry.latlng)
              .setContent(regionPopupHtml(entry))
              .openOn(this.map);
            return;
          }
        }
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
        if (nearest && nearestDist <= 26) {
          L.popup({ closeButton: true, offset: [0, -6] })
            .setLatLng(nearest.latlng)
            .setContent(popupHtml(nearest))
            .openOn(this.map);
        }
      }
    });

    const heatLayer = L.heatLayer(heatPoints, {
      radius: 44,
      blur: 28,
      maxZoom: -1,
      minOpacity: 0.26,
      gradient: { 0.18: "#6ee7b7", 0.42: "#22c55e", 0.68: "#f59e0b", 1.0: "#ef4444" }
    });
    const markerCanvasLayer = new CanvasMarkerLayer(projected);
    window.__markerCanvasLayer = markerCanvasLayer;

    function setMode(mode) {
      for (const layer of [markerCanvasLayer, heatLayer]) map.removeLayer(layer);
      if (mode === "points") { markerCanvasLayer.setMode("points"); markerCanvasLayer.addTo(map); }
      if (mode === "regions") { markerCanvasLayer.setMode("regions"); markerCanvasLayer.addTo(map); }
      if (mode === "badges") { markerCanvasLayer.setMode("badges"); markerCanvasLayer.addTo(map); }
      if (mode === "heat") heatLayer.addTo(map);
      if (mode === "hybrid") { heatLayer.addTo(map); markerCanvasLayer.setMode("points"); markerCanvasLayer.addTo(map); }
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
    document.getElementById("totalGenerators").textContent = format.format(projected.reduce((sum, d) => sum + Number(d.count || 0), 0));
    document.getElementById("countryTotal").textContent = format.format(Object.keys(countBy("cc")).length);
    renderLegend("statusLegend", countBy("status"), label => statusColors[label] || "#64748b");
    renderLegend("countryLegend", countBy("cc"), label => countryColors[label] || "#64748b");

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
      sourceMap,
      sourcePin,
      rows: deployments.length,
      plotted: projected.length,
      clamped: projected.filter(d => d.clamped).length,
      renderer: "svg-map-canvas-pins-and-region-aggregates",
      visualContract: "branded_overview_display_placement_not_gis",
      mapProfile,
      pinSvg: pinIsSvg,
      pointPlacement: {
        lonLatLinear: projected.length,
        clamped: projected.filter(d => d.pointClamped).length
      },
      placementMethods: {
        regionAnchor: projected.filter(d => d.placement === "region_anchor").length,
        latLonFallback: projected.filter(d => d.placement === "lat_lon_fallback").length
      },
      markerIcons: document.querySelectorAll(".leaflet-marker-icon").length,
      markerCanvas: document.querySelectorAll("canvas.marker-canvas").length,
      zoomAnimation: false
    };
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
