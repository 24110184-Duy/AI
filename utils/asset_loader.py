# utils/asset_loader.py

import os
from pathlib import Path
import re

import pygame

from config import (
    ASSET_PATHS,
    ASSET_ROOT,
    TILE_ASSET_KEYS,
    TILE_SIZE,
)


FOOTPRINT_PATTERN = re.compile(r"_(\d)x(\d)(?:_|$)")


class AssetLoader:
    """
    Asset pipeline:
    - Exact config keys still work: road.png -> "road".
    - Extra PNG files are auto-scanned from assets/.
    - Variant prefixes are grouped: building_1_a.png belongs to building_1.
    - Footprint suffixes are understood: building_4_3x2.png fits a 3x2 lot.
    """

    def __init__(self):
        self.images = {}
        self.original_images = {}
        self.image_paths = {}
        self.image_footprints = {}
        self.variant_keys = {}
        self.reload()

    def reload(self):
        self.images = {}
        self.original_images = {}
        self.image_paths = {}
        self.image_footprints = {}
        self.variant_keys = {}
        self._load_configured_images()
        self._scan_png_assets()
        self._build_variant_groups()

    def _load_configured_images(self):
        for key, path in ASSET_PATHS.items():
            self._load_image_key(key, path)

    def _scan_png_assets(self):
        root = Path(ASSET_ROOT)
        if not root.exists():
            return
        for path in root.rglob("*.png"):
            key = path.stem
            if key not in self.original_images:
                self._load_image_key(key, str(path))

    def _load_image_key(self, key, path):
        self.image_paths[key] = path
        self.image_footprints[key] = self._parse_footprint(key)
        if not os.path.exists(path):
            self.original_images.setdefault(key, None)
            self.images.setdefault(key, None)
            return
        try:
            image = pygame.image.load(path).convert_alpha()
            self.original_images[key] = image
            if self._should_scale_to_tile(key, path):
                self.images[key] = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            else:
                self.images[key] = image
        except pygame.error:
            self.original_images[key] = None
            self.images[key] = None

    def _parse_footprint(self, key):
        match = FOOTPRINT_PATTERN.search(key)
        if not match:
            return (1, 1)
        return int(match.group(1)), int(match.group(2))

    def _should_scale_to_tile(self, key, path):
        if key in {"start_bg", "panel_bg"}:
            return False
        if self._parse_footprint(key) != (1, 1):
            return False
        parts = Path(path).parts
        return "ui" not in parts

    def _build_variant_groups(self):
        bases = sorted(TILE_ASSET_KEYS, key=len, reverse=True)
        for key, image in self.original_images.items():
            if image is None:
                continue
            base = self._match_base_key(key, bases)
            self.variant_keys.setdefault(base, []).append(key)
        for key in self.variant_keys:
            self.variant_keys[key].sort()

    def _match_base_key(self, key, bases):
        for base in bases:
            if key == base or key.startswith(base + "_"):
                return base
        return key

    def get(self, key):
        return self.images.get(key)

    def get_for_footprint(self, key, footprint):
        image = self.original_images.get(key)
        if image is None:
            return None
        width, height = footprint
        target_size = (max(1, width) * TILE_SIZE, max(1, height) * TILE_SIZE)
        if image.get_size() == target_size:
            return image
        return pygame.transform.scale(image, target_size)

    def get_path(self, key):
        return self.image_paths.get(key, "")

    def choose_asset_key(self, base_key, rng=None, footprint=None):
        keys = self.variant_keys.get(base_key, [])
        if not keys:
            return base_key
        if footprint:
            matching = [key for key in keys if self.image_footprints.get(key, (1, 1)) == footprint]
            if matching:
                keys = matching
        if rng:
            return rng.choice(keys)
        return keys[0]
