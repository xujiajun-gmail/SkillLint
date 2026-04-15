const i18n = {
  en: {
    eyebrow: "Skill security workstation",
    title: "Scan agent skills with SkillLint",
    subtitle:
      "Upload a directory, archive, or URL. The app calls the SkillLint scan API and renders a human-friendly report with structured output for integrations.",
    scanSetup: "Scan setup",
    scanSetupHint: "Choose an input type and review the options.",
    archiveTab: "Archive",
    directoryTab: "Directory",
    urlTab: "URL",
    archiveLabel: "Upload a zip skill package",
    directoryLabel: "Upload a local skill directory",
    directoryHint: "The browser sends all files plus their relative paths.",
    urlLabel: "Remote archive or git repository URL",
    reportLanguageLabel: "Report language",
    autoOption: "auto",
    useDataflow: "Enable dataflow analysis",
    useLlm: "Enable optional LLM semantic review",
    scanButton: "Start scan",
    scanHint: "Results stay in your browser session.",
    validationTitle: "Input checks",
    validationArchive1: "The archive must unpack into a skill package with a SKILL.md entry.",
    validationArchive2: "Unsafe zip paths, symlink entries, over-deep paths, and oversized payloads are rejected.",
    validationArchive3: "The extracted file count must not exceed 1000.",
    validationDirectory1: "The selected directory must look like a skill root, or contain a single wrapped skill directory.",
    validationDirectory2: "The normalized file count must not exceed 1000.",
    validationDirectory3: "Very large files, deep paths, and oversized directory payloads are rejected.",
    validationUrl1: "Remote input is downloaded with size limits before scan starts.",
    validationUrl2: "Downloaded archives and extracted content must still pass the same skill-package checks.",
    validationUrl3: "Very large downloads, invalid archives, and non-skill content are rejected early.",
    reportTitle: "Analysis report",
    reportHint: "Human-readable report with structured findings and source locations.",
    copyMarkdown: "Copy Markdown",
    copyJson: "Copy JSON",
    emptyTitle: "No scan yet",
    emptyBody: "Run a scan to view the summary, findings, source snippets, Markdown report, and raw JSON.",
    loadingText: "Scanning skill package and building the report…",
    tabReport: "Report",
    tabMarkdown: "Markdown",
    tabJson: "JSON",
    summarySection: "Summary",
    findingsSection: "Findings",
    sourceSection: "Source location",
    verdict: "Verdict",
    risk: "Risk",
    scoreRisk: "Score risk",
    findings: "Findings",
    score: "Score",
    files: "Files",
    taxonomy: "Taxonomy",
    engines: "Engines",
    sourceLanguage: "Source language",
    target: "Target",
    targetType: "Target type",
    correlation: "Correlation",
    criticalHigh: "critical/high",
    field: "Field",
    value: "Value",
    selectedFinding: "Selected finding",
    lineRange: "Line range",
    explanation: "Explanation",
    remediation: "Remediation",
    noSource: "Select a finding to inspect the source location.",
    noFileLocation: "This finding does not have a file-level source location.",
    sourceUnavailable: "The original source file is unavailable in the current response.",
    snippet: "Snippet",
    truncated: "The file content is truncated for transport safety.",
    copyOk: "Copied",
    apiReady: "API ready",
    apiOffline: "API unavailable",
    errorPrefix: "Scan failed:",
    errorTitle: "Input validation failed",
    sourceTypeMissing: "Please provide a valid input for the selected source type.",
    errorMissingSkill: "The uploaded content does not look like a skill package. Make sure the actual skill root contains SKILL.md.",
    errorTooManyFiles: "The uploaded content exceeds the file-count limit. Reduce generated files, caches, or bundled dependencies.",
    errorTooLarge: "The uploaded content exceeds the size limit. Remove large artifacts or split the package.",
    errorUnsafeArchive: "The archive contains unsafe or malformed paths. Rebuild the zip from a clean skill directory.",
    errorInvalidArchive: "The uploaded archive is not a valid zip file.",
    errorPathDepth: "Some paths are too deep or too long. Flatten the package structure before scanning.",
    errorRemoteSize: "The remote URL points to content that exceeds the allowed download size.",
    errorRemoteHost: "The remote URL host is not allowed for server-side scanning.",
    errorRemoteCredentials: "Remote URLs must not contain embedded usernames or passwords."
  },
  zh: {
    eyebrow: "Skill 安全工作台",
    title: "使用 SkillLint 扫描 agent skill",
    subtitle:
      "上传目录、压缩包或 URL。网页应用会调用 SkillLint 扫描 API，并输出适合人工阅读、也适合集成的结构化结果。",
    scanSetup: "扫描配置",
    scanSetupHint: "选择输入类型并确认扫描选项。",
    archiveTab: "压缩包",
    directoryTab: "目录",
    urlTab: "URL",
    archiveLabel: "上传 zip 格式的 skill 包",
    directoryLabel: "上传本地 skill 目录",
    directoryHint: "浏览器会连同相对路径一起上传所有文件。",
    urlLabel: "远程压缩包或 git 仓库 URL",
    reportLanguageLabel: "报告语言",
    autoOption: "自动",
    useDataflow: "启用 dataflow 分析",
    useLlm: "启用可选的 LLM 语义复核",
    scanButton: "开始扫描",
    scanHint: "结果只保留在当前浏览器会话中。",
    validationTitle: "输入校验",
    validationArchive1: "压缩包解压后必须像一个 skill 包，并包含 SKILL.md 入口。",
    validationArchive2: "会拒绝不安全 zip 路径、symlink entry、过深路径和超大展开内容。",
    validationArchive3: "解压后的文件总数不能超过 1000。",
    validationDirectory1: "所选目录必须像一个 skill 根目录，或只包裹了单个 skill 子目录。",
    validationDirectory2: "归一化后的文件总数不能超过 1000。",
    validationDirectory3: "会拒绝超大文件、过深路径和整体体积过大的目录。",
    validationUrl1: "远程输入会先在大小限制下下载，再进入扫描。",
    validationUrl2: "下载后的压缩包及解压结果仍需通过同样的 skill 包校验。",
    validationUrl3: "超大下载、无效压缩包和非 skill 内容会被提前拒绝。",
    reportTitle: "分析报告",
    reportHint: "适合人工阅读的报告，同时保留结构化 finding 与源码定位。",
    copyMarkdown: "复制 Markdown",
    copyJson: "复制 JSON",
    emptyTitle: "还没有扫描结果",
    emptyBody: "执行一次扫描后，这里会显示摘要、finding、源码片段、Markdown 报告和原始 JSON。",
    loadingText: "正在扫描 skill 并生成报告……",
    tabReport: "结构化报告",
    tabMarkdown: "Markdown",
    tabJson: "JSON",
    summarySection: "摘要",
    findingsSection: "风险发现",
    sourceSection: "源码定位",
    verdict: "结论",
    risk: "风险等级",
    scoreRisk: "评分风险",
    findings: "发现数量",
    score: "分数",
    files: "涉及文件",
    taxonomy: "Taxonomy",
    engines: "启用引擎",
    sourceLanguage: "源码语言",
    target: "扫描目标",
    targetType: "目标类型",
    correlation: "相关性",
    criticalHigh: "critical/high",
    field: "字段",
    value: "值",
    selectedFinding: "当前选中 finding",
    lineRange: "行号区间",
    explanation: "原因说明",
    remediation: "修复建议",
    noSource: "点击左侧 finding 后，可以在这里查看源码定位。",
    noFileLocation: "这个 finding 没有文件级源码定位信息。",
    sourceUnavailable: "当前响应中没有返回对应的原始源码文件。",
    snippet: "片段",
    truncated: "为避免传输过大，文件内容已截断。",
    copyOk: "已复制",
    apiReady: "API 可用",
    apiOffline: "API 不可用",
    errorPrefix: "扫描失败：",
    errorTitle: "输入校验未通过",
    sourceTypeMissing: "请先为当前输入类型提供有效内容。",
    errorMissingSkill: "上传内容看起来不像 skill 包。请确认真正的 skill 根目录下包含 SKILL.md。",
    errorTooManyFiles: "上传内容超过文件数限制。请移除缓存、构建产物或无关依赖文件。",
    errorTooLarge: "上传内容超过大小限制。请移除大文件或拆分包内容。",
    errorUnsafeArchive: "压缩包中包含不安全或异常路径。请从干净的 skill 目录重新打包。",
    errorInvalidArchive: "上传的压缩包不是有效 zip 文件。",
    errorPathDepth: "部分路径过深或过长。请先扁平化目录结构后再扫描。",
    errorRemoteSize: "远程 URL 指向的内容超过允许的下载大小。",
    errorRemoteHost: "远程 URL 的主机不允许由服务端扫描访问。",
    errorRemoteCredentials: "远程 URL 不能包含内嵌用户名或密码。"
  }
};

