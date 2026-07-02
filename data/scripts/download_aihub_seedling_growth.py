from __future__ import annotations

import sys

from common import CATALOG_DIR, DATA_DIR
from download_aihub_horticulture import main


def add_default_arg(name: str, value: str) -> None:
    if name not in sys.argv:
        sys.argv.extend([name, value])


if __name__ == "__main__":
    add_default_arg("--catalog", str(CATALOG_DIR / "aihub_seedling_growth_files.json"))
    add_default_arg("--output-dir", str(DATA_DIR / "external" / "aihub" / "seedling_growth"))
    main()
