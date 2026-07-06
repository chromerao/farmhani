// 디자인 HTML 주입 문서(doc)를 다루는 순수 DOM 유틸리티
export function normalizedText(element: Element | null) {
  return (element?.textContent ?? "").replace(/\s+/g, " ").trim();
}

export function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function frameAlert(doc: Document, message: string) {
  doc.defaultView?.alert(message);
}

export function createHiddenFileInput(doc: Document) {
  const input = doc.createElement("input");
  input.type = "file";
  input.accept = "image/png,image/jpeg,image/webp";
  input.style.display = "none";
  doc.body.appendChild(input);
  return input;
}

export function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function removeCategoryAddButtons(doc: Document) {
  doc.querySelectorAll("button").forEach((button) => {
    const text = normalizedText(button);
    if (text.includes("카테고리 추가") || text.includes("새 카테고리")) {
      button.remove();
    }
  });
}

export function removeChatConfidence(doc: Document) {
  Array.from(doc.querySelectorAll("p, span")).forEach((element) => {
    const text = normalizedText(element);
    if (text.includes("분석 확신도") || (text.includes("87%") && text.includes("확신"))) {
      element.remove();
    }
  });
}

export function simplifyDashboardViewButtons(doc: Document) {
  const listButton = Array.from(doc.querySelectorAll("button")).find((button) => normalizedText(button).includes("view_list"));
  listButton?.remove();

  const gridButton = Array.from(doc.querySelectorAll("button")).find((button) => normalizedText(button).includes("grid_view")) as HTMLElement | undefined;
  if (!gridButton || gridButton.dataset.viewButtonsSimplified === "true") return;
  gridButton.dataset.viewButtonsSimplified = "true";
  gridButton.setAttribute("title", "카드 보기");
  gridButton.addEventListener("click", (event) => {
    event.preventDefault();
  });
}

export function removeAddPhotoSkipButton(doc: Document) {
  doc.getElementById("skip-btn")?.remove();
}

export function findPlantGrid(doc: Document) {
  const plantSection = Array.from(doc.querySelectorAll("section")).find((section) => {
    const heading = section.querySelector("h2");
    return normalizedText(heading).includes("내 식물");
  });
  const preciseGrid = plantSection?.querySelector(".grid");
  if (preciseGrid) return preciseGrid as HTMLElement;

  return Array.from(doc.querySelectorAll(".grid")).find((element) => {
    const text = normalizedText(element);
    return text.includes("새 식물 추가") && (text.includes("몬스테라") || text.includes("내 식물"));
  }) as HTMLElement | undefined;
}


export function showFormModal(
  doc: Document,
  options: {
    title: string;
    description: string;
    submitLabel: string;
    fields: { key: string; label: string; value?: string; placeholder?: string; required?: boolean }[];
  },
  onSubmit: (values: Record<string, string>) => void
) {
  doc.querySelector("[data-app-modal]")?.remove();
  const overlay = doc.createElement("div");
  overlay.dataset.appModal = "true";
  overlay.className = "fixed inset-0 z-[999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4";
  overlay.innerHTML = `<div class="w-full max-w-md bg-surface-container-lowest rounded-2xl shadow-2xl border border-outline-variant/20 p-6 space-y-5 max-h-[90vh] overflow-y-auto">
    <div>
      <p class="text-label-sm font-bold text-primary uppercase tracking-wide">Farm하니 기록</p>
      <h3 class="text-headline-md font-bold text-on-surface mt-1">${escapeHtml(options.title)}</h3>
      <p class="text-body-md text-on-surface-variant mt-2">${escapeHtml(options.description)}</p>
    </div>
    <div class="space-y-3">
      ${options.fields
        .map(
          (field) => `<label class="block">
        <span class="text-label-sm font-bold text-on-surface-variant">${escapeHtml(field.label)}${field.required ? ' <span class="text-diagnostic-red">*</span>' : ""}</span>
        <input type="text" data-form-field="${escapeHtml(field.key)}" value="${escapeHtml(field.value ?? "")}" placeholder="${escapeHtml(field.placeholder ?? "")}"
          class="mt-1 w-full rounded-xl bg-surface-container border border-outline-variant/20 focus:ring-2 focus:ring-primary p-3 text-body-md" />
      </label>`
        )
        .join("")}
    </div>
    <div class="flex justify-end gap-2">
      <button class="px-4 py-2 rounded-lg text-on-surface-variant hover:bg-surface-container" data-modal-cancel="true">취소</button>
      <button class="px-5 py-2 rounded-lg bg-primary text-white font-bold shadow-sm" data-modal-submit="true">${escapeHtml(options.submitLabel)}</button>
    </div>
  </div>`;
  doc.body.appendChild(overlay);
  const firstInput = overlay.querySelector("input[data-form-field]") as HTMLInputElement | null;
  firstInput?.focus();
  overlay.querySelector("[data-modal-cancel]")?.addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) overlay.remove();
  });
  overlay.querySelector("[data-modal-submit]")?.addEventListener("click", () => {
    const values: Record<string, string> = {};
    let missingRequired = false;
    options.fields.forEach((field) => {
      const input = overlay.querySelector(`input[data-form-field="${field.key}"]`) as HTMLInputElement | null;
      const value = input?.value.trim() ?? "";
      values[field.key] = value;
      if (field.required && !value) {
        missingRequired = true;
        input?.focus();
      }
    });
    if (missingRequired) return;
    overlay.remove();
    onSubmit(values);
  });
}

export function showTextInputModal(
  doc: Document,
  options: { title: string; description: string; placeholder: string; submitLabel: string },
  onSubmit: (value: string) => void
) {
  doc.querySelector("[data-app-modal]")?.remove();
  const overlay = doc.createElement("div");
  overlay.dataset.appModal = "true";
  overlay.className = "fixed inset-0 z-[999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4";
  overlay.innerHTML = `<div class="w-full max-w-md bg-surface-container-lowest rounded-2xl shadow-2xl border border-outline-variant/20 p-6 space-y-5">
    <div>
      <p class="text-label-sm font-bold text-primary uppercase tracking-wide">Farm하니 기록</p>
      <h3 class="text-headline-md font-bold text-on-surface mt-1">${escapeHtml(options.title)}</h3>
      <p class="text-body-md text-on-surface-variant mt-2">${escapeHtml(options.description)}</p>
    </div>
    <textarea class="w-full min-h-32 rounded-xl bg-surface-container border border-outline-variant/20 focus:ring-2 focus:ring-primary p-4 text-body-md resize-none" placeholder="${escapeHtml(options.placeholder)}"></textarea>
    <div class="flex justify-end gap-2">
      <button class="px-4 py-2 rounded-lg text-on-surface-variant hover:bg-surface-container" data-modal-cancel="true">취소</button>
      <button class="px-5 py-2 rounded-lg bg-primary text-white font-bold shadow-sm" data-modal-submit="true">${escapeHtml(options.submitLabel)}</button>
    </div>
  </div>`;
  doc.body.appendChild(overlay);
  const textarea = overlay.querySelector("textarea") as HTMLTextAreaElement | null;
  textarea?.focus();
  overlay.querySelector("[data-modal-cancel]")?.addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) overlay.remove();
  });
  overlay.querySelector("[data-modal-submit]")?.addEventListener("click", () => {
    const value = textarea?.value.trim() || "";
    if (!value) {
      textarea?.focus();
      return;
    }
    overlay.remove();
    onSubmit(value);
  });
}
