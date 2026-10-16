"""Resolve native Hydra launch semantics before direct or queued effects."""

from datetime import UTC, datetime
from secrets import choice

from hydra._internal.core_plugins.basic_sweeper import BasicSweeper
from hydra.core.global_hydra import GlobalHydra
from hydra.core.override_parser.overrides_parser import OverridesParser
from hydra.types import RunMode
from omegaconf import DictConfig, OmegaConf, open_dict


def task_overrides(config: DictConfig) -> list[str]:
    """Keep job-local interpolations unresolved until the job context exists."""
    values = OmegaConf.to_container(config.hydra.overrides.task, resolve=False)
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise TypeError("Hydra task overrides must be a list of strings")
    return [str(value) for value in values]


def new_multirun_tag() -> str:
    """Create an independent group for one launch or queued submission."""
    words = (
        "amber",
        "birch",
        "bloom",
        "brook",
        "cedar",
        "cloud",
        "coral",
        "dawn",
        "delta",
        "dune",
        "elm",
        "fern",
        "field",
        "flint",
        "forest",
        "frost",
        "grove",
        "harbor",
        "hazel",
        "hill",
        "iris",
        "lake",
        "maple",
        "meadow",
        "moon",
        "oak",
        "pine",
        "river",
        "stone",
        "sun",
        "valley",
        "willow",
    )
    phrase = "-".join(choice(words) for _ in range(6))
    return f"multirun-{datetime.now(UTC):%Y%m%d-%H%M%S}-{phrase}"


def tag_multirun_job(config: DictConfig, tag: str) -> None:
    """Append the launch-owned group to a job, preserving its explicit tags."""
    tags = list(config.clearml.tags)
    if tag not in tags:
        with open_dict(config.clearml):
            config.clearml.tags = [*tags, tag]


def compose_jobs(
    name: str, overrides: list[str], *, multirun: bool
) -> tuple[bool, tuple[DictConfig, ...]]:
    """Compose complete jobs in an initialized Hydra context, without launching.

    Like Hydra, probe mode with sweep syntax permitted; an explicit -m takes
    precedence over configured RUN. Saved sweeper parameters precede CLI task
    overrides, so the BasicSweeper's own expansion applies the same precedence.
    """
    hydra = GlobalHydra.instance().hydra
    if hydra is None:
        raise RuntimeError("Hydra initialization did not provide a composer")
    probe = hydra.compose_config(
        config_name=name,
        overrides=overrides,
        run_mode=RunMode.MULTIRUN,
        validate_sweep_overrides=False,
    )
    multirun = multirun or probe.hydra.mode == RunMode.MULTIRUN
    mode = RunMode.MULTIRUN if multirun else RunMode.RUN
    parser = OverridesParser.create(config_loader=hydra.config_loader)
    if not multirun and any(item.is_sweep_override() for item in parser.parse_overrides(overrides)):
        raise ValueError("Use -m or hydra.mode=MULTIRUN to expand a Hydra sweep")
    configuration = hydra.compose_config(
        config_name=name,
        overrides=[*overrides, f"hydra.mode={mode.name}"],
        run_mode=mode,
    )
    if not multirun:
        return False, (configuration,)
    for plugin in ("sweeper", "launcher"):
        expected = (
            "hydra._internal.core_plugins.basic_sweeper.BasicSweeper"
            if plugin == "sweeper"
            else "hydra._internal.core_plugins.basic_launcher.BasicLauncher"
        )
        if configuration.hydra[plugin]._target_ != expected:
            raise ValueError(
                "cy supports sequential BasicSweeper/BasicLauncher sweeps; "
                "use cy-queue for concurrent execution"
            )
    parameters = configuration.hydra.sweeper.get("params") or {}
    arguments = [f"{key}={value}" for key, value in parameters.items()]
    arguments.extend(task_overrides(configuration))
    batches = BasicSweeper.split_arguments(parser.parse_overrides(arguments), None)
    jobs = tuple(
        hydra.config_loader.load_sweep_config(configuration, values)
        for batch in batches
        for values in batch
    )
    if not jobs:
        raise ValueError("Hydra sweep must produce at least one job")
    return True, jobs
