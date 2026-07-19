"""Sequential image writer — replaces SHA256 filenames with 1.png, 2.jpg, ...

Usage in main.py::

    raw_writer = FileBasedDataWriter(str(img_dir))
    image_writer = SequentialImageWriter(raw_writer)
    # ... convert ...
    # After conversion:
    markdown = image_writer.patch_markdown(markdown, img_buket_path)
"""

import hashlib
import os
from pathlib import Path


class SequentialImageWriter:
    """Wraps a FileBasedDataWriter to use sequential image names.

    Tracks content hash → sequential name so that identical images
    (same SHA-256 of decoded bytes) share the same file.
    """

    def __init__(self, real_writer):
        self._real = real_writer
        self._counter = 0
        # content_sha256 → (seq_name, path_used_in_first_write)
        self._hash_to_name: dict[str, str] = {}
        # path_used_by_save_base64_image → seq_name
        self._old_to_new: dict[str, str] = {}
        # set of already-written seq paths (for _mineru_written_image_paths)
        self._mineru_written_image_paths: set[str] = set()

    # --- delegate attrs that save_base64_image / _write_image_once expect ---

    @property
    def output_dir(self):
        return self._real.output_dir

    def write(self, relative_path: str, data: bytes) -> None:
        """Write *data* to disk using a sequential name derived from content hash."""
        h = hashlib.sha256(data).hexdigest()

        if h in self._hash_to_name:
            seq_name = self._hash_to_name[h]
        else:
            # Determine extension from the original SHA256-based path
            ext = Path(relative_path).suffix.lower()
            self._counter += 1
            seq_name = f"{self._counter}{ext}"
            self._hash_to_name[h] = seq_name

        # Record old→new mapping (the old SHA256 path is what save_base64_image
        # returns and what ends up in span['image_path'])
        self._old_to_new[relative_path] = seq_name

        # Dedup: don't write the same content twice
        if seq_name in self._mineru_written_image_paths:
            return

        self._real.write(seq_name, data)
        self._mineru_written_image_paths.add(seq_name)

    def patch_markdown(self, markdown: str, img_buket_path: str) -> str:
        """Replace SHA256-based image paths in *markdown* with sequential names."""
        import re

        # Also build a proper name ordering for Markdown references
        # old_to_new maps  SHA256.ext  →  3.png
        prefix = f"{img_buket_path}/" if img_buket_path else ""

        def _replace(m):
            old_path = m.group(1)
            old_basename = old_path.rsplit("/", 1)[-1] if "/" in old_path else old_path
            new_basename = self._old_to_new.get(old_basename, old_basename)
            new_full = f"{prefix}{new_basename}"
            return m.group(0).replace(old_path, new_full)

        # Replace in ![]() and src=""
        md = re.sub(r'!\[\]\(([^)]+)\)', _replace, markdown)
        md = re.sub(r'src="([^"]+)"', _replace, md)
        return md
