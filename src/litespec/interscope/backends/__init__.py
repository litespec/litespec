"""ISIR-side helpers.

The in-repo ``structural`` check (``discharge``) is LiteSpec's EC-side α-coherence
check for the LIR→ISIR abstraction seam — **not** an InterScope backend and **not**
for EC. InterScope itself (``verify-isir``) verifies generic properties on the
abstracted transition system via its own ``run.sh`` (SymbiYosys / Kōika / ACL2).
"""

from litespec.interscope.backends.structural_backend import BACKEND_NAME, discharge

__all__ = ["BACKEND_NAME", "discharge"]
