# Cropix

A QGIS plugin for monitoring crop health using free Sentinel-2 satellite imagery.

---

I built this because I kept running into the same problem — you want to know how your fields are doing, but the tools that actually work (Google Earth Engine, commercial platforms) either have a steep learning curve or cost money. Cropix tries to fix that. You draw a polygon around your farm in QGIS, pick a date range, and it handles the rest.

No Google Earth Engine. No paid APIs. No command line. Just QGIS.

---

## What it does

- Downloads Sentinel-2 imagery for your farm boundary only — not the whole scene
- Calculates NDVI, NDWI, and EVI
- Loads the results as colored raster layers directly in QGIS
- Generates an HTML report with statistics and spatial maps

---

## Requirements

- QGIS 3.16 or newer
- A free Copernicus account with a Sentinel Hub OAuth client

That's it. No Python packages to install — everything runs on what QGIS already ships with.

---

## Getting a Copernicus account

1. Sign up at [dataspace.copernicus.eu](https://dataspace.copernicus.eu) — it's free
2. Go to [shapps.dataspace.copernicus.eu](https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings)
3. Navigate to **OAuth Clients** and create a new client
4. Copy the **Client ID** and **Client Secret** — you'll need these in Cropix settings

The free tier gives you enough quota for regular farm monitoring use.

---

## How to use it

1. Open QGIS and load or draw a polygon layer for your farm
2. Click the Cropix icon in the toolbar (or go to **Plugins → Cropix**)
3. Open **Settings** and paste your Client ID and Client Secret
4. Select your farm layer, set the date range, choose which indices to calculate
5. Hit **Start Analysis**

The plugin downloads only the pixels that cover your farm — so even with a slow connection it stays manageable. When it's done, it opens an HTML report in your browser automatically.

---

## The indices

**NDVI** (Normalized Difference Vegetation Index) is the standard measure of vegetation health. Values above 0.5 generally mean the crop is doing well. Below 0.2 usually means stress, sparse cover, or bare soil.

**NDWI** (Normalized Difference Water Index) tells you about water content in the vegetation. Negative values point toward water stress, which is often the first sign of trouble before you can see it on the ground.

**EVI** (Enhanced Vegetation Index) is similar to NDVI but handles dense canopy and atmospheric interference better. Useful when NDVI is saturating in very green areas.

---

## Known limitations

- Sentinel-2 has a revisit time of around 5 days, so very short date ranges might return no imagery
- Cloud cover can block the view — the plugin picks the least cloudy scene in your date range, but sometimes there's no clean image available
- Very small farm polygons (under ~1 hectare) might produce noisy results due to the 10m pixel resolution of Sentinel-2

---

## What's coming

- Multi-date time series (currently shows only the most recent scene)
- Export options for the report
- Additional indices (SAVI, NDRE)

---

## Feedback

If something's broken or you have an idea, open an issue on GitHub. I check it regularly.

---

*Data: Copernicus Sentinel-2, European Space Agency. Free and open access.*
