"""User journeys against the actual packaged site and composition worker."""

import json
import re
import signal
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect

from browser_tests.conftest import start_server


def open_editor(page: Page) -> None:
    page.goto("/")
    expect(page.get_by_role("heading", name="Настройки без догадок")).to_be_visible()
    page.get_by_label("Команда", exact=True).select_option("train")
    page.get_by_label("Модель", exact=True).select_option("ultralytics")


def test_search_stable_links_and_keyboard_navigation(page: Page) -> None:
    open_editor(page)
    page.get_by_label("Найти параметр").fill("ultralytics.batch")
    link = page.get_by_role("list", name="Параметры").get_by_role(
        "link", name=re.compile(r"^ultralytics\.batch")
    )
    expect(link).to_have_count(1)
    link.focus()
    page.keyboard.press("Enter")
    expect(page).to_have_url(re.compile(r"#field=ultralytics\.batch$"))
    detail = page.get_by_role("article", name="Описание параметра")
    expect(detail.get_by_role("heading", name="ultralytics.batch", exact=True)).to_be_visible()
    expect(detail).to_contain_text("Форма ввода")
    page.reload()
    expect(detail.get_by_role("heading", name="ultralytics.batch", exact=True)).to_be_visible()
    page.get_by_role("heading", name="Настройки без догадок").click()
    page.keyboard.press("/")
    expect(page.get_by_label("Найти параметр")).to_be_focused()


def test_edit_preview_differences_clipboard_and_download(page: Page, tmp_path: Path) -> None:
    open_editor(page)
    page.get_by_label("Содержимое YAML", exact=True).fill(
        "defaults:\n  - train\n  - _self_\nground_truth: ./tiny.csv\n"
    )
    page.get_by_label("Переопределения по порядку").fill("ultralytics.epochs=2")
    page.get_by_role("button", name="Предпросмотр").click()
    result = page.get_by_role("region", name="Результат предпросмотра")
    expect(result).to_be_visible()
    yaml = page.get_by_label("Собранный YAML")
    expect(yaml).to_contain_text("epochs: 2")
    expect(result).to_contain_text("tiny.csv")
    expect(result).to_contain_text("Изменения от исходной композиции")
    page.get_by_role("button", name="Копировать YAML", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="Скопировано")).to_be_visible()
    assert "epochs: 2" in page.evaluate("navigator.clipboard.readText()")
    with page.expect_download() as received:
        page.get_by_role("button", name="Скачать YAML", exact=True).click()
    received.value.save_as(tmp_path / "download.yaml")
    assert "epochs: 2" in (tmp_path / "download.yaml").read_text()
    with page.expect_download() as documents:
        page.get_by_role("button", name="Скачать документы JSON", exact=True).click()
    documents.value.save_as(tmp_path / "documents.json")
    assert json.loads((tmp_path / "documents.json").read_text())["example.yaml"].endswith(
        "ground_truth: ./tiny.csv\n"
    )


def test_named_documents_and_ordered_overrides(page: Page) -> None:
    open_editor(page)
    page.get_by_label("Содержимое YAML", exact=True).fill(
        "defaults:\n  - train\n  - custom\n  - _self_\n"
    )
    page.get_by_role("button", name="+ Документ", exact=True).click()
    page.get_by_label("Имя документа", exact=True).nth(1).fill("custom.yaml")
    page.get_by_label("Содержимое YAML", exact=True).nth(1).fill("ultralytics:\n  epochs: 3\n")
    page.get_by_label("Переопределения по порядку").fill(
        "ultralytics.epochs=4\nultralytics.epochs=5"
    )
    page.get_by_label("Переопределения по порядку").press("Control+Enter")
    expect(page.get_by_label("Собранный YAML")).to_contain_text("epochs: 5")
    page.get_by_role("button", name="Удалить документ 2", exact=True).click()
    expect(page.get_by_label("Имя документа", exact=True)).to_have_count(1)


def test_reference_examples_are_valid_overrides(page: Page) -> None:
    open_editor(page)
    page.get_by_label("Найти параметр").fill("ground_truth")
    page.get_by_role("list", name="Параметры").get_by_role(
        "link", name=re.compile(r"^ground_truth ")
    ).click()
    detail = page.get_by_role("article", name="Описание параметра")
    detail.get_by_role("button", name="ground_truth=truth.csv", exact=True).click()
    expect(page.get_by_label("Переопределения по порядку")).to_have_value("ground_truth=truth.csv")
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_label("Собранный YAML")).to_contain_text("ground_truth: truth.csv")
    page.get_by_label("Команда", exact=True).select_option("compare")
    page.get_by_role("button", name="Начальный пример", exact=True).click()
    page.get_by_label("Найти параметр").fill("baseline_model.thresholds")
    page.get_by_role("list", name="Параметры").get_by_role("link").click()
    detail.get_by_role("button", name="baseline_model.thresholds={defect:0.35}", exact=True).click()
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_label("Собранный YAML")).to_contain_text("defect: 0.35")


