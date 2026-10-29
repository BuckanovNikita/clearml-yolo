"use strict";

// All catalog and preview values enter the DOM as text, never as HTML.
const element = (id) => document.getElementById(id);
const state = {catalog: null, selectedField: null, configuration: null, result: null, documentId: 0, dirty: false, editVersion: 0, lastRequest: null};
const missing = Symbol("missing");
let toastTimer;

function node(tag, text, className) {
  const value = document.createElement(tag);
  if (text !== undefined) value.textContent = text;
  if (className) value.className = className;
  return value;
}

function pretty(value) {
  if (value === missing) return "не задано";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function toast(message) {
  clearTimeout(toastTimer);
  element("toast").textContent = message;
  element("toast").hidden = false;
  toastTimer = setTimeout(() => { element("toast").hidden = true; }, 4000);
}

function errorBox(id, messages) {
  element(id).textContent = messages.join("\n");
  element(id).hidden = messages.length === 0;
}

function selectedCommand() { return element("command").value; }
function selectedModel() { return element("model").value; }
function selectedProfile() { return element("profile").value; }

function fillSelect(select, options, requested) {
  select.replaceChildren(...options.map(([value, title]) => {
    const option = node("option", title);
    option.value = value;
    return option;
  }));
  if (options.some(([value]) => value === requested)) select.value = requested;
  select.disabled = options.length < 2;
}

function refreshSelections() {
  const configurations = state.catalog.configurations.filter((item) => item.command === selectedCommand());
  const models = [...new Set(configurations.map((item) => item.model))];
  const profiles = [...new Set(configurations.map((item) => item.profile))];
  fillSelect(element("model"), models.length ? models.map((model) => [model, model || "Не применяется"]) : [["", "Не применяется"]], selectedModel());
  fillSelect(element("profile"), profiles.length ? profiles.map((profile) => [profile, profile || "Не применяется"]) : [["", "Не применяется"]], selectedProfile());
  selectConfiguration();
}

function selectConfiguration() {
  state.configuration = state.catalog.configurations.find((item) => item.command === selectedCommand() && item.model === selectedModel() && item.profile === selectedProfile()) || null;
  element("default-yaml").textContent = state.configuration?.yaml || "У этой утилиты нет конфигурации Hydra. Параметры передаются в командной строке.";
  element("editor-context").textContent = [state.catalog.commands[selectedCommand()], selectedModel(), selectedProfile()].filter(Boolean).join(" / ");
  element("preview").disabled = !state.configuration;
  renderFields();
  renderField(state.selectedField);
  if (state.result) renderJob();
}

function isApplicable(field) {
  const publicCommand = state.catalog.commands[selectedCommand()];
  return field.commands.length === 0 || field.commands.includes(selectedCommand()) || field.commands.includes(publicCommand);
}

function isModelApplicable(field) {
  const model = selectedModel();
  if (!model) return true;
  if (model === "ultralytics" && /^(model\.(train|predict)\.|model\.source_dir$)/u.test(field.path)) return false;
  if (model !== "ultralytics" && /^ultralytics(_predict)?\./u.test(field.path)) return false;
  if (/^(ultralytics(_predict)?\.|model\.train\.augmentation\.)/u.test(field.path)) {
    return Object.hasOwn(state.configuration?.values || {}, field.path);
  }
  return true;
}

function effectiveField(field) {
  return {...field, ...(field.variants?.[selectedCommand()] || {})};
}

function renderFields() {
  const query = element("search").value.toLocaleLowerCase("ru").trim();
  const fields = state.catalog.fields.map(effectiveField).filter((field) => {
    if (!isApplicable(field)) return false;
    if (!element("show-inactive").checked && !isModelApplicable(field)) return false;
    const searchable = [field.path, field.description, field.shapes, field.applicability, ...field.examples.map(pretty)].join(" ").toLocaleLowerCase("ru");
    return !query || query.split(/\s+/u).every((word) => searchable.includes(word));
  });
  element("field-list").replaceChildren(...fields.map((field) => {
    const item = node("li");
    const link = node("a");
    link.href = `/#field=${encodeURIComponent(field.id)}`;
    link.dataset.field = field.id;
    link.setAttribute("aria-current", String(state.selectedField?.id === field.id));
    link.append(node("code", field.path), node("span", field.description, "field-summary"));
    link.addEventListener("click", (event) => { event.preventDefault(); selectField(field, true); });
    item.append(link);
    return item;
  }));
  element("field-count").textContent = `Найдено параметров: ${fields.length}`;
  element("no-fields").hidden = fields.length !== 0;
  if (fields.length && (!state.selectedField || !isApplicable(state.selectedField) || (!element("show-inactive").checked && !isModelApplicable(state.selectedField)))) selectField(fields[0], false);
}

function selectField(field, updateHash) {
  state.selectedField = field;
  if (updateHash) history.replaceState(null, "", `/#field=${encodeURIComponent(field.id)}`);
  for (const link of element("field-list").querySelectorAll("a")) link.setAttribute("aria-current", String(link.dataset.field === field.id));
  renderField(field);
}

function addDetail(list, title, value, code = false) {
  list.append(node("dt", title));
  const definition = node("dd");
  definition.append(node(code ? "pre" : "span", value));
  list.append(definition);
}

function fieldValue(path, kind) {
  const values = state.configuration?.[kind];
  return values && Object.hasOwn(values, path) ? values[path] : missing;
}

function hydraValue(value) {
  if (Array.isArray(value)) return `[${value.map(hydraValue).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.entries(value).map(([key, child]) => {
      if (!/^[\w./@%*?$|+ :,-]+$/u.test(key)) throw new Error("Ключ этого примера нужно задать в YAML.");
      const escaped = key.replace(/[ :,]/gu, "\\$&");
      return `${escaped}:${hydraValue(child)}`;
    }).join(",")}}`;
  }
  if (typeof value === "string") {
    // JSON double quotes are supported Hydra string values; shell quoting belongs to export.
    return JSON.stringify(value);
  }
  return JSON.stringify(value);
}