const state = {
  // UI 层只维护最小状态：
  // 当前界面语言、当前输入模式、最近一次扫描响应、当前选中 finding。
  uiLanguage: navigator.language && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en",
  sourceType: "archive",
  response: null,
  selectedFindingId: null
};

const INPUT_LIMITS = {
  maxArchiveBytes: 100 * 1024 * 1024,
  maxInputFiles: 1000,
  maxSingleFileBytes: 20 * 1024 * 1024,
  maxTotalInputBytes: 200 * 1024 * 1024,
  maxPathDepth: 20,
  maxPathLength: 240
};

const els = {
  healthChip: document.getElementById("healthChip"),
  scanForm: document.getElementById("scanForm"),
  archiveFile: document.getElementById("archiveFile"),
  directoryFiles: document.getElementById("directoryFiles"),
  urlInput: document.getElementById("urlInput"),
  reportLanguage: document.getElementById("reportLanguage"),
  useDataflow: document.getElementById("useDataflow"),
  useLlm: document.getElementById("useLlm"),
  emptyState: document.getElementById("emptyState"),
  loadingState: document.getElementById("loadingState"),
  errorState: document.getElementById("errorState"),
  reportView: document.getElementById("reportView"),
  summaryGrid: document.getElementById("summaryGrid"),
  summaryTable: document.getElementById("summaryTable"),
  findingsList: document.getElementById("findingsList"),
  sourceViewer: document.getElementById("sourceViewer"),
  markdownView: document.getElementById("markdownView"),
  jsonView: document.getElementById("jsonView"),
  copyMarkdownBtn: document.getElementById("copyMarkdownBtn"),
  copyJsonBtn: document.getElementById("copyJsonBtn"),
  validationTitle: document.getElementById("validationTitle"),
  validationChecklist: document.getElementById("validationChecklist")
};

