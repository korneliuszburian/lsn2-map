"""Regression checks for the artwork-based client map renderer."""

from __future__ import annotations

from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point

from src import render_lsn_final_map as final_map
from src import render_lsn_map_options as artwork_map


def test_artwork_renderer_uses_client_svg_as_default_basemap() -> None:
    assert artwork_map.DEFAULT_MAP_IMAGE == "data/assets/client-map/new-na-map.svg"
    assert artwork_map.DEFAULT_PIN_IMAGE == "data/assets/client-map/pin-na-map.svg"

    width, height = artwork_map.read_svg_size(Path(artwork_map.DEFAULT_MAP_IMAGE))

    assert round(width, 2) == 816
    assert round(height, 2) == 838.86


def test_artwork_renderer_does_not_draw_manual_map_geometry_over_client_svg() -> None:
    html = artwork_map.HTML_TEMPLATE

    assert "L.imageOverlay(mapImage, bounds" in html
    assert "visualContract: \"branded_overview_display_placement_not_gis\"" in html
    assert "drawMapAdditions" not in html
    assert "mapAdditions" not in html
    assert "ctx.ellipse(x, y, rx, ry" not in html


def test_makefile_exposes_single_client_facing_final_map_target() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "map-final:" in makefile
    assert "$(PYTHON) -m src.render_lsn_final_map" in makefile
    assert "--basemap-output $(OUTPUT_DIR)/lsn-north-america-final.svg" in makefile
    assert "--short-basemap-output $(OUTPUT_DIR)/lsn-north-america-final-short.svg" in makefile
    assert "--pin-image $(PIN_IMAGE)" in makefile
    assert "--pin-image $(PIN_IMAGE)" in makefile
    assert "--output $(OUTPUT_DIR)/lsn-map-final.html" in makefile
    assert "map-d3:" not in makefile
    assert "map-options:" not in makefile
    assert "map-figma:" not in makefile
    assert "map-geographic:" not in makefile


def test_final_renderer_keeps_required_map_review_behaviour() -> None:
    html = final_map.HTML_TEMPLATE

    assert 'id="hotZonesToggle"' in html
    assert 'id="pinsToggle"' in html
    assert 'id="pointsToggle"' in html
    assert 'data-mode="flags"' not in html
    assert "drawHotZones" in html
    assert "HOT_ZONES_FADE_START_SCALE" in html
    assert "HOT_ZONES_FADE_END_SCALE" in html
    assert "buildScreenHotZones" in html
    assert "startPinReveal" in html
    assert "PIN_ANIMATION_DURATION" in html
    assert "d3.zoom()" in html
    assert "on(\"zoom\", handleZoom)" in html


def test_final_renderer_keeps_full_map_default_and_short_frame_as_variation() -> None:
    html = final_map.HTML_TEMPLATE

    assert 'id="fullFrameBtn"' in html
    assert 'id="shortFrameBtn"' in html
    assert 'let activeFrame = "full";' in html
    assert "const mapFrames = {" in html
    assert "const shortMapImage = \"__SHORT_MAP_IMAGE__\";" in html
    assert "const shortMapNoLakesImage = \"__SHORT_MAP_NO_LAKES_IMAGE__\";" in html
    assert "const shortMainDeployments = __SHORT_MAIN_DEPLOYMENTS_JSON__;" in html
    assert 'mapVariant: "generated_full_basemap"' in html
    assert "basemapSvg: shortBasemapSvg" in html
    assert "images: { lakes: shortMapImage, noLakes: shortMapNoLakesImage }" in html
    assert "mainDeployments: shortMainDeployments" in html
    assert "const frameProfiles = {" in html
    assert 'document.body.dataset.mapFrame = frameId;' in html
    assert 'mapVariant: "generated_clipped_basemap"' in html
    assert "function activeStageRect()" in html
    assert "function activateFrameData(frameId)" in html
    assert "mapVariant: frame.mapVariant" in html
    assert "mapImageEl.src = frame.images[activeWater] || frame.images.lakes;" in html
    assert 'let activeWater = "lakes";' in html
    assert 'id="lakesBtn"' in html
    assert 'id="noLakesBtn"' in html
    assert 'document.getElementById("noLakesBtn").addEventListener("click", () => setWater("noLakes"));' in html
    assert "allPoints = mainPoints.concat(hawaiiPoints);" in html
    assert "excludedPoints: Math.max(0, fullPointCount - framePointCount)" in html
    assert "activeFrame: frameProof()" in html
    assert "resizeAll();" in html
    assert "document.getElementById(\"shortFrameBtn\").addEventListener(\"click\", () => setFrame(\"short\"));" in html


