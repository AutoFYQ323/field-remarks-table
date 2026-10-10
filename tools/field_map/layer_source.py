# -*- coding: utf-8 -*-
from ...i18n import tr
"""Load vector files including KML/KMZ sublayers."""

import os
import tempfile
import zipfile

from qgis.core import (
    QgsMapLayerType,
    QgsProject,
    QgsProviderRegistry,
    QgsVectorLayer,
)

VECTOR_OPEN_FILTER = (
    tr('矢量文件 (*.kml *.kmz *.shp *.gpkg *.geojson *.json *.gpx *.dxf *.tab);;KML/KMZ (*.kml *.kmz);;GeoPackage (*.gpkg);;Shapefile (*.shp);;GeoJSON (*.geojson *.json);;所有文件 (*.*)')
)

_TEMP_KMZ_DIRS = []


def _normalize_path(path):
    return os.path.normpath(path)


def _posix_path(path):
    return _normalize_path(path).replace("\\", "/")


def _unique(items):
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _kmz_kml_members(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            return [name for name in archive.namelist() if name.lower().endswith(".kml")]
    except Exception:
        return []


def _candidate_uris(path):
    path = _normalize_path(path)
    posix = _posix_path(path)
    uris = [path, posix]

    if path.lower().endswith(".kmz"):
        uris.extend([
            "/vsizip/" + posix,
            "/vsizip/" + posix + "/",
        ])
        members = _kmz_kml_members(path)
        members.sort(key=lambda name: (0 if os.path.basename(name).lower() == "doc.kml" else 1, name))
        for member in members:
            uris.append("/vsizip/{}/{}".format(posix, member))
    return _unique(uris)


def _extract_kmz_kmls(path):
    members = _kmz_kml_members(path)
    if not members:
        return []

    members.sort(key=lambda name: (0 if os.path.basename(name).lower() == "doc.kml" else 1, name))
    tmpdir = tempfile.mkdtemp(prefix="coty_kmz_")
    _TEMP_KMZ_DIRS.append(tmpdir)
    extracted = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for name in members:
                archive.extract(name, tmpdir)
                extracted.append(os.path.join(tmpdir, name.replace("/", os.sep)))
    except Exception:
        return []
    return extracted


def _is_vector_sublayer(sublayer):
    try:
        return sublayer.type() == QgsMapLayerType.VectorLayer
    except Exception:
        return True


def _sublayer_key(sublayer):
    name = ""
    try:
        name = (sublayer.name() or "").strip().lower()
    except Exception:
        name = ""
    wkb = ""
    try:
        wkb = str(sublayer.wkbType())
    except Exception:
        pass
    return (name, wkb)


def _dedupe_sublayers(sublayers):
    seen = set()
    result = []
    for sub in sublayers:
        if not _is_vector_sublayer(sub):
            continue
        key = _sublayer_key(sub)
        if not key[0]:
            try:
                key = ((sub.uri() or "").lower(), key[1])
            except Exception:
                key = ("", key[1])
        if not key[0] or key in seen:
            continue
        seen.add(key)
        result.append(sub)
    return result


def _query_one_uri(uri):
    """Query one URI and expand a nested KML entry if needed. Stop at this URI's result."""
    registry = QgsProviderRegistry.instance()
    try:
        sublayers = list(registry.querySublayers(uri) or [])
    except Exception:
        return []

    expanded = []
    for sub in sublayers:
        name = ""
        nested_uri = ""
        try:
            name = sub.name() or ""
            nested_uri = sub.uri() or ""
        except Exception:
            pass
        if nested_uri and (name.lower().endswith(".kml") or nested_uri.lower().endswith(".kml")):
            try:
                nested = list(registry.querySublayers(nested_uri) or [])
                if nested:
                    expanded.extend(nested)
                    continue
            except Exception:
                pass
        expanded.append(sub)
    return _dedupe_sublayers(expanded)


def _valid_layer(uri, display_name):
    layer = QgsVectorLayer(uri, display_name, "ogr")
    return layer if layer.isValid() else None


def query_file_sublayers(path):
    """Return unique vector sublayers. Tries each open method once, stops at first success."""
    path = _normalize_path(path)
    if not os.path.isfile(path):
        return []

    for uri in _candidate_uris(path):
        found = _query_one_uri(uri)
        if found:
            return found

    if path.lower().endswith(".kmz"):
        for extracted in _extract_kmz_kmls(path):
            found = _query_one_uri(extracted)
            if found:
                return found

    display = os.path.splitext(os.path.basename(path))[0]
    for uri in _candidate_uris(path):
        if _valid_layer(uri, display):
            return [uri]
    return []


def sublayer_label(sublayer, index):
    if isinstance(sublayer, str):
        name = os.path.basename(sublayer)
        return name or tr("图层 {}").format(index + 1)

    name = sublayer.name() if sublayer.name() else tr("图层 {}").format(index + 1)
    description = ""
    try:
        description = sublayer.description()
    except Exception:
        description = ""

    if description and description != name:
        return "{} ({})".format(name, description)
    return name


def sublayer_uri(sublayer, path):
    if isinstance(sublayer, str):
        return sublayer

    try:
        uri = sublayer.uri()
        if uri:
            return uri
    except Exception:
        pass

    name = ""
    try:
        name = sublayer.name() if sublayer.name() else ""
    except Exception:
        name = ""

    for base in _candidate_uris(path):
        if name:
            return "{}|layername={}".format(base, name)
        return base
    return _normalize_path(path)


def load_vector_layer(path, sublayer=None, layer_name=None):
    """
    Load a vector layer from file.

    sublayer: QgsProviderSublayerDetails, URI string, or None
    Returns (QgsVectorLayer or None, error_message)
    """
    path = _normalize_path(path)
    if not os.path.isfile(path) and not str(path).startswith("/vsizip/"):
        if not (sublayer and isinstance(sublayer, str) and os.path.isfile(sublayer)):
            if not (sublayer and hasattr(sublayer, "uri")):
                return None, tr("文件不存在：{}").format(path)

    display_name = layer_name or (
        sublayer_label(sublayer, 0) if sublayer is not None
        else os.path.splitext(os.path.basename(path))[0]
    )

    uris = []
    if sublayer is not None:
        uris.append(sublayer_uri(sublayer, path))
    uris.extend(_candidate_uris(path))

    last_error = ""
    for uri in _unique(uris):
        layer = _valid_layer(uri, display_name)
        if layer:
            return layer, ""
        last_error = uri

    if path.lower().endswith(".kmz"):
        for extracted in _extract_kmz_kmls(path):
            layer = _valid_layer(extracted, display_name)
            if layer:
                return layer, ""
            last_error = extracted

    return None, tr("无法读取图层「{}」。已尝试 KMZ/KML 直接打开、/vsizip 和解压。最后尝试：{}").format(
        display_name, last_error
    )


def add_layer_to_project(layer, group_name="字段映射"):
    """Add layer to project under a named group."""
    project = QgsProject.instance()
    root = project.layerTreeRoot()

    group = root.findGroup(group_name)
    if group is None:
        group = root.insertGroup(0, group_name)

    project.addMapLayer(layer, False)
    group.addLayer(layer)
    return layer
