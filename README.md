# Snowballing: crop rotation decision support for dryland wheat

NASA Space Apps Challenge 2026 project. A decision-support tool that helps farmers in the
inland Pacific Northwest (eastern Washington) compare crop rotations using NASA Earth
observations, USDA soil data and published Washington State University research.

It supports, not replaces, farmer judgment and local agronomic advice.

## What it does
1. Downloads 45 years of daily NASA POWER weather for a field.
2. Sorts the field into a rainfall zone (low, intermediate, high).
3. Estimates wheat yields for every past year with WSU's published yield equations.
4. Checks candidate rotations against regional rules (fallow, soil pH, erosion, disease).
5. Looks up the field's soil in the USDA soil survey.
6. Scores each rotation on yield, dry-year performance, soil and risk, weighted by the
   farmer's priorities, and shows ranges rather than single forecasts.

## Run it
    python -m venv .venv
    .venv\Scripts\activate        (Windows)   or   source .venv/bin/activate   (Mac/Linux)
    pip install -r requirements.txt
    python server.py

Then open http://localhost:8000

## Files
| File | Role |
|---|---|
| server.py | Web server: serves the page and runs the analysis |
| analysis.py | Everything the page needs for one field, in one call |
| static/ | The web page: index.html, style.css, app.js, and vendor/ (Material Web components, Leaflet map, fonts) |
| power.py | NASA POWER daily weather download, cache and precipitation correction |
| climate.py | Daily weather to one row per crop year (September to August) |
| zones.py | Rainfall zone classification |
| yield_model.py | WSU EM049E wheat yield equations |
| crops.py | Crop facts with sources |
| rules.py | Regional rules and candidate rotations |
| soil.py | USDA soil survey lookup |
| scoring.py | Replays rotations over 45 years and ranks them |
| sites.py | Demo field locations |
| LIMITATIONS.md | Known limitations, measured checks and design choices |

## Data and libraries
- NASA POWER daily meteorology (MERRA-2)
- USDA NRCS soil survey (SSURGO) via Soil Data Access
- WSU Extension EM049E, FS050E; Schillinger 2017; Maaz et al. 2017; and others cited in
  the code and LIMITATIONS.md
- Google Material Web components, Leaflet with OpenStreetMap tiles,
  Space Grotesk and Inter fonts (SIL Open Font License)