def test_final_short_map_is_separate_generated_extent_not_viewport_crop() -> None:
    source = Path("src/render_lsn_final_map.py").read_text(encoding="utf-8")

    assert "SHORT_MAP_COMPONENT_MAX_LAT = 66.5" in source
    assert "SHORT_MAP_POINT_EXTENT_LON_LAT = (-170.0, 9.0, -50.0, SHORT_MAP_COMPONENT_MAX_LAT)" in source
    assert "SHORT_MAP_MAX_SNAP_DISTANCE_M = 100_000" in source
    assert "DEFAULT_SHORT_BASEMAP_OUTPUT" in source
    assert "short_projected_admin0 = project_boundaries" in source
    assert "short_viewport = build_viewport" in source
    assert "short_basemap_svg = render_basemap_svg" in source
    assert "projected_short_deployments = project_deployments" in source
    assert "deployment_in_lon_lat_extent(d, SHORT_MAP_POINT_EXTENT_LON_LAT)" in source
    assert "filter_deployments_for_short_basemap(" in source
    assert "was_on_full_basemap and not remains_on_short_basemap" in source
    assert "too_far_to_snap = point.distance(short_union) > SHORT_MAP_MAX_SNAP_DISTANCE_M" in source
    assert "component_max_lat=SHORT_MAP_COMPONENT_MAX_LAT" in source
    assert "def filter_components_north_of" in source
    assert "geom.representative_point().y <= max_lat" in source
    assert "source_geom = filter_components_north_of(geom, component_max_lat)" in source
    assert "geom.intersection(geographic_clip)" not in source
    assert 'body[data-map-frame="short"] #stage' not in source


def test_final_hot_zones_use_canvas_safe_green_style_and_bounded_radius() -> None:
    html = final_map.HTML_TEMPLATE

    assert 'const HOTZONE_FILL = "rgba(0, 167, 81, 0.23)";' in html
    assert 'const HOTZONE_STROKE = "rgba(0, 127, 61, 0.62)";' in html
    assert 'const HOTZONE_MAX_RADIUS = 72;' in html
    assert 'const HOTZONE_SCALE = 5.2;' in html
    assert 'const HOTZONE_FILL = "var(' not in html
    assert 'const HOTZONE_STROKE = "var(' not in html


def test_final_renderer_does_not_draw_manual_water_ovals() -> None:
    basemap = final_map.render_basemap_svg(
        [],
        [],
        [],
        {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1, "scale": 1, "offset_x": 0, "offset_y": 0},
        final_map.GeometryCollection(),
        None,
    )

    assert "water-features" not in final_map.HTML_TEMPLATE
    assert "<ellipse" not in basemap


def test_final_renderer_includes_caribbean_basemap_islands() -> None:
    assert {"CU", "PR", "HT", "DO", "JM", "BS"} <= set(final_map.BASEMAP_COUNTRIES)
    assert set(final_map.DATA_COUNTRIES) == {"US", "CA", "MX"}
    assert "10m_cultural/ne_10m_admin_1_states_provinces.zip" in final_map.SOURCES["admin1"]


def test_final_renderer_draws_explicit_lake_layer() -> None:
    source = Path("src/render_lsn_final_map.py").read_text(encoding="utf-8")

    assert "10m_physical/ne_10m_lakes.zip" in final_map.SOURCES["lakes"]
    assert 'class="water"' in source
    assert '<g id="water">' in source
    assert "filter_visible_lakes(" in source


