from importlib import import_module

__all__ = ["AblationRunner", "BenchRunner"]


def __getattr__(name: str):
    if name == "AblationRunner":
        return import_module(".ablation_runner", __name__).AblationRunner
    if name == "BenchRunner":
        return import_module(".bench_runner", __name__).BenchRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
