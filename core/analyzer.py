import os
import base64
import tempfile
import numpy as np
from datetime import datetime
from qgis.core import (
    QgsRasterLayer, QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)
from qgis.PyQt.QtCore import QThread, pyqtSignal, QObject


class AnalyzerWorker(QObject):
    """Runs in a separate thread — keeps QGIS responsive."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, layer, date_start, date_end, indices,
                 client_id, client_secret, output_dir):
        super().__init__()
        self.layer = layer
        self.date_start = date_start
        self.date_end = date_end
        self.indices = indices
        self.client_id = client_id
        self.client_secret = client_secret
        self.output_dir = output_dir

    def run(self):
        try:
            self.progress.emit(10, "Computing farm boundary...")
            bbox = self._get_bbox_wgs84()

            self.progress.emit(25, "Downloading Sentinel-2 imagery...")
            image_paths = self._download_sentinel(bbox)

            self.progress.emit(55, "Calculating vegetation indices...")
            index_results = self._calculate_indices(image_paths)

            self.progress.emit(82, "Generating PNG thumbnails...")
            png_b64 = self._export_png_b64(index_results)

            self.progress.emit(90, "Preparing report data...")
            results = self._prepare_results(bbox, index_results, png_b64)

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))

    def _get_bbox_wgs84(self):
        extent = self.layer.extent()
        crs_src = self.layer.crs()
        crs_dst = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(
            crs_src, crs_dst, QgsProject.instance()
        )
        extent_wgs = transform.transformBoundingBox(extent)
        return {
            "xmin": round(extent_wgs.xMinimum(), 6),
            "ymin": round(extent_wgs.yMinimum(), 6),
            "xmax": round(extent_wgs.xMaximum(), 6),
            "ymax": round(extent_wgs.yMaximum(), 6),
        }

    def _download_sentinel(self, bbox):
        from .sentinel_downloader import SentinelDownloader
        downloader = SentinelDownloader(
            bbox=bbox,
            date_start=self.date_start,
            date_end=self.date_end,
            output_dir=self.output_dir,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        return downloader.download()

    def _calculate_indices(self, image_paths):
        try:
            import rasterio
        except ImportError:
            raise Exception(
                "rasterio is not installed.\n"
                "Run: pip install rasterio --break-system-packages"
            )

        results = {}

        for date_str, bands in image_paths.items():
            results[date_str] = {}

            with rasterio.open(bands["B04"]) as src:
                red = src.read(1).astype(float)
                transform = src.transform
                height, width = src.height, src.width

            with rasterio.open(bands["B08"]) as src:
                nir = src.read(1).astype(float)

            with rasterio.open(bands["B03"]) as src:
                green = src.read(1).astype(float)

            np.seterr(divide="ignore", invalid="ignore")

            if "NDVI" in self.indices:
                ndvi = np.where(
                    (nir + red) == 0, np.nan,
                    (nir - red) / (nir + red)
                )
                path = os.path.join(self.output_dir, f"NDVI_{date_str}.tif")
                self._save_raster(ndvi, transform, height, width, path)
                results[date_str]["NDVI"] = {
                    "path": path,
                    "array": ndvi,
                    "stats": self._calc_stats(ndvi),
                }

            if "NDWI" in self.indices:
                ndwi = np.where(
                    (green + nir) == 0, np.nan,
                    (green - nir) / (green + nir)
                )
                path = os.path.join(self.output_dir, f"NDWI_{date_str}.tif")
                self._save_raster(ndwi, transform, height, width, path)
                results[date_str]["NDWI"] = {
                    "path": path,
                    "array": ndwi,
                    "stats": self._calc_stats(ndwi),
                }

            if "EVI" in self.indices:
                with rasterio.open(bands["B02"]) as src:
                    blue = src.read(1).astype(float)
                denom = nir + 6 * red - 7.5 * blue + 1
                evi = np.where(denom == 0, np.nan, 2.5 * (nir - red) / denom)
                path = os.path.join(self.output_dir, f"EVI_{date_str}.tif")
                self._save_raster(evi, transform, height, width, path)
                results[date_str]["EVI"] = {
                    "path": path,
                    "array": evi,
                    "stats": self._calc_stats(evi),
                }

        return results

    def _save_raster(self, array, transform, height, width, path):
        """
        Save raster using GDAL (bundled with QGIS).
        Avoids rasterio PROJ conflicts completely — works on all platforms.
        """
        from osgeo import gdal, osr

        data = array.astype("float32")
        data[~np.isfinite(data)] = -9999.0

        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, width, height, 1, gdal.GDT_Float32)

        # Affine transform → GDAL geotransform
        ds.SetGeoTransform((
            transform.c,   # x origin (top-left)
            transform.a,   # pixel width
            transform.b,   # x rotation (0 for north-up)
            transform.f,   # y origin (top-left)
            transform.d,   # y rotation (0 for north-up)
            transform.e,   # pixel height (negative)
        ))

        # WGS84 projection via QGIS's GDAL — no external PROJ needed
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        ds.SetProjection(srs.ExportToWkt())

        band = ds.GetRasterBand(1)
        band.WriteArray(data)
        band.SetNoDataValue(-9999.0)
        band.FlushCache()
        ds = None  # Close and flush to disk

    def _export_png_b64(self, index_results):
        """
        Generate colored PNG thumbnails for each index.
        Returns base64-encoded strings for embedding in HTML.
        """
        color_stops = {
            "NDVI": [
                (-1.0, (165,   0,  38)),
                (-0.2, (215,  48,  39)),
                ( 0.0, (244, 109,  67)),
                ( 0.2, (254, 224, 139)),
                ( 0.4, (217, 239, 139)),
                ( 0.6, (102, 189, 100)),
                ( 1.0, ( 26, 152,  80)),
            ],
            "NDWI": [
                (-1.0, (140,  81,  10)),
                ( 0.0, (245, 245, 245)),
                ( 0.3, (116, 173, 209)),
                ( 1.0, ( 49,  54, 149)),
            ],
            "EVI": [
                (-1.0, (215,  48,  39)),
                ( 0.0, (254, 224, 139)),
                ( 0.5, (102, 189, 100)),
                ( 1.0, (  0, 104,  55)),
            ],
        }

        dates = sorted(index_results.keys())
        if not dates:
            return {}

        last_date = dates[-1]
        png_b64 = {}

        for index_name, data in index_results[last_date].items():
            arr = data.get("array")
            if arr is None:
                continue

            stops = color_stops.get(index_name, [])
            if not stops:
                continue

            arr_clipped = np.clip(arr, -1.0, 1.0)
            h, w = arr_clipped.shape
            rgb = np.zeros((h, w, 3), dtype=np.uint8)

            values = [s[0] for s in stops]
            colors = [s[1] for s in stops]

            for ch in range(3):
                channel_stops = [c[ch] for c in colors]
                rgb[:, :, ch] = np.interp(
                    arr_clipped, values, channel_stops
                ).astype(np.uint8)

            # Gray for nodata pixels
            mask = ~np.isfinite(arr)
            rgb[mask] = [200, 200, 200]

            png_path = os.path.join(
                self.output_dir, f"{index_name}_{last_date}.png"
            )

            saved = False
            try:
                from PIL import Image
                Image.fromarray(rgb, mode="RGB").save(png_path)
                saved = True
            except ImportError:
                pass

            if not saved:
                try:
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt
                    plt.imsave(png_path, rgb)
                    plt.close()
                    saved = True
                except Exception:
                    pass

            if not saved:
                continue

            with open(png_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            png_b64[index_name] = b64

        return png_b64

    def _calc_stats(self, array):
        valid = array[np.isfinite(array)]
        if len(valid) == 0:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "std": 0.0}
        return {
            "mean": round(float(np.mean(valid)), 4),
            "min":  round(float(np.min(valid)), 4),
            "max":  round(float(np.max(valid)), 4),
            "std":  round(float(np.std(valid)), 4),
        }

    def _prepare_results(self, bbox, index_results, png_b64):
        clean_results = {}
        for date_str, indices in index_results.items():
            clean_results[date_str] = {}
            for index_name, data in indices.items():
                clean_results[date_str][index_name] = {
                    "path": data["path"],
                    "stats": data["stats"],
                }

        return {
            "farm_name": self.layer.name(),
            "bbox": bbox,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "indices": clean_results,
            "png_b64": png_b64,
            "output_dir": self.output_dir,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }


class CropixAnalyzer:
    """
    Manages the worker thread.
    Keeps QGIS fully responsive during download and processing.
    """

    def __init__(self, layer, date_start, date_end, indices,
                 client_id, client_secret,
                 iface, progress_callback, done_callback, error_callback):
        self.iface = iface
        self.on_progress = progress_callback
        self.on_done = done_callback
        self.on_error = error_callback
        self.output_dir = tempfile.mkdtemp(prefix="cropix_")

        self.thread = QThread()
        self.worker = AnalyzerWorker(
            layer=layer,
            date_start=date_start,
            date_end=date_end,
            indices=indices,
            client_id=client_id,
            client_secret=client_secret,
            output_dir=self.output_dir,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)

    def run(self):
        self.thread.start()

    def _on_done(self, results):
        self._load_layers_to_qgis(results["indices"])
        self.on_done(results)

    def _on_error(self, msg):
        self.on_error(msg)

    def _load_layers_to_qgis(self, index_results):
        from qgis.core import (
            QgsColorRampShader, QgsRasterShader,
            QgsSingleBandPseudoColorRenderer
        )
        from qgis.PyQt.QtGui import QColor

        color_ramps = {
            "NDVI": [
                (-1.0, QColor("#a50026")),
                (-0.2, QColor("#d73027")),
                ( 0.0, QColor("#f46d43")),
                ( 0.2, QColor("#fee08b")),
                ( 0.4, QColor("#d9ef8b")),
                ( 0.6, QColor("#66bd63")),
                ( 1.0, QColor("#1a9850")),
            ],
            "NDWI": [
                (-1.0, QColor("#8c510a")),
                ( 0.0, QColor("#f5f5f5")),
                ( 0.3, QColor("#74add1")),
                ( 1.0, QColor("#313695")),
            ],
            "EVI": [
                (-1.0, QColor("#d73027")),
                ( 0.0, QColor("#fee08b")),
                ( 0.5, QColor("#66bd63")),
                ( 1.0, QColor("#006837")),
            ],
        }

        for date_str, indices in index_results.items():
            for index_name, data in indices.items():
                rl = QgsRasterLayer(
                    data["path"],
                    f"{index_name}  •  {date_str}"
                )

                if not rl.isValid():
                    continue

                crs = QgsCoordinateReferenceSystem("EPSG:4326")
                rl.setCrs(crs)

                ramp = color_ramps.get(index_name, [])
                shader_items = [
                    QgsColorRampShader.ColorRampItem(v, c) for v, c in ramp
                ]
                color_ramp_shader = QgsColorRampShader()
                color_ramp_shader.setColorRampType(
                    QgsColorRampShader.Interpolated
                )
                color_ramp_shader.setColorRampItemList(shader_items)

                raster_shader = QgsRasterShader()
                raster_shader.setRasterShaderFunction(color_ramp_shader)

                renderer = QgsSingleBandPseudoColorRenderer(
                    rl.dataProvider(), 1, raster_shader
                )
                rl.setRenderer(renderer)
                QgsProject.instance().addMapLayer(rl)