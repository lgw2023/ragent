from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import QueryParam as QueryParam
    from .ragent import Ragent as Ragent
    from .wide_table import WideTableImportConfig as WideTableImportConfig

#--> modified by ACS
__version__ = "1.0.0"
__author__ = "ACS"
#--> ended by ACS

__all__ = [
    "Ragent",
    "QueryParam",
    "WideTableImportConfig",
    "__version__",
    "__author__",
]


def __getattr__(name: str):
    if name == "Ragent":
        from .ragent import Ragent as exported_ragent

        return exported_ragent
    if name == "QueryParam":
        from .base import QueryParam as exported_query_param

        return exported_query_param
    if name == "WideTableImportConfig":
        from .wide_table import WideTableImportConfig as exported_config

        return exported_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
