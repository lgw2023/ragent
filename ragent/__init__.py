from .ragent import QueryParam as QueryParam, Ragent as Ragent

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
    if name == "WideTableImportConfig":
        from .wide_table import WideTableImportConfig as exported_config

        return exported_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
