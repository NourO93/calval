"""
Normalized format for representing scenes.
Each scene contains metadata with some fixed fields, and some rasters with fixed band names.
The data in the rasters are fixed point 16bit floats in range 0:1
scene_id and sceneset_id can be either normalized or provider-specific (provider specific
scene_id are useful when using provider-specific storage backend).
"""
import os
import glob
from collections import namedtuple
from functools import total_ordering
import json
import datetime as dt
from calval.utils import cached_property
from calval.raster_utils import hires_tile, TileCache, uncached_get_tile

band_names = ['blue', 'green', 'red', 'nir']
tile_cache = TileCache()

sceneid_params = namedtuple('sceneid_params', ['product', 'satellite', 'tile_id', 'timestamp', 'tag'])
sceneid_params.__new__.__defaults__ = ('0',)  # default tag
scenesetid_params = namedtuple('scenesetid_params', ['satellite', 'tile_id', 'timestamp'])


@total_ordering
class StringableTuple:
    """
    Wrapper for `namedtuple` with converters to/from strings.
    String representation contains str of fields, separated by '_'
    For extra type conversions, override the _tostr/_fromstr methods
    baseclass already has support for timestamps (`datetimes` at minute resolution).
    """
    tuple_type = None  # must override this
    timestamp_fmt = '%Y%m%d%H%M'
    timestamp_fields = {}

    def __init__(self, *args, **kwargs):
        self.params = self.tuple_type(*args, **kwargs)

    @classmethod
    def from_str(cls, s, separator='_'):
        str_tuple = cls.tuple_type(*s.split(separator))
        obj = cls(*(cls._fromstr(getattr(str_tuple, field), field)
                    for field in cls.tuple_type._fields))
        return obj

    def copy_with(self, **kwargs):
        data = self.params._asdict()
        data.update(kwargs)
        return type(self)(**data)

    def __getattr__(self, item):
        "if normal attribute getting fails, try to get from params"
        return getattr(self.params, item)

    def __str__(self):
        return '_'.join(self.str_tuple)

    def __eq__(self, other):
        return self.str_tuple == other.str_tuple

    def __lt__(self, other):
        return self.str_tuple < other.str_tuple

    @property
    def str_tuple(cls):
        return cls.tuple_type(*(cls._tostr(x) for x in cls.params))

    # type converters
    @classmethod
    def _fromstr(cls, s, fieldname):
        if fieldname in cls.timestamp_fields:
            return dt.datetime.strptime(s, cls.timestamp_fmt)
        return s

    @classmethod
    def _tostr(cls, x):
        if hasattr(x, 'strftime'):
            return x.strftime(cls.timestamp_fmt)
        return str(x)


class NormalizedScenesetId(StringableTuple):
    tuple_type = scenesetid_params
    timestamp_fields = {'timestamp'}


class NormalizedSceneId(StringableTuple):
    tuple_type = sceneid_params
    timestamp_fields = {'timestamp'}

    @property
    def sceneset_id(self):
        return NormalizedScenesetId(*(getattr(self, attr) for attr in NormalizedScenesetId.tuple_type._fields))

    def dir_path(self):
        return '/'.join(self.str_tuple)

    def scenepath_prefix(self):
        return '/'.join([self.dir_path(), str(self)])

    def metadata_path(self):
        return self.scenepath_prefix() + '_metadata.json'

    def band_path(self, band):
        return self.scenepath_prefix() + '_{}.tif'.format(band)

    def band_url(self, prefix, band):
        return prefix + self.band_path(band)

    def band_urls(self, prefix, bands=band_names):
        return {band: self.band_url(prefix, band) for band in bands}


class NormalizedScene:
    def __init__(self, metadata, band_urls):
        self.metadata = metadata
        self.band_urls = band_urls

    @property
    def scene_info(self):
        return NormalizedSceneId.from_str(self['scene_id'])

    def __getitem__(self, key):
        return self.metadata[key]

    def band_tile(self, band, tile_coords, zoomlevel=None,
                  get_tile=uncached_get_tile):
        return hires_tile(self.band_urls[band], tile_coords, zoomlevel, get_tile=get_tile)


class FilebasedScene(NormalizedScene):
    def __init__(self, path, band_urls=None):
        """
        Lazy NormalizedScene that is read from files.
        `path` points to the metadata file, or to a directory that contains a single metadata file.
        `band_urls` are either specifed, or assumed to be files in the same directory
        as `path`.
        """
        if band_urls is not None:
            self.band_urls = band_urls

        if os.path.isfile(path):
            self._metadata_path = path
            self._path = os.path.abspath(os.path.dirname(path))
        elif os.path.isdir(path):
            self._path = path
            fnames = glob.glob(os.path.join(path, '*_metadata.json'))
            assert len(fnames) == 1, 'directory should have a single metadata file'
            self._metadata_path = fnames[0]

    @cached_property
    def band_urls(self):
        scene_id_str = self.metadata['scene_id']
        band_urls = {band: os.path.join(self._path, '{}_{}.tif'.format(scene_id_str, band))
                     for band in band_names}
        return band_urls

    @cached_property
    def metadata(self):
        return json.load(open(self._metadata_path))