document.querySelectorAll("[data-lang-ui]").forEach((button) => {
  button.addEventListener("click", () => {
    state.uiLanguage = button.dataset.langUi;
    renderLanguage();
    renderReport();
  });
});

document.querySelectorAll(".source-btn").forEach((button) => {
  // 扫描输入模式（zip / directory / url）切换时，统一走 setSourceType，
  // 避免显示逻辑散落在多个事件处理器里。
  button.addEventListener("click", () => setSourceType(button.dataset.source));
});

document.querySelectorAll(".tab-btn").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((item) => item.classList.toggle("is-active", item === button));
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.reportPanel === button.dataset.reportTab);
    });
  });
});

els.copyMarkdownBtn.addEventListener("click", async () => {
  if (!state.response) return;
  await navigator.clipboard.writeText(state.response.report_markdown);
  toast(i18n[state.uiLanguage].copyOk);
});

els.copyJsonBtn.addEventListener("click", async () => {
  if (!state.response) return;
  await navigator.clipboard.writeText(JSON.stringify(state.response.scan_result, null, 2));
  toast(i18n[state.uiLanguage].copyOk);
});

els.scanForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  try {
    // 先抓取当前表单内容，再进入 loading；
    // 否则某些浏览器在禁用 file input 后会丢失已选目录/文件。
    const responsePromise = submitScan();
    setLoading(true);
    const response = await responsePromise;
    state.response = response;
    state.selectedFindingId = response.scan_result.findings[0]?.id ?? null;
    renderReport();
  } catch (error) {
    error.message = `${i18n[state.uiLanguage].errorPrefix} ${error.message}`;
    showError(error);
  } finally {
    setLoading(false);
  }
});