def test_required_marker_follows_selected_command(page: Page) -> None:
    open_editor(page)
    page.get_by_label("Найти параметр").fill("ground_truth")
    page.get_by_role("list", name="Параметры").get_by_role(
        "link", name=re.compile(r"^ground_truth ")
    ).click()
    detail = page.get_by_role("article", name="Описание параметра")
    expect(detail.get_by_text("Обязательное значение", exact=True)).to_be_visible()
    page.get_by_label("Команда", exact=True).select_option("export")
    expect(detail.get_by_text("Есть значение по умолчанию", exact=True)).to_be_visible()
    expect(detail.get_by_text("Обязательное значение", exact=True)).to_have_count(0)


def test_mapping_and_relative_nested_examples_compose(page: Page) -> None:
    open_editor(page)
    page.get_by_label("Команда", exact=True).select_option("pipeline")
    page.get_by_role("button", name="Начальный пример", exact=True).click()
    for field, expected in (
        ("clearml", "clearml.project_name=examples"),
        ("compare.q", "compare.q=0.05"),
        ("metrics.calibration_split", "metrics.calibration_split=val"),
    ):
        page.get_by_label("Найти параметр").fill(field)
        page.get_by_role("list", name="Параметры").get_by_role(
            "link", name=re.compile(rf"^{re.escape(field)} ")
        ).click()
        page.get_by_role("article", name="Описание параметра").get_by_role(
            "button", name=expected, exact=True
        ).click()
    page.get_by_role("button", name="Предпросмотр").click()
    yaml = page.get_by_label("Собранный YAML")
    expect(yaml).to_contain_text("project_name: examples")
    expect(yaml).to_contain_text("q: 0.05")
    expect(yaml).to_contain_text("calibration_split: val")


def test_local_requests_only_and_loaded_search_works_offline(page: Page) -> None:
    outside: list[str] = []

    def local_only(route: Route) -> None:
        if route.request.url.startswith("http://127.0.0.1:"):
            route.continue_()
        else:
            outside.append(route.request.url)
            route.abort()

    page.route("**/*", local_only)
    open_editor(page)
    page.context.set_offline(True)
    page.get_by_label("Найти параметр").fill("ground_truth")
    expect(page.get_by_role("list", name="Параметры").get_by_role("link")).not_to_have_count(0)
    page.context.set_offline(False)
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_role("region", name="Результат предпросмотра")).to_be_visible()
    assert outside == []


def test_worker_errors_preserve_inputs_and_allow_retry(page: Page) -> None:
    open_editor(page)
    overrides = page.get_by_label("Переопределения по порядку")
    overrides.fill("ultralytics.epochs=2")

    def fail_worker(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {"jobs": [], "errors": ["Preview worker timed out"], "deferred": [], "command": ""}
            ),
        )

    page.route("**/api/preview", fail_worker)
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_role("alert").filter(has_text="Preview worker timed out")).to_be_visible()
    expect(overrides).to_have_value("ultralytics.epochs=2")
    page.unroute("**/api/preview", fail_worker)
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_label("Собранный YAML")).to_contain_text("epochs: 2")


def test_unsafe_settings_and_environment_are_visible_without_execution(page: Page) -> None:
    open_editor(page)
    overrides = page.get_by_label("Переопределения по порядку")
    overrides.fill("ground_truth=${oc.env:CY_DOCS_TEST_SECRET}")
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_label("Собранный YAML")).to_contain_text("${oc.env:CY_DOCS_TEST_SECRET}")
    overrides.fill("hydra.searchpath=[file:///tmp]")
    page.get_by_role("button", name="Предпросмотр").click()
    expect(page.get_by_role("alert")).to_be_visible()
    expect(page.get_by_role("region", name="Результат предпросмотра")).to_be_hidden()


def test_tutorial_examples_and_mobile_layout(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("/")
    tutorials = page.get_by_role("region", name="Пройдите весь путь")
    expect(tutorials).to_be_visible()
    tutorials.get_by_role("button", name="Редактировать пример").first.click()
    expect(page.get_by_label("Переопределения по порядку")).to_be_focused()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_shutdown_closes_listener() -> None:
    with start_server() as server:
        with urllib.request.urlopen(server.url + "/api/catalog", timeout=20) as response:  # noqa: S310 - fixture-owned loopback URL
            assert response.status == 200
        server.process.send_signal(signal.SIGINT)
        assert server.process.wait(timeout=20) == 0
        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen(server.url + "/api/catalog", timeout=1)  # noqa: S310 - fixture-owned loopback URL