function appendOverride(field, example) {
  const line = exampleOverride(field, example);
  const editor = element("overrides");
  editor.value = [editor.value.trimEnd(), line].filter(Boolean).join("\n");
  edited();
  element("editor").scrollIntoView({block: "start"});
  editor.focus({preventScroll: true});
  toast("Переопределение добавлено в конец списка");
}

function exampleOverride(field, example) {
  if (field.path.startsWith("hydra.")) return null;
  if (typeof example === "string" && example.includes("=")) {
    const key = example.slice(0, example.indexOf("="));
    if (key === field.path || key.startsWith(`${field.path}.`)) return example;
    // Nested declarations are shared with standalone commands and carry relative keys.
    const parts = field.path.split(".");
    const leaf = parts.pop();
    if (parts.length && (key === leaf || key.startsWith(`${leaf}.`))) {
      return `${parts.join(".")}.${example}`;
    }
  }
  return `${field.path}=${hydraValue(example)}`;
}

function renderField(field) {
  if (!field) return;
  field = effectiveField(field);
  const selected = fieldValue(field.path, "values");
  const required = selected === missing ? field.required : selected === "???";
  const detail = element("field-detail");
  detail.replaceChildren();
  const heading = node("div", undefined, "field-title");
  heading.append(node("h3", field.path));
  const permalink = node("a", "Ссылка на поле ↗");
  permalink.href = `/#field=${encodeURIComponent(field.id)}`;
  heading.append(permalink);
  detail.append(heading);
  detail.append(node("span", field.generated ? "Снимок / происхождение" : "Входной параметр", "tag"));
  detail.append(node("span", required ? "Обязательное значение" : "Есть значение по умолчанию", required ? "tag required" : "tag"));
  detail.append(node("p", field.description, "field-description"));
  const facts = node("dl");
  addDetail(facts, "Форма ввода", field.shapes);
  addDetail(facts, "Ограничения", field.constraints);
  addDetail(facts, "Применяется", field.applicability);
  const raw = fieldValue(field.path, "expressions");
  if (raw !== missing) addDetail(facts, "Выражение", pretty(raw), true);
  addDetail(facts, "Выбранное значение", pretty(selected), true);
  detail.append(facts);
  if (field.examples.length) {
    detail.append(node("h4", "Примеры ввода"));
    if (!field.generated && state.configuration) detail.append(node("p", "Нажмите пример, чтобы добавить его в переопределения редактора.", "hint"));
    for (const example of field.examples) {
      let override;
      try { override = exampleOverride(field, example); }
      catch { override = null; }
      if (field.generated || !state.configuration || field.path.startsWith("--") || override === null) {
        detail.append(node("pre", pretty(example)));
      } else {
        const button = node("button", override, "example-button");
        button.type = "button";
        button.addEventListener("click", () => appendOverride(field, example));
        detail.append(button);
      }
    }
  }
  detail.append(node("p", `Определение: ${field.source}`, "source"));
  element("editor-field-help").replaceChildren(node("h4", field.path), node("p", field.description), node("p", `${field.shapes} · ${field.constraints}`, "hint"));
}

