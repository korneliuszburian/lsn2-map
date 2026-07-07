"""Render a Figma-aligned static map component prototype."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.render_lsn_map_options import build_map_profile, image_data_uri, read_deployments, read_image_size, write_html


DEFAULT_INPUT = "data/output/clients_geocoded.csv"
DEFAULT_MAP_IMAGE = "data/assets/client-map/new-na-map.svg"
DEFAULT_OUTPUT = "data/output/lsn-map-figma.html"


def render_html(input_path: Path, map_image_path: Path, title: str) -> str:
    deployments = read_deployments(input_path)
    if not deployments:
        raise ValueError(f"No geocoded deployments found in {input_path}")

    width, height = read_image_size(map_image_path)
    replacements = {
        "__TITLE__": title,
        "__DEPLOYMENTS_JSON__": json.dumps(deployments, ensure_ascii=True, separators=(",", ":")),
        "__MAP_IMAGE__": image_data_uri(map_image_path),
        "__IMAGE_WIDTH__": str(width),
        "__IMAGE_HEIGHT__": str(height),
        "__MAP_PROFILE_JSON__": json.dumps(build_map_profile(width, height), ensure_ascii=True, separators=(",", ":")),
        "__GENERATED_AT__": datetime.now(timezone.utc).isoformat(),
        "__SOURCE_CSV__": str(input_path),
        "__SOURCE_MAP__": str(map_image_path),
    }

    html = HTML_TEMPLATE
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Figma Map Zoom-In prototype")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to clients_geocoded.csv")
    parser.add_argument("--map-image", default=DEFAULT_MAP_IMAGE, help="Path to browser-ready SVG/PNG artwork")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path")
    parser.add_argument("--title", default="LSN2 North America - Figma Map", help="Document title")
    args = parser.parse_args()

    html = render_html(Path(args.input), Path(args.map_image), args.title)
    write_html(html, Path(args.output))
    print(f"Rendered {args.output} from {args.input}")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root {
      --green: #00a751;
      --green-dark: #007c3c;
      --blue: #345168;
      --map-grey: #d3d3d4;
      background: #fff;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; margin: 0; }
    body {
      min-height: 100vh;
      overflow-x: auto;
      background: #fff;
    }

    .figma-frame {
      position: relative;
      width: 844px;
      height: 1820px;
      margin: 24px auto;
      background: #fff;
      overflow: hidden;
    }

    .map-card {
      position: absolute;
      left: 20px;
      width: 804px;
      height: 880px;
      overflow: hidden;
      background: #fff;
    }

    .map-card[data-variant="overview"] { top: 20px; }
    .map-card[data-variant="zoom"] { top: 920px; }

    .map-card canvas {
      position: absolute;
      inset: 0;
      width: 804px;
      height: 880px;
      display: block;
    }

    .zoom-glyph {
      position: absolute;
      left: 0;
      bottom: 0;
      width: 34px;
      height: 34px;
      border: 0;
      background: transparent;
      padding: 0;
      cursor: default;
    }

    .zoom-glyph::before {
      content: "";
      position: absolute;
      left: 11px;
      top: 8px;
      width: 11px;
      height: 11px;
      border: 1.6px solid #3c5165;
      border-radius: 50%;
      background: rgba(255,255,255,.72);
    }

    .zoom-glyph::after {
      content: "";
      position: absolute;
      left: 21px;
      top: 20px;
      width: 8px;
      height: 1.6px;
      border-radius: 999px;
      background: #3c5165;
      transform: rotate(45deg);
      transform-origin: left center;
    }

    @media (max-width: 900px) {
      body { background: #fff; }
      .figma-frame {
        margin: 0;
        transform: scale(calc((100vw - 1px) / 844));
        transform-origin: top left;
      }
    }
  </style>
</head>
<body>
  <main class="figma-frame" aria-label="LSN2 North America map Figma component">
    <section class="map-card" data-variant="overview" data-node-id="1715:3526">
      <canvas width="804" height="880" data-map-canvas="overview"></canvas>
      <button class="zoom-glyph" aria-label="Zoom map"></button>
    </section>
    <section class="map-card" data-variant="zoom" data-node-id="1715:3528">
      <canvas width="804" height="880" data-map-canvas="zoom"></canvas>
      <button class="zoom-glyph" aria-label="Zoom map"></button>
    </section>
  </main>

  <script>
    const generatedAt = "__GENERATED_AT__";
    const sourceCsv = "__SOURCE_CSV__";
    const sourceMap = "__SOURCE_MAP__";
    const deployments = __DEPLOYMENTS_JSON__;
    const mapImage = "__MAP_IMAGE__";
    const imageSize = { width: __IMAGE_WIDTH__, height: __IMAGE_HEIGHT__ };
    const mapProfile = __MAP_PROFILE_JSON__;
    const projection = mapProfile.projection;

    const component = { width: 804, height: 880 };
    const views = {
      overview: {
        x: -0.0164 * component.width,
        y: 0,
        w: 1.0531 * component.width,
        h: component.height
      },
      zoom: {
        x: -2.0237 * component.width,
        y: -2.3232 * component.height,
        w: 4.4366 * component.width,
        h: 4.2129 * component.height
      }
    };

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function project(lon, lat) {
      const xRatio = (lon - projection.lonMin) / (projection.lonMax - projection.lonMin);
      const yRatio = (projection.latMax - lat) / (projection.latMax - projection.latMin);
      const x = projection.imageLeft + xRatio * (projection.imageRight - projection.imageLeft);
      const y = projection.imageTop + yRatio * (projection.imageBottom - projection.imageTop);
      return [clamp(x, 8, imageSize.width - 8), clamp(y, 8, imageSize.height - 8)];
    }

    const points = deployments.map(d => {
      const [x, y] = project(d.lon, d.lat);
      return { ...d, x, y };
    });

    function toStage(point, view) {
      return {
        x: view.x + (point.x / imageSize.width) * view.w,
        y: view.y + (point.y / imageSize.height) * view.h
      };
    }

    function buildClusters() {
      const cellSize = 52;
      const cells = new Map();
      for (const point of points) {
        const key = `${Math.floor(point.x / cellSize)}:${Math.floor(point.y / cellSize)}`;
        const cell = cells.get(key) || { count: 0, x: 0, y: 0 };
        cell.count += 1;
        cell.x += point.x;
        cell.y += point.y;
        cells.set(key, cell);
      }
      return [...cells.values()]
        .filter(cell => cell.count >= 5)
        .map(cell => ({
          x: cell.x / cell.count,
          y: cell.y / cell.count,
          count: cell.count,
          radius: clamp(9 + Math.sqrt(cell.count) * 4.8, 15, 44)
        }));
    }

    const clusters = buildClusters();

    function drawClusterLayer(ctx, view) {
      const scale = Math.sqrt(view.w / imageSize.width);
      ctx.save();
      ctx.setLineDash([3, 4]);
      for (const cluster of clusters) {
        const p = toStage(cluster, view);
        const radius = cluster.radius * scale;
        const outside =
          p.x + radius < -20 ||
          p.y + radius < -20 ||
          p.x - radius > component.width + 20 ||
          p.y - radius > component.height + 20;
        if (outside) continue;
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(0, 167, 81, 0.15)";
        ctx.fill();
        ctx.lineWidth = Math.max(1.05, 1.15 * Math.min(scale, 1.9));
        ctx.strokeStyle = "rgba(0, 124, 60, 0.68)";
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawPointLayer(ctx, view, variant) {
      const zoomed = variant === "zoom";
      const radius = zoomed ? 4.2 : 1.9;
      const stem = zoomed ? 9 : 4.5;
      ctx.save();
      ctx.lineCap = "round";
      for (const point of points) {
        const p = toStage(point, view);
        if (p.x < -14 || p.y < -18 || p.x > component.width + 14 || p.y > component.height + 14) continue;
        ctx.beginPath();
        ctx.moveTo(p.x + radius * 0.55, p.y + radius * 0.9);
        ctx.lineTo(p.x + radius * 1.1, p.y + stem);
        ctx.lineWidth = zoomed ? 1.25 : 0.85;
        ctx.strokeStyle = "rgba(52, 81, 104, .88)";
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = "#00a751";
        ctx.fill();
        ctx.lineWidth = zoomed ? 1.35 : 0.75;
        ctx.strokeStyle = "#345168";
        ctx.stroke();
      }
      ctx.restore();
    }

    function renderCanvas(canvas, variant, image) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = component.width * dpr;
      canvas.height = component.height * dpr;
      canvas.style.width = `${component.width}px`;
      canvas.style.height = `${component.height}px`;

      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, component.width, component.height);
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, component.width, component.height);

      const view = views[variant];
      ctx.drawImage(image, view.x, view.y, view.w, view.h);
      drawClusterLayer(ctx, view);
      drawPointLayer(ctx, view, variant);
    }

    const image = new Image();
    image.onload = () => {
      document.querySelectorAll("[data-map-canvas]").forEach(canvas => {
        renderCanvas(canvas, canvas.dataset.mapCanvas, image);
      });
    };
    image.src = mapImage;

    window.__LSN_FIGMA_MAP_PROOF__ = {
      generatedAt,
      sourceCsv,
      sourceMap,
      figmaNode: "1715:3527",
      variants: ["overview", "zoom"],
      rows: deployments.length,
      plotted: points.length,
      clusters: clusters.length,
      renderer: "figma-map-zoom-in-canvas",
      mapProfile,
      component,
      views
    };
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
