"""Shared one-shot Rscript subprocess machinery for the heterogeneity wrappers.

Each R-backed diagnostic in this subpackage (the mixed-effects variance
decomposition, the Bradley-Terry trees) follows the same boundary: serialise
the input to JSON, run a one-shot Rscript that fits the model and prints its
JSON result to stdout, then parse that output. The mechanics are identical
across diagnostics and live here: locating the Rscript executable, probing for
the required R packages, running the subprocess under a timeout, and parsing
the printed JSON. A one-shot subprocess is used rather than reticulate so each
diagnostic runs in a clean R process with no shared interpreter state.
"""

from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
from importlib import resources

_PROBE_TIMEOUT_SECONDS = 30


class RNotAvailableError(RuntimeError):
    """Raised when Rscript or a required R package is not on the system."""


class RExecutionError(RuntimeError):
    """Raised when the R subprocess exits with an error or unparseable output."""


def rscript_executable() -> str:
    """Return the Rscript executable to call.

    Defaults to ``Rscript`` on PATH. Set the ``BEAM_RSCRIPT`` environment
    variable to an explicit path or wrapper script to point beam at an R
    living elsewhere, for example an ``Rscript`` shim that runs inside an
    apptainer or singularity container.
    """
    return os.environ.get("BEAM_RSCRIPT", "Rscript")


@functools.cache
def packages_available(packages: tuple[str, ...]) -> bool:
    """Return True when Rscript is callable and every named package is installed.

    The result is cached per package set for the process. Tests and vignettes
    use this to skip an analysis cleanly on a machine without the R toolchain.

    Parameters
    ----------
    packages
        R package names that must all resolve through ``requireNamespace``.
    """
    rscript = rscript_executable()
    if shutil.which(rscript) is None and not os.path.exists(rscript):
        return False
    checks = " && ".join(f'requireNamespace("{p}", quietly = TRUE)' for p in packages)
    probe = f"quit(status = if ({checks}) 0L else 1L)"
    try:
        completed = subprocess.run(
            [rscript, "-e", probe],
            capture_output=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


def run_rscript(
    r_package: str,
    script_name: str,
    payload: dict,
    required_packages: tuple[str, ...],
    timeout: int,
) -> dict:
    """Run a packaged Rscript on a JSON payload and parse the JSON it prints.

    Parameters
    ----------
    r_package
        Import package that ships the script, for ``importlib.resources``
        (for example ``"beam.heterogeneity"``).
    script_name
        File name of the R script within that package.
    payload
        JSON-serialisable input written to the subprocess stdin.
    required_packages
        R packages that must be present; checked via ``packages_available``.
    timeout
        Seconds before the fit is abandoned.

    Returns
    -------
    dict
        The parsed JSON object the script printed to stdout.

    Raises
    ------
    RNotAvailableError
        If the R toolchain or a required package is missing.
    RExecutionError
        If the subprocess fails, times out, or prints unparseable output.
    """
    if not packages_available(tuple(required_packages)):
        raise RNotAvailableError(
            "Rscript with the "
            + ", ".join(required_packages)
            + " packages is required for this analysis; check "
            "beam.heterogeneity.r_available or .bttree_available"
        )
    script = str(resources.files(r_package).joinpath(script_name))
    try:
        completed = subprocess.run(
            [rscript_executable(), script],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RExecutionError(f"the R fit timed out after {timeout}s") from exc
    if completed.returncode != 0:
        raise RExecutionError(f"the R fit failed:\n{completed.stderr.strip()}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RExecutionError(
            f"could not parse the R output as JSON:\n{completed.stdout.strip()}"
        ) from exc