function addDocument(name = "", content = "") {
  if (element("documents").children.length >= 32) { toast("Можно добавить не более 32 документов"); return; }
  const id = ++state.documentId;
  const block = node("div", undefined, "document");
  const header = node("div", undefined, "document-title");
  const nameGroup = node("div");
  const label = node("label", "Имя документа");
  label.htmlFor = `document-name-${id}`;
  const input = node("input");
  input.id = label.htmlFor;
  input.value = name || `extra-${id}.yaml`;
  input.required = true;
  input.className = "document-name";
  input.spellcheck = false;
  nameGroup.append(label, input);
  const remove = node("button", "Удалить", "quiet");
  remove.type = "button";
  remove.setAttribute("aria-label", `Удалить документ ${id}`);
  remove.addEventListener("click", () => { block.remove(); edited(); });
  header.append(nameGroup, remove);
  const codeLabel = node("label", "Содержимое YAML");
  codeLabel.htmlFor = `document-content-${id}`;
  const textarea = node("textarea");
  textarea.id = codeLabel.htmlFor;
  textarea.className = "code-input document-content";
  textarea.spellcheck = false;
  textarea.rows = 9;
  textarea.value = content;
  block.append(header, codeLabel, textarea);
  block.addEventListener("input", edited);
  element("documents").append(block);
}

function starterDocument() {
  return `defaults:\n  - ${selectedCommand()}\n  - _self_\n\n# Задайте входы здесь или в переопределениях ниже.\n`;
}

function resetDocuments() {
  state.editVersion += 1;
  element("documents").replaceChildren();
  if (state.configuration) addDocument("example.yaml", starterDocument());
  element("overrides").value = "";
  element("sweep").checked = false;
  state.dirty = false;
  state.result = null;
  element("result").hidden = true;
  errorBox("preview-error", []);
  element("preview-status").textContent = "";
}

function edited() {
  state.dirty = true;
  state.editVersion += 1;
  if (state.result) {
    state.result = null;
    element("result").hidden = true;
    element("preview-status").textContent = "Конфигурация изменена. Выполните предпросмотр заново.";
  }
}

function documentValues() {
  const result = Object.create(null);
  for (const block of element("documents").children) {
    const name = block.querySelector(".document-name").value.trim();
    if (!name || Object.hasOwn(result, name)) throw new Error("Имена документов должны быть непустыми и уникальными.");
    result[name] = block.querySelector(".document-content").value;
  }
  return result;
}

function currentRequest() {
  const overrides = [];
  if (selectedModel()) overrides.push(`model=${selectedModel()}`);
  if (selectedProfile()) overrides.push(`transforms=${selectedProfile()}`);
  overrides.push(...element("overrides").value.split("\n").map((line) => line.trim()).filter((line) => line && !line.startsWith("#")));
  return {command: selectedCommand(), documents: documentValues(), overrides, sweep: element("sweep").checked};
}