def test_final_projected_extent_samples_edges_so_southern_mexico_is_not_clipped() -> None:
    transformer = Transformer.from_crs("EPSG:4326", final_map.PROJECTION, always_xy=True)
    extent = final_map.projected_extent_box(transformer, *final_map.MAIN_VIEWPORT_EXTENT_LON_LAT)

    oaxaca = Point(*transformer.transform(-96.99, 16.8))
    mexico_city = Point(*transformer.transform(-99.27, 19.67))
    yucatan = Point(*transformer.transform(-88.0, 18.0))

    assert extent.contains(oaxaca)
    assert extent.contains(mexico_city)
    assert extent.contains(yucatan)


def test_final_hot_zones_use_crs_simple_y_axis_and_do_not_force_empty_hawaii_inset() -> None:
    html = final_map.HTML_TEMPLATE

    assert "buildHotZones(points, distancePx, mapWidth, mapHeight)" in html
    assert "function buildScreenHotZones()" in html
    assert "const clusters = this.buildScreenHotZones ? this.buildScreenHotZones() : buildScreenHotZones();" in html
    assert "hawaiiPoints" in html
    assert "allPoints = mainPoints.concat(hawaiiPoints);" in html
    assert "#hawaiiInset" not in html
    assert "paddingBottomRight: [window.innerWidth >= 900 ? 420 : 220, 20]" not in html
    assert "requestDraw()" in html


def test_final_hawaii_is_relocated_inside_single_svg_not_separate_html_map() -> None:
    main_svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect/><g id="countries"></g></svg>'
    hawaii_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"><rect/>'
        '<g id="countries"><path class="country" d="M0,0Z"/></g></svg>'
    )
    combined = final_map.inject_hawaii_display_inset(main_svg, hawaii_svg)
    point = final_map.relocate_hawaii_deployments([{"x": 10, "y": 20, "rawX": 11, "rawY": 21}])[0]

    assert 'id="hawaii-display-inset"' in combined
    assert f"translate({final_map.HAWAII_DISPLAY_X} {final_map.HAWAII_DISPLAY_Y})" in combined
    assert f"scale({final_map.HAWAII_DISPLAY_SCALE})" in combined
    assert "displayRelocated" in point
    assert point["x"] == round(final_map.HAWAII_DISPLAY_X + 10 * final_map.HAWAII_DISPLAY_SCALE, 3)


def test_final_uses_d3_single_transform_instead_of_leaflet_overlay_animation() -> None:
    html = final_map.HTML_TEMPLATE

    assert "leaflet" not in html.lower()
    assert "L.map" not in html
    assert "requestReset()" not in html
    assert "applyTransform()" in html
    assert "transform.applyX(point.x)" in html
    assert "transform.applyY(point.y)" in html


def test_final_hot_zones_recluster_responsively_on_mobile_zoom_and_resize() -> None:
    html = final_map.HTML_TEMPLATE

    assert "const cell = (HOTZONE_SCREEN_CELL * mobileFactor) / currentScale();" in html
    assert "const minClusterCount = viewport.width < 760 || relativeZoom() >= 2.2 ? 2 : HOTZONE_MIN_CLUSTER_COUNT;" in html
    assert "ctx.translate(transform.x, transform.y);" in html
    assert "ctx.scale(transform.k, transform.k);" in html
    assert "const radius = screenRadius / currentScale();" in html
    assert "ctx.lineWidth = 1.15 / currentScale();" in html
    assert "window.visualViewport.addEventListener(\"resize\", handleViewportChange);" in html
    assert "window.addEventListener(\"orientationchange\", handleViewportChange);" in html
    assert ".touchable(() => true)" in html


def test_final_basemap_uses_thinner_borders_for_zoomed_review() -> None:
    source = Path("src/render_lsn_final_map.py").read_text(encoding="utf-8")

    assert 'stroke-width="0.75"' in source
    assert 'stroke-width="0.55"' in source
    assert 'stroke-width="1.3"' not in source
    assert 'stroke-width="1.1"' not in source