async function submitScan() {
  // 以当前激活 tab 为准重新确认 sourceType，避免 state 与实际 UI 不一致。
  const activeSource = document.querySelector(".source-btn.is-active")?.dataset.source || state.sourceType;
  state.sourceType = activeSource;
  const options = {
    language: els.reportLanguage.value,
    use_dataflow: els.useDataflow.checked,
    use_llm: els.useLlm.checked
  };

  if (state.sourceType === "url") {
    if (!els.urlInput.value.trim()) {
      throw new Error(i18n[state.uiLanguage].sourceTypeMissing);
    }
    validateUrlBeforeSubmit(els.urlInput.value.trim());
    const response = await fetch("/api/scan/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...options, url: els.urlInput.value.trim() })
    });
    return parseApiResponse(response);
  }

  if (state.sourceType === "archive") {
    const file = els.archiveFile.files[0];
    if (!file) {
      throw new Error(i18n[state.uiLanguage].sourceTypeMissing);
    }
    validateArchiveBeforeSubmit(file);
    const form = new FormData();
    form.append("file", file);
    Object.entries(options).forEach(([key, value]) => form.append(key, String(value)));
    const response = await fetch("/api/scan/archive", { method: "POST", body: form });
    return parseApiResponse(response);
  }

  const files = Array.from(els.directoryFiles.files || []);
  if (!files.length) {
    throw new Error(i18n[state.uiLanguage].sourceTypeMissing);
  }
  validateDirectoryBeforeSubmit(files);
  const form = new FormData();
  const relativePaths = [];
  files.forEach((file) => {
    const relativePath = file.webkitRelativePath || file.name;
    form.append("files", file, relativePath);
    relativePaths.push(relativePath);
  });
  form.append("relative_paths", JSON.stringify(relativePaths));
  Object.entries(options).forEach(([key, value]) => form.append(key, String(value)));
  const response = await fetch("/api/scan/directory", { method: "POST", body: form });
  return parseApiResponse(response);
}

function validateArchiveBeforeSubmit(file) {
  const name = file.name || "";
  if (!name.toLowerCase().endsWith(".zip")) {
    throw makeValidationError("invalid_archive", i18n[state.uiLanguage].errorInvalidArchive);
  }
  if (file.size > INPUT_LIMITS.maxArchiveBytes) {
    throw makeValidationError(
      "archive_too_large",
      `${i18n[state.uiLanguage].errorTooLarge} (${formatBytes(file.size)} > ${formatBytes(INPUT_LIMITS.maxArchiveBytes)})`
    );
  }
}

function validateDirectoryBeforeSubmit(files) {
  if (files.length > INPUT_LIMITS.maxInputFiles) {
    throw makeValidationError(
      "too_many_files",
      `${i18n[state.uiLanguage].errorTooManyFiles} (${files.length} > ${INPUT_LIMITS.maxInputFiles})`,
      { file_count: files.length, max_input_files: INPUT_LIMITS.maxInputFiles }
    );
  }

  let totalBytes = 0;
  let hasSkillEntry = false;
  for (const file of files) {
    const rel = normalizeClientPath(file.webkitRelativePath || file.name);
    const parts = rel.split("/").filter(Boolean);
    if (parts.at(-1) === "SKILL.md") {
      hasSkillEntry = true;
    }
    if (rel.length > INPUT_LIMITS.maxPathLength) {
      throw makeValidationError("path_too_long", `${i18n[state.uiLanguage].errorPathDepth} (${rel.length} > ${INPUT_LIMITS.maxPathLength})`, {
        path: rel,
        path_length: rel.length,
        max_path_length: INPUT_LIMITS.maxPathLength
      });
    }
    if (parts.length > INPUT_LIMITS.maxPathDepth) {
      throw makeValidationError("path_too_deep", `${i18n[state.uiLanguage].errorPathDepth} (${parts.length} > ${INPUT_LIMITS.maxPathDepth})`, {
        path: rel,
        path_depth: parts.length,
        max_path_depth: INPUT_LIMITS.maxPathDepth
      });
    }
    if (file.size > INPUT_LIMITS.maxSingleFileBytes) {
      throw makeValidationError(
        "file_too_large",
        `${i18n[state.uiLanguage].errorTooLarge} (${rel}: ${formatBytes(file.size)} > ${formatBytes(INPUT_LIMITS.maxSingleFileBytes)})`,
        { path: rel, file_size: file.size, max_single_file_bytes: INPUT_LIMITS.maxSingleFileBytes }
      );
    }
    totalBytes += file.size;
    if (totalBytes > INPUT_LIMITS.maxTotalInputBytes) {
      throw makeValidationError(
        "input_too_large",
        `${i18n[state.uiLanguage].errorTooLarge} (${formatBytes(totalBytes)} > ${formatBytes(INPUT_LIMITS.maxTotalInputBytes)})`,
        { total_bytes: totalBytes, max_total_input_bytes: INPUT_LIMITS.maxTotalInputBytes }
      );
    }
  }

  if (!hasSkillEntry) {
    throw makeValidationError("missing_skill_entry", i18n[state.uiLanguage].errorMissingSkill);
  }
}

