import os
import math
import numpy as np
from osgeo import gdal, osr

# ─────────────────────────────────────────────────────────────────────────────
# SentinelDownloader — Zero external dependencies
# Uses only: requests + numpy + osgeo (all bundled with QGIS)
# No sentinelhub, no rasterio, no PROJ conflicts.
# ─────────────────────────────────────────────────────────────────────────────

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
CATALOG_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


class SentinelDownloader:
    """
    Download Sentinel-2 imagery for a farm bounding box.
    Communicates directly with Sentinel Hub Process API via HTTP.
    Requires only packages bundled with QGIS — nothing to install.
    """

    def __init__(self, bbox, date_start, date_end, output_dir,
                 client_id=None, client_secret=None, max_cloud=30):
        self.bbox = bbox
        self.date_start = date_start
        self.date_end = date_end
        self.output_dir = output_dir
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_cloud = int(max_cloud)
        self._token = None

    # ── Authentication ────────────────────────────────────────────────────────

    def _get_token(self):
        """Fetch OAuth2 access token from Copernicus Identity Service."""
        if self._token:
            return self._token

        import requests

        if not self.client_id or not self.client_secret:
            raise Exception(
                "Sentinel Hub credentials are missing.\n"
                "Go to Settings and enter your Client ID and Client Secret."
            )

        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            raise Exception(
                f"Authentication failed (HTTP {resp.status_code}).\n"
                "Please check your Client ID and Secret in Settings.\n\n"
                f"Details: {resp.text[:200]}"
            )

        self._token = resp.json()["access_token"]
        return self._token

    # ── Scene search ──────────────────────────────────────────────────────────

    def _get_real_date(self):
        """
        Query Copernicus STAC catalog for the actual acquisition date
        of the most recent low-cloud scene in the date range.
        Falls back to date_start if the search fails.
        """
        import requests

        try:
            payload = {
                "collections": ["sentinel-2-l2a"],
                "bbox": [
                    self.bbox["xmin"],
                    self.bbox["ymin"],
                    self.bbox["xmax"],
                    self.bbox["ymax"],
                ],
                "datetime": (
                    f"{self.date_start}T00:00:00Z"
                    f"/{self.date_end}T23:59:59Z"
                ),
                "query": {"eo:cloud_cover": {"lte": self.max_cloud}},
                "sortby": [
                    {"field": "properties.datetime", "direction": "desc"}
                ],
                "limit": 1,
            }

            resp = requests.post(CATALOG_URL, json=payload, timeout=20)

            if resp.status_code == 200:
                features = resp.json().get("features", [])
                if features:
                    raw = features[0]["properties"]["datetime"]
                    return raw[:10]  # "2025-08-15"
        except Exception:
            pass

        return self.date_start

    # ── Image size calculation ────────────────────────────────────────────────

    def _calc_size(self, resolution=10, max_px=1024):
        """
        Calculate output pixel dimensions for the bbox at a given resolution.
        Uses degree-to-meter conversion (haversine approximation).
        """
        lat_center = (self.bbox["ymin"] + self.bbox["ymax"]) / 2
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(lat_center))

        width_m  = (self.bbox["xmax"] - self.bbox["xmin"]) * m_per_deg_lon
        height_m = (self.bbox["ymax"] - self.bbox["ymin"]) * m_per_deg_lat

        w = max(1, int(width_m  / resolution))
        h = max(1, int(height_m / resolution))

        if w > max_px or h > max_px:
            scale = max_px / max(w, h)
            w = max(1, int(w * scale))
            h = max(1, int(h * scale))

        return w, h

    # ── GDAL geotransform ─────────────────────────────────────────────────────

    def _make_geotransform(self, width, height):
        """
        Build a GDAL geotransform tuple for the bbox.
        Format: (x_origin, pixel_w, 0, y_origin, 0, -pixel_h)
        """
        pixel_w = (self.bbox["xmax"] - self.bbox["xmin"]) / width
        pixel_h = (self.bbox["ymax"] - self.bbox["ymin"]) / height
        return (
            self.bbox["xmin"],   # x origin (west)
            pixel_w,             # pixel width in degrees
            0.0,                 # x rotation (0 = north-up)
            self.bbox["ymax"],   # y origin (north)
            0.0,                 # y rotation (0 = north-up)
            -pixel_h,            # pixel height (negative = north-up)
        )

    # ── Band download ─────────────────────────────────────────────────────────

    def _download_band(self, band_name, width, height):
        """
        Request a single Sentinel-2 band from Sentinel Hub Process API.
        Returns a 2D float32 numpy array (height × width).
        """
        import requests

        token = self._get_token()

        evalscript = f"""
//VERSION=3
function setup() {{
    return {{
        input: [{{ bands: ["{band_name}"], units: "REFLECTANCE" }}],
        output: {{ bands: 1, sampleType: "FLOAT32" }}
    }};
}}
function evaluatePixel(sample) {{
    return [sample.{band_name}];
}}
"""
        payload = {
            "input": {
                "bounds": {
                    "bbox": [
                        self.bbox["xmin"],
                        self.bbox["ymin"],
                        self.bbox["xmax"],
                        self.bbox["ymax"],
                    ],
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                    },
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": f"{self.date_start}T00:00:00Z",
                                "to":   f"{self.date_end}T23:59:59Z",
                            },
                            "maxCloudCoverage": self.max_cloud,
                            "mosaickingOrder": "leastCC",
                        },
                    }
                ],
            },
            "output": {
                "width":  width,
                "height": height,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {"type": "image/tiff"},
                    }
                ],
            },
            "evalscript": evalscript,
        }

        resp = requests.post(
            PROCESS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "image/tiff",
            },
            timeout=120,
        )

        if resp.status_code != 200:
            raise Exception(
                f"Sentinel Hub API error for band {band_name} "
                f"(HTTP {resp.status_code}):\n{resp.text[:300]}"
            )

        if not resp.content:
            raise Exception(
                f"Empty response for band {band_name}.\n"
                "Try expanding the date range or reducing cloud cover threshold."
            )

        return self._tiff_bytes_to_array(resp.content, band_name)

    def _tiff_bytes_to_array(self, tiff_bytes, band_name):
        """
        Convert raw GeoTIFF bytes to a 2D float32 numpy array
        using GDAL's in-memory virtual filesystem (/vsimem/).
        No temp files, no rasterio needed.
        """
        vsi_path = f"/vsimem/cropix_{band_name}.tif"
        try:
            gdal.FileFromMemBuffer(vsi_path, tiff_bytes)
            ds = gdal.Open(vsi_path)
            if ds is None:
                raise Exception(
                    f"Could not decode TIFF data for band {band_name}."
                )
            arr = ds.GetRasterBand(1).ReadAsArray().astype("float32")
            ds = None
            return arr
        finally:
            gdal.Unlink(vsi_path)

    # ── Save to GeoTIFF ───────────────────────────────────────────────────────

    def _save_band(self, arr, geotransform, path):
        """
        Save a 2D float32 array as a GeoTIFF.
        Uses GDAL (bundled with QGIS) — no PROJ conflicts, cross-platform.
        """
        height, width = arr.shape

        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)
        ds.SetGeoTransform(geotransform)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())

        data = arr.copy()
        data[~np.isfinite(data)] = -9999.0

        b = ds.GetRasterBand(1)
        b.WriteArray(data)
        b.SetNoDataValue(-9999.0)
        b.FlushCache()
        ds = None

    # ── Public entry point ────────────────────────────────────────────────────

    def download(self):
        """
        Download bands B02, B03, B04, B08 for the farm bbox.
        Returns: {date_str: {"B02": path, "B03": path, ...}}
        """
        width, height = self._calc_size(resolution=10, max_px=1024)
        date_str = self._get_real_date()
        geotransform = self._make_geotransform(width, height)

        band_names = ["B02", "B03", "B04", "B08"]
        band_paths = {}

        for band_name in band_names:
            arr = self._download_band(band_name, width, height)
            out_path = os.path.join(
                self.output_dir, f"{band_name}_{date_str}.tif"
            )
            self._save_band(arr, geotransform, out_path)
            band_paths[band_name] = out_path

        return {date_str: band_paths}