"""HTML report generation for a beam RunResult.

The package is named ``reporting`` so the public convenience ``beam.report``
can be a callable (a module and a function cannot share the name
``beam.report``). ``write_report`` is the full entry point; ``beam.report`` is
an alias for it.
"""

from .render import write_report

__all__ = ["write_report"]