async function preview(event) {
  event?.preventDefault();
  if (!state.configuration || element("preview").disabled) return;
  errorBox("preview-error", []);
  element("preview-status").textContent = "Собираем конфигурацию…";
  element("preview").disabled = true;
  element("result").hidden = true;
  state.result = null;
  const editVersion = state.editVersion;
  try {
    const request = currentRequest();
    const response = await fetch("/api/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request), signal: AbortSignal.timeout(20000)});
    const result = await response.json();
    if (!response.ok) throw new Error((result.errors || [result.error || `Ошибка HTTP ${response.status}`]).join("\n"));
    if (editVersion !== state.editVersion) {
      element("preview-status").textContent = "Во время предпросмотра конфигурация изменилась. Повторите запрос для новых значений.";
      return;
    }
    state.lastRequest = request;
    state.result = result;
    errorBox("preview-error", result.errors || []);
    if (result.jobs.length) {
      fillSelect(element("job"), result.jobs.map((_, index) => [String(index), `${index + 1} / ${result.jobs.length}`]), "0");
      element("result").hidden = false;
      element("result-command").textContent = result.command;
      renderList("deferred-checks", result.deferred, "Дополнительные проверки не указаны.");
      renderJob();
      element("preview-status").textContent = `Композиция готова. Запусков: ${result.jobs.length}. Обучение не запускалось.`;
    } else {
      element("preview-status").textContent = "Композиция не выполнена. Исправьте указанные ошибки.";
    }
  } catch (error) {
    errorBox("preview-error", [`Не удалось выполнить предпросмотр: ${error.message}`]);
    element("preview-status").textContent = "Ваши изменения сохранены в редакторе. Можно повторить запрос.";
  } finally {
    element("preview").disabled = !state.configuration;
  }
}

function renderList(id, values, empty) {
  element(id).replaceChildren(...(values.length ? values : [empty]).map((value) => node("li", value)));
}

function renderJob() {
  const job = state.result?.jobs[Number(element("job").value)];
  if (!job) return;
  element("result-yaml").textContent = job.yaml;
  errorBox("job-errors", job.errors || []);
  renderList("unresolved", job.unresolved, "Нет неразрешённых значений.");
  const base = state.configuration?.values || {};
  const changed = [...new Set([...Object.keys(base), ...Object.keys(job.values)])].sort().filter((key) => JSON.stringify(base[key]) !== JSON.stringify(job.values[key]));
  element("diff").replaceChildren(...changed.map((key) => {
    const row = node("div", undefined, "difference");
    row.append(node("code", key), node("del", `− ${pretty(Object.hasOwn(base, key) ? base[key] : missing)}`), node("ins", `+ ${pretty(Object.hasOwn(job.values, key) ? job.values[key] : missing)}`));
    return row;
  }));
  if (!changed.length) element("diff").append(node("p", "Значения совпадают с исходной композицией.", "hint"));
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Скопировано"); }
  catch { toast("Буфер обмена недоступен. Выделите текст и скопируйте вручную."); }
}

function download(text, name, type) {
  const url = URL.createObjectURL(new Blob([text], {type}));
  const link = node("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function useTutorialExample(example) {
  element("command").value = example.command;
  refreshSelections();
  for (const [prefix, select] of [["model=", element("model")], ["transforms=", element("profile")]]) {
    const override = [...example.overrides].reverse().find((value) => value.startsWith(prefix));
    const value = override?.slice(prefix.length);
    if (value && [...select.options].some((option) => option.value === value)) select.value = value;
  }
  selectConfiguration();
  resetDocuments();
  if (Object.keys(example.documents).length) {
    element("documents").replaceChildren();
    for (const [name, content] of Object.entries(example.documents)) addDocument(name, content);
  }
  element("overrides").value = example.overrides.join("\n");
  element("sweep").checked = example.sweep;
  edited();
  element("editor").scrollIntoView({block: "start"});
  element("overrides").focus({preventScroll: true});
  toast("Пример урока загружен. Измените входы и выполните предпросмотр.");
}

function renderTutorials() {
  element("tutorial-list").replaceChildren(...state.catalog.tutorials.map((tutorial, index) => {
    const card = node("article", undefined, "tutorial-card");
    card.append(node("span", String(index + 1).padStart(2, "0"), "tutorial-number"), node("h3", tutorial.title), node("p", `Команды: ${tutorial.commands.join(" · ")}`));
    const link = node("a", "Открыть урок →");
    link.href = `/tutorials/${encodeURIComponent(tutorial.file.replace(/\.md$/u, ".html"))}`;
    card.append(link);
    if (tutorial.previews.length) {
      const button = node("button", "Редактировать пример", "quiet");
      button.type = "button";
      button.addEventListener("click", () => useTutorialExample(tutorial.previews[0]));
      card.append(button);
    }
    card.append(node("p", `Настройки: ${tutorial.groups.join(" · ")}`, "group-list"));
    return card;
  }));
}

function followHash() {
  const parameters = new URLSearchParams(location.hash.slice(1));
  const fieldId = parameters.get("field");
  if (!fieldId) return;
  const field = state.catalog.fields.find((item) => item.id === fieldId || item.path === fieldId);
  if (!field) { toast("Параметр отсутствует в установленной версии"); return; }
  if (!isApplicable(field)) {
    const first = Object.keys(state.catalog.commands).find((command) => field.commands.includes(command) || field.commands.includes(state.catalog.commands[command]));
    if (first) { element("command").value = first; refreshSelections(); resetDocuments(); }
  }
  if (!isModelApplicable(field)) { element("show-inactive").checked = true; renderFields(); }
  selectField(field, false);
  element("reference").scrollIntoView({block: "start"});
}

function attachEvents() {
  element("filters").addEventListener("submit", (event) => event.preventDefault());
  element("search").addEventListener("input", renderFields);
  element("show-inactive").addEventListener("change", renderFields);
  element("command").addEventListener("change", () => {
    const hadEdits = state.dirty;
    edited();
    refreshSelections();
    if (hadEdits) toast("Команда изменена. Сверьте defaults в сохранённых документах или загрузите начальный пример.");
    else resetDocuments();
  });
  element("model").addEventListener("change", () => { edited(); selectConfiguration(); });
  element("profile").addEventListener("change", () => { edited(); selectConfiguration(); });
  element("add-document").addEventListener("click", () => { addDocument(); edited(); });
  element("reset-document").addEventListener("click", resetDocuments);
  element("overrides").addEventListener("input", edited);
  element("sweep").addEventListener("change", edited);
  element("preview-form").addEventListener("submit", preview);
  element("job").addEventListener("change", renderJob);
  element("copy-yaml").addEventListener("click", () => copyText(element("result-yaml").textContent));
  element("copy-command").addEventListener("click", () => copyText(element("result-command").textContent));
  element("download-yaml").addEventListener("click", () => download(element("result-yaml").textContent, "cy-preview.yaml", "application/yaml;charset=utf-8"));
  element("download-command").addEventListener("click", () => download(element("result-command").textContent + "\n", "cy-command.sh", "text/plain;charset=utf-8"));
  element("download-documents").addEventListener("click", () => {
    try { download(JSON.stringify(state.lastRequest?.documents || documentValues(), null, 2) + "\n", "cy-documents.json", "application/json;charset=utf-8"); }
    catch (error) { toast(error.message); }
  });
  window.addEventListener("hashchange", followHash);
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); preview(); }
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) { event.preventDefault(); element("search").focus(); }
  });
}

async function start() {
  try {
    const response = await fetch("/api/catalog");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.catalog = await response.json();
    element("version").textContent = ` / ${state.catalog.version}`;
    fillSelect(element("command"), Object.entries(state.catalog.commands), "train");
    refreshSelections();
    resetDocuments();
    renderTutorials();
    attachEvents();
    element("workspace").hidden = false;
    element("load-status").hidden = true;
    followHash();
  } catch (error) {
    element("load-status").hidden = true;
    errorBox("load-error", [`Не удалось загрузить справочник: ${error.message}`, "Проверьте установку командой cy-docs --check и перезапустите cy-docs."]);
  }
}

start();