function validateUrlBeforeSubmit(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch (_error) {
    throw makeValidationError("invalid_remote_url", i18n[state.uiLanguage].sourceTypeMissing);
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw makeValidationError("unsupported_remote_scheme", i18n[state.uiLanguage].errorRemoteHost);
  }
  if (parsed.username || parsed.password) {
    throw makeValidationError("remote_credentials_not_allowed", i18n[state.uiLanguage].errorRemoteCredentials);
  }
  const host = parsed.hostname.toLowerCase();
  if (isUnsafeClientRemoteHost(host)) {
    throw makeValidationError("unsafe_remote_host", `${i18n[state.uiLanguage].errorRemoteHost} (${host})`, { host });
  }
}

function isUnsafeClientRemoteHost(host) {
  if (!host) return true;
  if (host === "localhost" || host.endsWith(".local")) return true;
  if (host === "::1" || host === "[::1]") return true;
  if (["169.254.169.254", "100.100.100.200"].includes(host)) return true;
  const ipv4Match = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!ipv4Match) return false;
  const octets = ipv4Match.slice(1).map((value) => Number(value));
  if (octets.some((value) => Number.isNaN(value) || value < 0 || value > 255)) return true;
  const [a, b] = octets;
  return (
    a === 10 ||
    a === 127 ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 169 && b === 254) ||
    a === 0
  );
}

function normalizeClientPath(path) {
  return String(path || "")
    .replaceAll("\\", "/")
    .split("/")
    .filter((part) => part && part !== "." && part !== "..")
    .join("/");
}

