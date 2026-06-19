# Map Visualization — 2nd Opinion Prompt

You are a senior frontend engineer and data visualization specialist. Generate a single self-contained HTML file that visualizes generator deployment data across North America on an interactive map.

## Data

You have ~1200 deployment records with these fields:

```
deployment_id, client_id, client_name, country_code (US/CA/MX),
postal_code_norm, latitude, longitude, generator_count (1-5),
generator_model (GX-250, GX-500, Hybrid-X),
install_status (Deployed, Service Due, Planned, Decommissioned),
install_date, service_region, account_manager
```

The data is in `data/output/clients_geocoded.csv` and `data/output/clients.geojson`.

## Requirements

1. **Single HTML file** — no build step, no npm, no bundler. All JS/CSS inline or from CDN.
2. **Map library**: Use MapLibre GL JS (free, no token needed) or Leaflet with high-quality tiles.
3. **Basemap**: Must show real geography — borders, cities, terrain. NOT a flat dark void.
4. **Scope**: North America (zoom to fit US + Canada + Mexico). Rest of world visible but secondary.
5. **Markers**:
   - One point per deployment, colored by `install_status`
   - Size proportional to `generator_count`
   - Click/hover shows rich tooltip with all fields
   - Must handle 1200 points smoothly (no lag)
6. **Layers** (toggleable):
   - Points layer (individual markers)
   - Heatmap layer (density)
   - Optional: clustered layer for zoomed-out view
7. **Dashboard panel**: Stats summary (total deployments, total generators, by status, by country, by model). Modern glass-morphism or card style.
8. **Visual quality**: Must look like a 2026 production dashboard — not a tutorial demo. Think Vercel, Stripe, Linear aesthetic. Clean typography, subtle animations, professional color palette.
9. **Responsive**: Must work on 1920x1080 and 1440x900.

## Color scheme

```
Deployed:       #10b981 (emerald)
Service Due:    #f59e0b (amber)
Planned:        #6366f1 (indigo)
Decommissioned: #ef4444 (red)
```

## Output

Produce the complete HTML file. Save it to `data/output/map.html`. It must open directly in a browser with no server required (all assets from CDN).

## Data loading

Since this is a single HTML file, embed the data as a JS variable. Read the CSV/GeoJSON, convert to a compact JSON array, and embed it in a `<script>` tag. Example:

```html
<script>
const deployments = [
  {id:"DEP-0001",name:"Backup Industrial Co 0001",cc:"US",zip:"10001",lat:40.8677,lon:-74.3962,count:1,model:"GX-500",status:"Deployed",region:"Northeast",manager:"Marek N."},
  ...
];
</script>
```

A Python helper script will generate this. You just design the HTML/JS/CSS.

## Tile sources (pick one, no API key needed)

- `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` (CartoDB Dark Matter — vector tiles, looks great)
- `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json` (CartoDB Positron — light, clean)
- `https://demotiles.maplibre.org/style.json` (MapLibre demo — simple but works)
- OpenStreetMap raster tiles: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (always works, no key)

## Anti-patterns to avoid

- Don't use folium — it generates bloated, ugly output
- Don't use default Leaflet blue markers
- Don't use a flat dark background with no geography
- Don't make it look like a Jupyter notebook output
- Don't add unnecessary 3D effects that hurt readability
- Don't use emoji in the UI

## Inspiration

Think: dark mode dashboard, subtle gradients, crisp typography, glass panels, smooth transitions. The kind of map you'd see on a startup's investor deck or a SOC dashboard.
