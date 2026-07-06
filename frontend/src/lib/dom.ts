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

