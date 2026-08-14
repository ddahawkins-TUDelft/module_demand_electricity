"""Download and cache the fixed OPSD electricity-demand snapshot."""

import logging
import shutil
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

logger = logging.getLogger(__name__)

USER_AGENT = "modelblocks-module-demand-electricity/OPSD downloader"

REQUIRED_COLUMNS = {
    "utc_timestamp",
    "region",
    "variable",
    "attribute",
    "data",
}


def _is_valid_cached_snapshot(path: Path) -> bool:
    """Return whether an existing OPSD snapshot is suitable for reuse."""
    if not path.exists() or path.stat().st_size == 0:
        return False

    try:
        columns = set(pd.read_csv(path, nrows=0).columns)
    except (OSError, ValueError):
        return False

    return REQUIRED_COLUMNS.issubset(columns)


def download_opsd(*, url: str, output_path: str | Path) -> None:
    """Download the OPSD snapshot unless a valid cached copy exists."""
    output_path = Path(output_path)

    if _is_valid_cached_snapshot(output_path):
        logger.info("Using cached OPSD snapshot: %s", output_path)
        return

    if output_path.exists():
        logger.warning("Cached OPSD snapshot is invalid; downloading a replacement.")
        output_path.unlink()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(output_path.suffix + ".part")
    temporary_path.unlink(missing_ok=True)

    logger.info("Downloading OPSD snapshot from %s.", url)

    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with (
            urlopen(request, timeout=300) as response,
            temporary_path.open("wb") as output_file,
        ):
            content_length = response.headers.get("Content-Length")
            shutil.copyfileobj(response, output_file)

        downloaded_size = temporary_path.stat().st_size

        if content_length is not None and downloaded_size != int(content_length):
            raise RuntimeError(
                "OPSD download is incomplete: "
                f"received {downloaded_size} of {content_length} bytes."
            )

        if not _is_valid_cached_snapshot(temporary_path):
            raise RuntimeError(
                "Downloaded OPSD snapshot does not contain the expected CSV structure."
            )

        temporary_path.replace(output_path)

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    logger.info(
        "Saved OPSD snapshot to %s (%s bytes).",
        output_path,
        output_path.stat().st_size,
    )


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    download_opsd(
        url=snakemake.params.url,
        output_path=snakemake.output.load,
    )