function makeValidationError(code, message, metadata = {}) {
  const error = new Error(message);
  error.code = code;
  error.metadata = metadata;
  return error;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units.shift();
  while (value >= 1024 && units.length) {
    value /= 1024;
    unit = units.shift();
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit}`;
}

async function parseApiResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.detail;
    if (detail && typeof detail === "object") {
      const error = new Error(detail.message || response.statusText);
      error.code = detail.code || "bad_request";
      error.metadata = detail.metadata || {};
      throw error;
    }
    throw new Error(detail || response.statusText);
  }
  return payload;
}

function renderLanguage() {
  const dict = i18n[state.uiLanguage];
  document.documentElement.lang = state.uiLanguage;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.dataset.i18n;
    if (dict[key]) node.textContent = dict[key];
  });
  document.querySelectorAll("[data-lang-ui]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.langUi === state.uiLanguage);
  });
  els.reportLanguage.querySelector('option[value="auto"]').textContent = dict.autoOption;
  if (els.validationTitle) {
    els.validationTitle.textContent = dict.validationTitle;
  }
  renderValidationChecklist();
}

function setSourceType(sourceType) {
  state.sourceType = sourceType;
  document.querySelectorAll(".source-btn").forEach((item) => {
    item.classList.toggle("is-active", item.dataset.source === sourceType);
  });
  document.querySelectorAll(".source-pane").forEach((pane) => {
    const isActive = pane.dataset.pane === sourceType;
    pane.classList.toggle("is-active", isActive);
    pane.hidden = !isActive;
    // 加一层内联 display 控制，避免样式缓存或 class 覆盖导致多个 pane 同时显示。
    pane.style.display = isActive ? "grid" : "none";
  });
  renderValidationChecklist();
}

function renderValidationChecklist() {
  if (!els.validationChecklist) return;
  const dict = i18n[state.uiLanguage];
  const itemsByType = {
    archive: [dict.validationArchive1, dict.validationArchive2, dict.validationArchive3],
    directory: [dict.validationDirectory1, dict.validationDirectory2, dict.validationDirectory3],
    url: [dict.validationUrl1, dict.validationUrl2, dict.validationUrl3]
  };
  const items = itemsByType[state.sourceType] || [];
  els.validationChecklist.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderReport() {
  if (!state.response) {
    els.emptyState.classList.remove("hidden");
    els.reportView.classList.add("hidden");
    return;
  }
  els.emptyState.classList.add("hidden");
  els.reportView.classList.remove("hidden");

  renderSummaryCards();
  renderSummaryTable();
  renderFindings();
  renderSourceViewer();
  els.markdownView.textContent = state.response.report_markdown;
  els.jsonView.textContent = JSON.stringify(state.response.scan_result, null, 2);
}

function renderSummaryCards() {
  const { summary } = state.response.scan_result;
  const dict = i18n[state.uiLanguage];
  const cards = [
    { label: dict.verdict, value: summary.verdict, subvalue: `${dict.risk}: ${summary.risk_level}` },
    { label: dict.scoreRisk, value: summary.score_risk_level, subvalue: `${dict.score}: ${summary.aggregate_score}` },
    { label: dict.findings, value: String(summary.finding_count), subvalue: `${dict.criticalHigh}: ${summary.critical} / ${summary.high}` },
    { label: dict.files, value: String(summary.distinct_files), subvalue: `${dict.taxonomy}: ${summary.distinct_taxonomies}` },
    {
      label: dict.correlation,
      value: String(summary.correlation_count),
      subvalue: `base ${summary.base_score} + corr ${summary.correlation_score}`
    }
  ];
  els.summaryGrid.innerHTML = cards
    .map(
      (item) => `
        <article class="summary-card">
          <p class="label">${escapeHtml(item.label)}</p>
          <p class="value">${escapeHtml(item.value)}</p>
          <p class="subvalue">${escapeHtml(item.subvalue)}</p>
        </article>
      `
    )
    .join("");
}

function renderSummaryTable() {
  const result = state.response.scan_result;
  const dict = i18n[state.uiLanguage];
  const rows = [
    [dict.verdict, result.summary.verdict],
    [dict.risk, result.summary.risk_level],
    [dict.scoreRisk, result.summary.score_risk_level],
    [dict.findings, String(result.summary.finding_count)],
    [dict.score, String(result.summary.aggregate_score)],
    [dict.engines, (result.metadata.enabled_engines || []).join(", ") || "-"],
    [dict.sourceLanguage, result.metadata.source_language || "-"],
    [dict.target, result.target.raw],
    [dict.targetType, result.target.normalized_type]
  ];
  els.summaryTable.innerHTML = renderTable([dict.field, dict.value], rows);
}

function renderFindings() {
  const dict = i18n[state.uiLanguage];
  const findings = state.response.scan_result.findings;
  els.findingsList.innerHTML = findings
    .map((finding) => {
      const selected = finding.id === state.selectedFindingId;
      const location = finding.evidence.file ? `${finding.evidence.file}:${finding.evidence.line_start || "?"}` : "repository";
      return `
        <article class="finding-card ${selected ? "is-active" : ""}" data-finding-id="${finding.id}">
          <div class="finding-head">
            <h4>${escapeHtml(finding.title)}</h4>
            <span class="severity-pill severity-${finding.severity}">${escapeHtml(finding.severity)}</span>
          </div>
          <div class="finding-meta">
            <span class="chip">${escapeHtml(finding.rule_id)}</span>
            <span class="chip">${escapeHtml(finding.primary_taxonomy || "unmapped")}</span>
            <span class="chip">${escapeHtml(location)}</span>
            <span class="chip">${escapeHtml(finding.engine)}</span>
          </div>
          <p>${escapeHtml(finding.explanation || finding.remediation || "")}</p>
        </article>
      `;
    })
    .join("");

  els.findingsList.querySelectorAll("[data-finding-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedFindingId = node.dataset.findingId;
      renderFindings();
      renderSourceViewer();
    });
  });
  if (!findings.length) {
    els.findingsList.innerHTML = `<div class="source-empty">${escapeHtml(dict.emptyBody)}</div>`;
  }
}

function renderSourceViewer() {
  const dict = i18n[state.uiLanguage];
  const finding = state.response.scan_result.findings.find((item) => item.id === state.selectedFindingId);
  if (!finding) {
    els.sourceViewer.innerHTML = `<div class="source-empty">${escapeHtml(dict.noSource)}</div>`;
    return;
  }

  if (!finding.evidence.file) {
    // 某些 finding 是仓库级或语义级命中，没有文件定位，这时退化为详情面板而不是空白。
    els.sourceViewer.innerHTML = renderFindingFallback(finding, dict.noFileLocation);
    return;
  }

  const source = state.response.source_files[finding.evidence.file];
  if (!source) {
    els.sourceViewer.innerHTML = renderFindingFallback(
      finding,
      `${dict.sourceUnavailable} (${finding.evidence.file})`
    );
    return;
  }

  const lines = source.content.split("\n");
  const lineStart = finding.evidence.line_start || 1;
  const lineEnd = finding.evidence.line_end || lineStart;
  const html = lines
    .map((line, index) => {
      const lineNo = index + 1;
      const highlighted = lineNo >= lineStart && lineNo <= lineEnd;
      const targeted = lineNo === lineStart;
      return `
        <div class="code-line ${highlighted ? "is-highlighted" : ""} ${targeted ? "is-targeted" : ""}" data-line-no="${lineNo}">
          <span class="line-no">${lineNo}</span>
          <span class="line-text">${escapeHtml(line || " ")}</span>
        </div>
      `;
    })
    .join("");

  els.sourceViewer.innerHTML = `
    <div class="source-header">
      <div>
        <strong>${escapeHtml(finding.evidence.file)}</strong>
        <div class="muted">${escapeHtml(finding.title)}</div>
      </div>
      <div class="source-meta">
        <span class="chip">${escapeHtml(dict.lineRange)}</span>
        <span class="chip">${escapeHtml(`${lineStart}-${lineEnd}`)}</span>
      </div>
    </div>
    ${finding.explanation ? `<p><strong>${escapeHtml(dict.explanation)}:</strong> ${escapeHtml(finding.explanation)}</p>` : ""}
    ${finding.remediation ? `<p><strong>${escapeHtml(dict.remediation)}:</strong> ${escapeHtml(finding.remediation)}</p>` : ""}
    ${source.truncated ? `<p class="muted">${escapeHtml(dict.truncated)}</p>` : ""}
    <div class="source-code" id="sourceCodeBlock">${html}</div>
  `;

  scrollSourceToFinding(lineStart);
}

function scrollSourceToFinding(lineStart) {
  const container = document.getElementById("sourceCodeBlock");
  const targetLine = container?.querySelector(`[data-line-no="${lineStart}"]`);
  if (!container || !targetLine) return;
  requestAnimationFrame(() => {
    // 尽量把目标行滚到视口中间，用户更容易同时看到上下文。
    const desiredTop = Math.max(
      0,
      targetLine.offsetTop - container.clientHeight / 2 + targetLine.clientHeight / 2
    );
    container.scrollTo({ top: desiredTop, behavior: "smooth" });
  });
}

function renderFindingFallback(finding, message) {
  // 当拿不到完整源码文件时，仍尽量把 finding 的关键信息和 snippet 展示给用户。
  const dict = i18n[state.uiLanguage];
  const snippet = finding.evidence?.snippet;
  const location = finding.evidence?.file
    ? `${finding.evidence.file}:${finding.evidence.line_start || "?"}`
    : "repository";
  return `
    <div class="source-header">
      <div>
        <strong>${escapeHtml(finding.title)}</strong>
        <div class="muted">${escapeHtml(location)}</div>
      </div>
      <div class="source-meta">
        <span class="chip">${escapeHtml(finding.severity)}</span>
        <span class="chip">${escapeHtml(finding.engine)}</span>
        <span class="chip">${escapeHtml(finding.rule_id)}</span>
      </div>
    </div>
    <p class="muted">${escapeHtml(message)}</p>
    ${finding.explanation ? `<p><strong>${escapeHtml(dict.explanation)}:</strong> ${escapeHtml(finding.explanation)}</p>` : ""}
    ${finding.remediation ? `<p><strong>${escapeHtml(dict.remediation)}:</strong> ${escapeHtml(finding.remediation)}</p>` : ""}
    ${snippet ? `<pre class="code-block"><strong>${escapeHtml(dict.snippet)}:</strong>\n${escapeHtml(snippet)}</pre>` : ""}
  `;
}

function renderTable(headers, rows) {
  return `
    <table>
      <thead>
        <tr>${headers.map((item) => `<th>${escapeHtml(item)}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) =>
              `<tr>${row
                .map((cell) => `<td>${escapeHtml(cell)}</td>`)
                .join("")}</tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function setLoading(isLoading) {
  els.loadingState.classList.toggle("hidden", !isLoading);
  els.scanForm.querySelectorAll("button,input,select").forEach((node) => {
    node.disabled = isLoading;
  });
}

function showError(errorLike) {
  const error = typeof errorLike === "string" ? { message: errorLike } : errorLike;
  const explanation = explainValidationError(error);
  const suggestions = explanation.suggestions.length
    ? `<ul class="error-list">${explanation.suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";
  els.errorState.innerHTML = `
    <h3>${escapeHtml(i18n[state.uiLanguage].errorTitle)}</h3>
    <p>${escapeHtml(error.message || String(errorLike))}</p>
    ${explanation.summary ? `<p>${escapeHtml(explanation.summary)}</p>` : ""}
    ${suggestions}
  `;
  els.errorState.classList.remove("hidden");
}

function clearError() {
  els.errorState.classList.add("hidden");
  els.errorState.innerHTML = "";
}

function explainValidationError(error) {
  const dict = i18n[state.uiLanguage];
  const code = error.code || "";
  const lowered = String(error.message || error).toLowerCase();
  const byCode = {
    missing_skill_entry: {
      summary: dict.errorMissingSkill,
      suggestions: [dict.validationDirectory1, dict.validationArchive1, dict.validationUrl2]
    },
    missing_root_skill_entry: {
      summary: dict.errorMissingSkill,
      suggestions: [dict.validationDirectory1, dict.validationArchive1, dict.validationUrl2]
    },
    too_many_files: {
      summary: dict.errorTooManyFiles,
      suggestions: [dict.validationDirectory2, dict.validationArchive3]
    },
    archive_symlink_entry: {
      summary: dict.errorUnsafeArchive,
      suggestions: [dict.validationArchive2]
    },
    unsafe_archive_path: {
      summary: dict.errorUnsafeArchive,
      suggestions: [dict.validationArchive2]
    },
    invalid_archive: {
      summary: dict.errorInvalidArchive,
      suggestions: [dict.validationArchive1]
    },
    path_too_deep: {
      summary: dict.errorPathDepth,
      suggestions: [dict.validationDirectory3, dict.validationArchive2]
    },
    path_too_long: {
      summary: dict.errorPathDepth,
      suggestions: [dict.validationDirectory3, dict.validationArchive2]
    },
    file_too_large: {
      summary: dict.errorTooLarge,
      suggestions: [dict.validationDirectory3, dict.validationArchive2, dict.validationUrl1]
    },
    input_too_large: {
      summary: dict.errorTooLarge,
      suggestions: [dict.validationDirectory3, dict.validationArchive2, dict.validationUrl1]
    },
    archive_too_large: {
      summary: dict.errorTooLarge,
      suggestions: [dict.validationArchive2]
    },
    remote_too_large: {
      summary: dict.errorRemoteSize,
      suggestions: [dict.validationUrl1, dict.validationUrl3]
    },
    remote_credentials_not_allowed: {
      summary: dict.errorRemoteCredentials,
      suggestions: [dict.validationUrl1]
    },
    unsafe_remote_host: {
      summary: dict.errorRemoteHost,
      suggestions: [dict.validationUrl1]
    },
    too_many_redirects: {
      summary: dict.errorRemoteSize,
      suggestions: [dict.validationUrl1, dict.validationUrl3]
    }
  };
  if (code && byCode[code]) return byCode[code];
  if (
    lowered.includes("no skill.md") ||
    lowered.includes("root skill.md is missing") ||
    lowered.includes("not a skill")
  ) {
    return {
      summary: dict.errorMissingSkill,
      suggestions: [dict.validationDirectory1, dict.validationArchive1, dict.validationUrl2]
    };
  }
  if (lowered.includes("too many files") || lowered.includes("maximum number of files")) {
    return {
      summary: dict.errorTooManyFiles,
      suggestions: [dict.validationDirectory2, dict.validationArchive3]
    };
  }
  if (lowered.includes("unsafe path traversal") || lowered.includes("symlink entry")) {
    return {
      summary: dict.errorUnsafeArchive,
      suggestions: [dict.validationArchive2]
    };
  }
  if (lowered.includes("invalid zip archive")) {
    return {
      summary: dict.errorInvalidArchive,
      suggestions: [dict.validationArchive1]
    };
  }
  if (lowered.includes("too deep") || lowered.includes("too long")) {
    return {
      summary: dict.errorPathDepth,
      suggestions: [dict.validationDirectory3, dict.validationArchive2]
    };
  }
  if (
    lowered.includes("too large") ||
    lowered.includes("file is too large") ||
    lowered.includes("bytes >")
  ) {
    return {
      summary: lowered.includes("remote") ? dict.errorRemoteSize : dict.errorTooLarge,
      suggestions: [dict.validationDirectory3, dict.validationArchive2, dict.validationUrl1]
    };
  }
  return { summary: "", suggestions: [] };
}

function toast(message) {
  els.healthChip.textContent = message;
  setTimeout(syncHealthChip, 1200);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function syncHealthChip() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("bad response");
    els.healthChip.textContent = i18n[state.uiLanguage].apiReady;
  } catch (_error) {
    els.healthChip.textContent = i18n[state.uiLanguage].apiOffline;
  }
}

renderLanguage();
setSourceType(state.sourceType);
syncHealthChip();
