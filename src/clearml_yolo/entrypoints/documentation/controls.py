"""Reference the installed Hydra CLI without running its command dispatcher."""

from hydra._internal.utils import get_args_parser  # noqa: PLC2701 - installed Hydra CLI inventory

from clearml_yolo.core.documentation import FieldDoc

CONTROLS = {
    "help": ("Справка приложения и доступные конфигурационные группы.", "--help"),
    "hydra_help": ("Справка общих параметров Hydra.", "--hydra-help"),
    "version": ("Версия Hydra; это не версия установленного CY.", "--version"),
    "overrides": (
        "Упорядоченные key=value переопределения; точки задают вложенные поля.",
        "ultralytics.epochs=1",
    ),
    "cfg": ("Напечатать job, hydra или all вместо выполнения приложения.", "--cfg job"),
    "resolve": (
        (
            "Разрешить интерполяции при --cfg. Терминальная команда может читать окружение; "
            "предпросмотр этого не делает."
        ),
        "--cfg job --resolve",
    ),
    "package": (
        "Ограничить вывод --cfg выбранным пакетом конфигурации.",
        "--cfg job --package model",
    ),
    "run": ("Выполнить один запуск; команда имеет обычные эффекты выполнения CY.", "--run"),
    "multirun": (
        ("Выполнить перебор конфигураций последовательно через стандартный BasicLauncher."),
        "--multirun ultralytics.epochs=1,2",
    ),
    "shell_completion": (
        (
            "Показать команды установки/удаления shell completion Hydra; выполняйте их "
            "осознанно в терминале."
        ),
        "--shell-completion install=bash",
    ),
    "config_path": (
        (
            "Заменить основной путь конфигураций Hydra; относительный путь отсчитывается от "
            "Python entrypoint."
        ),
        "--config-path /path/to/configs",
    ),
    "config_name": (
        "Выбрать имя основной YAML-конфигурации без расширения.",
        "--config-name cy-train",
    ),
    "config_dir": (
        (
            "Добавить локальный каталог конфигураций; для экспортированных примеров "
            "одновременно передайте --config-name."
        ),
        "--config-dir ./configs --config-name cy-train",
    ),
    "experimental_rerun": (
        (
            "Экспериментальный повтор Hydra из pickle. Загружайте только доверенные файлы; "
            "это не ClearML Agent replay."
        ),
        "--experimental-rerun /trusted/job.pickle",
    ),
    "info": (
        ("Диагностика конфигураций, defaults, плагинов и путей поиска без запуска обучения."),
        "--info defaults-tree",
    ),
}


def hydra_controls(commands: list[str]) -> list[FieldDoc]:
    # argparse has no public action iterator; its stable actions expose the actual
    # installed Hydra flags, so additions fail coverage instead of disappearing.
    actions = get_args_parser()._actions  # noqa: SLF001 - read-only argparse inventory
    actual = {action.dest for action in actions}
    if actual != set(CONTROLS):
        raise ValueError(f"Hydra CLI documentation mismatch: {actual ^ set(CONTROLS)}")
    result = []
    for action in actions:
        description, example = CONTROLS[action.dest]
        name = action.option_strings[0] if action.option_strings else "overrides"
        path = f"hydra.{name}"
        result.append(
            FieldDoc(
                id=path,
                path=path,
                description=description,
                shapes="flag" if action.nargs == 0 else "string",
                constraints=(
                    f"aliases={action.option_strings}; choices={action.choices}; "
                    f"nargs={action.nargs}; default={action.default}"
                ),
                applicability=(
                    "CLI Hydra; параметры запуска передаются в терминале, не как поля YAML."
                ),
                examples=[example],
                source="hydra._internal.utils.get_args_parser",
                commands=commands,
            )
        )
    return result
