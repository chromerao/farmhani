import {
  askPlantCareStream,
  getAccessToken,
  getChatModelInfo,
  hasAuthSession,
  hasSupabaseAuthConfig,
  listChatMessages,
  listChatSessions,
  submitChatFeedback,
  uploadPlantPhoto
} from "../api";
import type { ChatFeedbackRating, ChatMessage, ChatResponseMode, ChatSession, PlantCareChatResponse } from "../types";
import {
  CHAT_RESPONSE_MODE_KEY,
  PENDING_DIAGNOSIS_QUESTION_KEY,
  REFERENCE_PANE_COMPACT_KEY,
  REFERENCE_PANE_HIDDEN_KEY
} from "../lib/constants";
import { createHiddenFileInput, escapeHtml, frameAlert, normalizedText } from "../lib/dom";
import { formatDate } from "../lib/format";
import {
  appendLocalChatMemory,
  clearLastSessionId,
  getLastSessionId,
  getSelectedPlantId,
  loadLocalChatMemory,
  saveLocalChatMemory,
  setLastSessionId
} from "../lib/storage";
import type { AppContext } from "./context";

export function createChatPage(ctx: AppContext) {
  const {
    navigate,
    handleApiError,
    resolvePlantId,
    pendingChatPhotoRef,
    pendingChatPhotoNoteRef,
    forceNewChatSessionRef,
    chatResponseModeRef
  } = ctx;

  function appendUserMessage(doc: Document, text: string, file?: File | null) {
    const messages = doc.getElementById("chat-messages");
    if (!messages) return;

    const preview = file ? `<p class="mt-2 text-label-sm opacity-80">첨부 사진: ${escapeHtml(file.name)}</p>` : "";
    messages.insertAdjacentHTML(
      "beforeend",
      `<div class="flex flex-col items-end gap-2 animate-fade-in">
        <div class="max-w-[80%] bg-primary-container text-on-primary-container p-4 rounded-2xl rounded-tr-none shadow-sm">
          <p class="text-body-md">${escapeHtml(text)}</p>
          ${preview}
        </div>
        <span class="text-label-sm text-outline">방금</span>
      </div>`
    );
    messages.scrollTop = messages.scrollHeight;
  }

  function setChatAttachmentStatus(doc: Document, file?: File | null) {
    const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
    const inputBar = textarea?.closest(".relative") as HTMLElement | null;
    if (!inputBar) return;
    inputBar.querySelector("[data-chat-attachment]")?.remove();
    if (!file) return;
    const badge = doc.createElement("div");
    badge.dataset.chatAttachment = "true";
    badge.className =
      "absolute left-3 -top-10 right-3 bg-growth-light text-primary rounded-xl px-3 py-2 text-label-sm font-bold flex items-center justify-between shadow-sm border border-primary/10";
    badge.innerHTML = `<span class="flex items-center gap-2"><span class="material-symbols-outlined text-[16px]">image</span>${escapeHtml(
      file.name
    )}</span><button type="button" class="text-on-surface-variant hover:text-primary" data-clear-attachment="true">×</button>`;
    inputBar.appendChild(badge);
    badge.querySelector("[data-clear-attachment]")?.addEventListener("click", (event) => {
      event.preventDefault();
      pendingChatPhotoRef.current = null;
      pendingChatPhotoNoteRef.current = "";
      badge.remove();
    });
  }

  function setPendingChatPhoto(doc: Document, file?: File | null) {
    pendingChatPhotoRef.current = file ?? null;
    pendingChatPhotoNoteRef.current = "";
    setChatAttachmentStatus(doc, pendingChatPhotoRef.current);
    const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
    if (textarea && file && !textarea.value.trim()) {
      textarea.value = "첨부한 사진을 기준으로 현재 식물 상태를 봐줘";
      textarea.focus();
    }
  }

  function appendAssistantLoading(doc: Document) {
    const messages = doc.getElementById("chat-messages");
    if (!messages) return null;
    const isCompanionMode = chatResponseModeRef.current === "companion";
    const loadingText = isCompanionMode
      ? "내 기록이랑 공식 자료를 같이 보면서 뭐라고 말해줄지 정리하고 있어..."
      : "공식 자료와 내 식물 기록을 함께 확인하고 있습니다...";

    const wrapper = doc.createElement("div");
    wrapper.className = "flex flex-col items-start gap-2 animate-fade-in";
    wrapper.innerHTML = `<div class="flex items-start gap-3 max-w-[85%]">
      <div class="w-8 h-8 rounded-full bg-sage-accent flex-shrink-0 flex items-center justify-center">
        <span class="material-symbols-outlined text-primary text-[18px]">${isCompanionMode ? "local_florist" : "nature"}</span>
      </div>
      <div class="bg-surface-container-lowest border border-outline-variant/30 p-5 rounded-2xl rounded-tl-none shadow-sm">
        <p class="text-body-md text-on-surface">${loadingText}</p>
      </div>
    </div>`;
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
    return wrapper;
  }

  function feedbackButtonHtml(messageId: string, rating: ChatFeedbackRating, label: string, icon: string) {
    return `<button type="button" class="inline-flex items-center gap-1 rounded-full border border-outline-variant/30 px-3 py-1.5 text-label-sm text-on-surface-variant hover:border-primary hover:text-primary transition-all" data-chat-feedback="${rating}" data-message-id="${escapeHtml(messageId)}">
      <span class="material-symbols-outlined text-[16px]">${icon}</span>${label}
    </button>`;
  }

  function bindChatFeedback(doc: Document, container: HTMLElement) {
    container.querySelectorAll("[data-chat-feedback]").forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.preventDefault();
        const target = button as HTMLButtonElement;
        const rating = target.dataset.chatFeedback as ChatFeedbackRating | undefined;
        const messageId = target.dataset.messageId;
        if (!rating || !messageId) return;

        const group = target.closest("[data-feedback-group]") as HTMLElement | null;
        group?.querySelectorAll("button").forEach((item) => item.setAttribute("disabled", "true"));
        try {
          await submitChatFeedback(messageId, rating);
          group?.querySelectorAll("button").forEach((item) => {
            item.classList.toggle("border-primary", item === target);
            item.classList.toggle("text-primary", item === target);
            item.classList.toggle("bg-growth-light", item === target);
          });
          const status = group?.querySelector("[data-feedback-status]");
          if (status) status.textContent = "피드백을 저장했습니다.";
        } catch (error) {
          group?.querySelectorAll("button").forEach((item) => item.removeAttribute("disabled"));
          frameAlert(doc, `피드백 저장에 실패했습니다. ${error instanceof Error ? error.message : ""}`);
        }
      });
    });
  }

  function renderAssistantAnswer(doc: Document, wrapper: HTMLElement, answer: PlantCareChatResponse) {
    const isCompanionMode = chatResponseModeRef.current === "companion";
    const assistantIcon = isCompanionMode ? "local_florist" : "nature";
    const summaryLabel = isCompanionMode ? "식물의 한마디" : "관찰 요약";
    const causesLabel = isCompanionMode ? "내가 힘든 이유 후보" : "가능성이 있는 원인";
    const checklistLabel = isCompanionMode ? "나를 봐줄 포인트" : "다음 관찰 포인트";
    const causes = answer.possibleCauses
      .map((item) => `<span class="inline-flex rounded-full bg-surface-container px-3 py-1 text-label-sm text-on-surface-variant">${escapeHtml(item)}</span>`)
      .join("");
    const actions = answer.todayActions
      .map(
        (item, index) => `<div class="flex gap-3 rounded-xl bg-primary-container/80 text-on-primary-container p-4 shadow-sm">
          <span class="inline-flex w-7 h-7 rounded-full bg-white/30 items-center justify-center text-label-sm font-bold flex-shrink-0">${index + 1}</span>
          <p class="text-body-md font-medium">${escapeHtml(item)}</p>
        </div>`
      )
      .join("");
    const checklist = answer.observationChecklist
      .map((item) => `<li class="flex gap-2"><span class="text-primary">•</span><span>${escapeHtml(item)}</span></li>`)
      .join("");
    const citations = answer.citations
      .map((item, index) => {
        const label = escapeHtml(item.title || `참조 ${index + 1}`);
        const url = item.url ? ` href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer"` : ' href="#"';
        return `<a class="citation-link inline-flex items-center gap-1 rounded-full bg-growth-light px-2 py-1 text-primary text-[11px] font-bold"${url}>${index + 1}. ${label}</a>`;
      })
      .join(" ");
    const feedback = answer.messageId
      ? `<div class="flex flex-wrap items-center gap-2 border-t border-outline-variant/20 pt-3" data-feedback-group="true">
          <span class="text-label-sm text-outline">이 답변은 어땠나요?</span>
          ${feedbackButtonHtml(answer.messageId, "helpful", "도움됨", "thumb_up")}
          ${feedbackButtonHtml(answer.messageId, "not_helpful", "부정확", "thumb_down")}
          ${feedbackButtonHtml(answer.messageId, "unsafe", "위험함", "report")}
          <span class="text-label-sm text-primary" data-feedback-status></span>
        </div>`
      : "";

    wrapper.innerHTML = `<div class="flex items-start gap-3 max-w-[85%]">
      <div class="w-8 h-8 rounded-full bg-sage-accent flex-shrink-0 flex items-center justify-center">
        <span class="material-symbols-outlined text-primary text-[18px]">${assistantIcon}</span>
      </div>
      <div class="bg-surface-container-lowest border border-outline-variant/30 p-5 rounded-2xl rounded-tl-none shadow-sm space-y-5">
        <div class="space-y-2 border-b border-outline-variant/20 pb-4">
          <p class="text-label-sm font-bold text-primary flex items-center gap-2 uppercase tracking-wide">
            <span class="material-symbols-outlined text-[16px]">auto_awesome</span>${summaryLabel}
          </p>
          <p class="text-body-md text-on-surface leading-relaxed">${escapeHtml(answer.summary)}</p>
        </div>
        ${
          actions
            ? `<div class="space-y-3">
                <p class="text-label-lg font-bold text-primary flex items-center gap-2">
                  <span class="material-symbols-outlined text-[18px]">task_alt</span>오늘의 할 일
                </p>
                <div class="space-y-2">${actions}</div>
              </div>`
            : ""
        }
        ${
          causes
            ? `<div class="space-y-2">
                <p class="text-label-md font-bold text-on-surface">${causesLabel}</p>
                <div class="flex flex-wrap gap-2">${causes}</div>
              </div>`
            : ""
        }
        ${
          checklist
            ? `<div class="rounded-xl border border-outline-variant/20 p-3">
                <p class="text-label-md font-bold text-on-surface mb-2">${checklistLabel}</p>
                <ul class="space-y-1 text-body-md text-on-surface-variant">${checklist}</ul>
              </div>`
            : ""
        }
        ${citations ? `<div class="flex flex-wrap gap-2 pt-2">${citations}</div>` : ""}
        ${feedback}
        ${answer.safetyNotice ? `<p class="text-[11px] text-outline border-t border-outline-variant/20 pt-3">${escapeHtml(answer.safetyNotice)}</p>` : ""}
      </div>
    </div>
    <span class="text-label-sm text-outline ml-11">방금</span>`;

    bindChatFeedback(doc, wrapper);
    const messages = doc.getElementById("chat-messages");
    if (messages) messages.scrollTop = messages.scrollHeight;
  }

  function renderReferences(doc: Document, citations: PlantCareChatResponse["citations"]) {
    const pane = doc.getElementById("reference-pane");
    if (!pane) return;
    if (citations.length === 0) {
      pane.innerHTML = `<article class="bg-white p-5 rounded-lg shadow-sm border border-outline-variant/10">
        <span class="text-[10px] font-bold text-primary bg-primary-fixed px-2 py-0.5 rounded uppercase tracking-tighter">공식 문서</span>
        <h4 class="font-headline-sm text-on-surface mt-3 mb-2">이번 검색에서 표시할 출처가 없습니다.</h4>
        <p class="text-body-md text-on-surface-variant">질문을 조금 더 구체적으로 입력하면 관련 공식 문서를 다시 검색합니다.</p>
      </article>`;
      return;
    }

    pane.innerHTML = citations
      .map((item, index) => {
        const title = escapeHtml(item.title || `참조 ${index + 1}`);
        const publisher = escapeHtml(item.publisher || "공식 자료");
        const excerpt = escapeHtml(item.excerpt || "이 출처는 현재 제목과 기관 정보만 확인됩니다. 관련 본문 발췌는 문서 본문이 함께 적재된 자료부터 표시됩니다.");
        const section = item.section ? `<p class="text-label-sm text-on-surface-variant mt-1">문서 위치: ${escapeHtml(item.section)}</p>` : "";
        const link = item.url
          ? `<a class="text-label-sm text-primary hover:underline" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">원문 보기</a>`
          : "";
        return `<article class="bg-white p-5 rounded-lg shadow-sm border border-outline-variant/10 transition-all duration-500">
          <div class="flex items-center justify-between mb-3">
            <span class="text-[10px] font-bold text-primary bg-primary-fixed px-2 py-0.5 rounded uppercase tracking-tighter">참조 [${index + 1}]</span>
            <span class="text-label-sm text-outline italic">${publisher}</span>
          </div>
          <h4 class="font-headline-sm text-on-surface mb-2">${title}</h4>
          ${section}
          <p class="text-body-md text-on-surface-variant mt-3 leading-relaxed">"${excerpt}"</p>
          <div class="mt-4 pt-4 border-t border-outline-variant/10">${link}</div>
        </article>`;
      })
      .join("");
  }

  function bindReferencePaneControls(doc: Document) {
    const pane = doc.getElementById("reference-pane");
    const section = pane?.closest("section") as HTMLElement | null;
    if (!pane || !section || section.dataset.refControlsBound === "true") return;
    section.dataset.refControlsBound = "true";

    // 간략 보기 CSS: 출처 카드에서 발췌문/문서 위치를 숨겨 제목·기관만 보여준다
    if (!doc.querySelector("[data-ref-pane-style]")) {
      const style = doc.createElement("style");
      style.dataset.refPaneStyle = "true";
      style.textContent = `
        #reference-pane[data-compact="true"] article p { display: none; }
        #reference-pane[data-compact="true"] article h4 { margin-bottom: 0; }
        #reference-pane[data-compact="true"] article > div:last-child { margin-top: 8px; padding-top: 8px; }
      `;
      doc.head.appendChild(style);
    }

    const headerButtons = Array.from(section.querySelectorAll("button"));
    const compactButton = headerButtons.find((button) => normalizedText(button).includes("filter_list")) as HTMLButtonElement | undefined;
    const collapseButton = headerButtons.find((button) => normalizedText(button).includes("open_in_full")) as HTMLButtonElement | undefined;

    // 접힌 상태에서 다시 열 수 있는 플로팅 탭 (데스크톱 전용 — 모바일에서는 패널 자체가 숨김)
    const reopenButton = doc.createElement("button");
    reopenButton.type = "button";
    reopenButton.dataset.refPaneReopen = "true";
    reopenButton.className =
      "hidden lg:inline-flex fixed right-4 top-20 z-40 items-center gap-1.5 rounded-full bg-white border border-outline-variant/30 px-3 py-2 text-label-sm font-bold text-primary shadow-md hover:bg-growth-light transition-all";
    reopenButton.innerHTML = '<span class="material-symbols-outlined text-[18px]">library_books</span>출처 보기';
    doc.body.appendChild(reopenButton);

    const applyHidden = (hidden: boolean) => {
      section.style.display = hidden ? "none" : "";
      reopenButton.style.display = hidden ? "" : "none";
      localStorage.setItem(REFERENCE_PANE_HIDDEN_KEY, String(hidden));
    };
    const applyCompact = (compact: boolean) => {
      pane.dataset.compact = String(compact);
      localStorage.setItem(REFERENCE_PANE_COMPACT_KEY, String(compact));
      if (compactButton) {
        compactButton.title = compact ? "자세히 보기 (발췌문 표시)" : "간략히 보기 (제목만 표시)";
        compactButton.classList.toggle("bg-growth-light", compact);
      }
    };

    applyHidden(localStorage.getItem(REFERENCE_PANE_HIDDEN_KEY) === "true");
    applyCompact(localStorage.getItem(REFERENCE_PANE_COMPACT_KEY) === "true");

    if (collapseButton) {
      collapseButton.title = "출처 사이드바 접기";
      const icon = collapseButton.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = "right_panel_close";
      collapseButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopImmediatePropagation();
        applyHidden(true);
      });
    }
    reopenButton.addEventListener("click", (event) => {
      event.preventDefault();
      applyHidden(false);
    });

    compactButton?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      applyCompact(pane.dataset.compact !== "true");
    });
  }

  function bindChatModeSelector(doc: Document) {
    const title = Array.from(doc.querySelectorAll("h3")).find((element) => normalizedText(element).includes("상담"));
    const header =
      (title?.closest(".glass-panel") as HTMLElement | null) ||
      (Array.from(doc.querySelectorAll(".glass-panel")).find((element) => normalizedText(element).includes("Botanical Vision")) as HTMLElement | undefined) ||
      null;
    if (!header || header.querySelector("[data-chat-mode-selector]")) return;

    const selector = doc.createElement("div");
    selector.dataset.chatModeSelector = "true";
    selector.className =
      "flex items-center gap-1 bg-surface-container-low border border-outline-variant/20 rounded-full p-1 shadow-sm";
    selector.innerHTML = `
      <button type="button" class="px-3 py-1.5 rounded-full text-label-sm font-bold transition-all flex items-center gap-1" data-chat-mode="expert" title="전문가가 답변하는 차분한 상담 모드">
        <span class="material-symbols-outlined text-[15px]">psychology</span>
        <span class="hidden sm:inline">전문가</span>
      </button>
      <button type="button" class="px-3 py-1.5 rounded-full text-label-sm font-bold transition-all flex items-center gap-1" data-chat-mode="companion" title="등록한 식물이 직접 말하는 친근한 대화 모드">
        <span class="material-symbols-outlined text-[15px]">local_florist</span>
        <span class="hidden sm:inline">내 식물</span>
      </button>`;

    const rightActions = header.lastElementChild;
    header.insertBefore(selector, rightActions ?? null);

    const syncButtons = () => {
      selector.querySelectorAll("[data-chat-mode]").forEach((button) => {
        const mode = (button as HTMLElement).dataset.chatMode as ChatResponseMode;
        const selected = mode === chatResponseModeRef.current;
        button.className = selected
          ? "px-3 py-1.5 rounded-full text-label-sm font-bold transition-all flex items-center gap-1 bg-primary text-white shadow-sm"
          : "px-3 py-1.5 rounded-full text-label-sm font-bold transition-all flex items-center gap-1 text-on-surface-variant hover:bg-growth-light hover:text-primary";
      });
    };

    selector.querySelectorAll("[data-chat-mode]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const mode = (button as HTMLElement).dataset.chatMode as ChatResponseMode;
        chatResponseModeRef.current = mode === "companion" ? "companion" : "expert";
        localStorage.setItem(CHAT_RESPONSE_MODE_KEY, chatResponseModeRef.current);
        syncButtons();
        initializeChatCanvas(doc);
        setChatAttachmentStatus(doc, pendingChatPhotoRef.current);
        void renderChatSessions(doc, { autoLoadLast: true });
      });
    });
    syncButtons();
  }

  function bindChatModelInfo(doc: Document) {
    const title = Array.from(doc.querySelectorAll("h3")).find((element) => normalizedText(element).includes("상담"));
    const subtitle = title?.nextElementSibling as HTMLElement | null;
    if (!subtitle || subtitle.dataset.modelInfoBound === "true") return;

    subtitle.dataset.modelInfoBound = "true";
    subtitle.textContent = "LLM 모델 정보를 확인하는 중입니다.";
    void getChatModelInfo()
      .then((info) => {
        subtitle.textContent = `LLM: ${info.chatModel}${info.visionModel ? ` · Vision: ${info.visionModel}` : ""}`;
      })
      .catch(() => {
        subtitle.textContent = "LLM: gpt-4o-mini";
      });
  }

  function initializeChatCanvas(doc: Document) {
    const messages = doc.getElementById("chat-messages");
    const isCompanionMode = chatResponseModeRef.current === "companion";
    const icon = isCompanionMode ? "local_florist" : "nature";
    const introTitle = isCompanionMode
      ? "나랑 바로 이야기해도 돼. 잎이 축 처졌는지, 흙이 말랐는지, 오늘 기분이 어떤지 물어봐줘."
      : "식물 상태, 물주기, 빛, 흙 상태를 물어보세요. 사진을 첨부하면 사진에서 보이는 증상도 함께 참고합니다.";
    const introCaption = isCompanionMode
      ? "친근한 대화 모드지만 공식 문서와 내 관리 기록을 함께 참고해서 답합니다."
      : "확정 진단보다는 관찰 가능한 가능성과 오늘 할 일을 중심으로 안내합니다.";
    if (messages) {
      messages.innerHTML = `<div class="flex flex-col items-start gap-2 animate-fade-in">
        <div class="flex items-start gap-3 max-w-[85%]">
          <div class="w-8 h-8 rounded-full bg-sage-accent flex-shrink-0 flex items-center justify-center">
            <span class="material-symbols-outlined text-primary text-[18px]">${icon}</span>
          </div>
          <div class="bg-surface-container-lowest border border-outline-variant/30 p-5 rounded-2xl rounded-tl-none shadow-sm space-y-2">
            <p class="text-body-md text-on-surface">${introTitle}</p>
            <p class="text-label-sm text-on-surface-variant">${introCaption}</p>
          </div>
        </div>
      </div>`;
    }
    const pane = doc.getElementById("reference-pane");
    if (pane) {
      pane.innerHTML = `<article class="bg-white p-5 rounded-lg shadow-sm border border-outline-variant/10">
        <span class="text-[10px] font-bold text-primary bg-primary-fixed px-2 py-0.5 rounded uppercase tracking-tighter">공식 문서</span>
        <h4 class="font-headline-sm text-on-surface mt-3 mb-2">아직 인용된 문서가 없습니다.</h4>
        <p class="text-body-md text-on-surface-variant">상담을 시작하면 검색된 공식 문서의 제목, 기관, 관련 발췌문이 이곳에 표시됩니다.</p>
      </article>`;
    }
  }

  function parseStoredAssistantMessage(message: ChatMessage): PlantCareChatResponse | null {
    const summaryMatch = message.content.match(/\[요약\]\s*([\s\S]*?)(?:\n\n\[의심 원인\]|\n\n\[오늘 할 일\]|$)/);
    const causesMatch = message.content.match(/\[의심 원인\]\s*([\s\S]*?)(?:\n\n\[오늘 할 일\]|$)/);
    const actionsMatch = message.content.match(/\[오늘 할 일\]\s*([\s\S]*)$/);
    if (!summaryMatch && !causesMatch && !actionsMatch) return null;

    const splitLines = (value?: string) =>
      (value || "")
        .split(/\n+/)
        .map((line) => line.replace(/^[-•\d. ]+/, "").trim())
        .filter(Boolean);

    return {
      summary: summaryMatch?.[1]?.trim() || message.content,
      possibleCauses: splitLines(causesMatch?.[1]),
      todayActions: splitLines(actionsMatch?.[1]),
      observationChecklist: [],
      citations: message.citations || [],
      messageId: message.id
    };
  }

  function renderHistoryMessage(doc: Document, message: ChatMessage) {
    if (message.sender === "user") {
      appendUserMessage(doc, message.content);
      return;
    }

    const messages = doc.getElementById("chat-messages");
    if (!messages) return;
    const citations = message.citations || [];
    const parsed = parseStoredAssistantMessage(message);
    if (parsed) {
      const wrapper = doc.createElement("div");
      wrapper.className = "flex flex-col items-start gap-2 animate-fade-in";
      messages.appendChild(wrapper);
      renderAssistantAnswer(doc, wrapper, parsed);
      renderReferences(doc, citations);
      return;
    }
    messages.insertAdjacentHTML(
      "beforeend",
      `<div class="flex flex-col items-start gap-2 animate-fade-in">
        <div class="flex items-start gap-3 max-w-[85%]">
          <div class="w-8 h-8 rounded-full bg-sage-accent flex-shrink-0 flex items-center justify-center">
            <span class="material-symbols-outlined text-primary text-[18px]">nature</span>
          </div>
          <div class="bg-surface-container-lowest border border-outline-variant/30 p-5 rounded-2xl rounded-tl-none shadow-sm whitespace-pre-line">
            ${escapeHtml(message.content)}
          </div>
        </div>
      </div>`
    );
    renderReferences(doc, citations);
  }

  async function loadChatMessages(doc: Document, sessionId: string) {
    try {
      const messages = await listChatMessages(sessionId);
      const container = doc.getElementById("chat-messages");
      if (container) container.innerHTML = "";
      renderReferences(doc, []);
      messages.forEach((message) => renderHistoryMessage(doc, message));
      forceNewChatSessionRef.current = false;
      setLastSessionId(sessionId);
      const plantId = getSelectedPlantId();
      if (plantId) {
        saveLocalChatMemory(
          plantId,
          chatResponseModeRef.current,
          messages.map((message) => ({ role: message.sender, content: message.content }))
        );
      }
    } catch (error) {
      if (!handleApiError(doc, error)) frameAlert(doc, "대화 내역을 불러오지 못했습니다.");
    }
  }

  async function renderChatSessions(doc: Document, options: { autoLoadLast?: boolean } = {}) {
    if (hasSupabaseAuthConfig() && !hasAuthSession()) return;
    const container = doc.querySelector("aside .space-y-1.mb-8") as HTMLElement | null;
    if (!container) return;

    try {
      const plantId = getSelectedPlantId() || undefined;
      const mode = chatResponseModeRef.current;
      const sessions = await listChatSessions(plantId, mode);
      container.innerHTML = `<div class="flex items-center gap-3 p-3 mb-1 cursor-pointer hover:bg-growth-light dark:hover:bg-tertiary-container rounded-lg transition-all duration-200 text-on-surface-variant" data-chat-home="true">
        <span class="material-symbols-outlined">home</span>
        <span class="font-label-md">홈 개요</span>
      </div>
      <div class="flex items-center gap-3 p-3 mb-3 cursor-pointer bg-primary text-white rounded-lg shadow-sm hover:shadow-md transition-all" data-new-chat="true">
        <span class="material-symbols-outlined">add_comment</span>
        <span class="font-label-md">새 채팅</span>
      </div>
      <div class="mt-4 mb-2 px-3">
        <span class="text-label-sm uppercase tracking-wider font-bold text-outline">이 식물의 상담</span>
      </div>
      ${sessions.length ? sessions.map((session, index) => chatSessionItemHtml(session, index)).join("") : `<p class="px-3 py-2 text-label-sm text-on-surface-variant">아직 상담 내역이 없습니다.</p>`}`;

      container.querySelector("[data-chat-home]")?.addEventListener("click", () => navigate("dashboard"));
      container.querySelector("[data-new-chat]")?.addEventListener("click", () => {
        forceNewChatSessionRef.current = true;
        clearLastSessionId(plantId, mode);
        if (plantId) saveLocalChatMemory(plantId, mode, []);
        pendingChatPhotoRef.current = null;
        pendingChatPhotoNoteRef.current = "";
        initializeChatCanvas(doc);
        setChatAttachmentStatus(doc, null);
      });
      container.querySelectorAll("[data-chat-session]").forEach((item) => {
        item.addEventListener("click", () => {
          const sessionId = (item as HTMLElement).dataset.chatSession;
          if (sessionId) void loadChatMessages(doc, sessionId);
        });
      });

      const lastSession = getLastSessionId(plantId, mode);
      if (options.autoLoadLast && lastSession && sessions.some((session) => session.id === lastSession)) {
        void loadChatMessages(doc, lastSession);
      }
    } catch (error) {
      if (!handleApiError(doc, error)) console.warn("[Farmhani] chat sessions unavailable", error);
    }
  }

  function chatSessionItemHtml(session: ChatSession, index: number) {
    const selected = getLastSessionId() === session.id || index === 0;
    const className = selected ? "text-primary font-bold" : "text-on-surface-variant";
    const title = session.title?.trim() || `상담 ${formatDate(session.createdAt)}`;
    return `<div class="flex items-center gap-3 p-3 mb-1 cursor-pointer hover:bg-growth-light rounded-lg ${className}" data-chat-session="${escapeHtml(session.id)}">
      <span class="material-symbols-outlined">eco</span>
      <span class="font-label-md truncate" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
    </div>`;
  }

  function bindChatPhotoPicker(doc: Document) {
    const photoButton = doc.querySelector("button[title='사진 업로드']") as HTMLButtonElement | null;
    if (!photoButton) return;

    const input = createHiddenFileInput(doc);
    photoButton.addEventListener("click", (event) => {
      event.preventDefault();
      input.click();
    });
    input.addEventListener("change", () => {
      setPendingChatPhoto(doc, input.files?.[0] ?? null);
    });
  }

  function bindChatImageDropAndPaste(doc: Document) {
    const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
    const inputBar = textarea?.closest(".relative") as HTMLElement | null;
    const messages = doc.getElementById("chat-messages");
    if (!textarea || !inputBar) return;

    const pickImageFile = (files?: FileList | File[] | null) =>
      Array.from(files || []).find((file) => file.type.startsWith("image/"));

    textarea.addEventListener("paste", (event) => {
      const file = pickImageFile(event.clipboardData?.files);
      if (!file) return;
      event.preventDefault();
      setPendingChatPhoto(doc, file);
    });

    [inputBar, messages].filter(Boolean).forEach((target) => {
      target?.addEventListener("dragover", (event) => {
        event.preventDefault();
        inputBar.classList.add("ring-2", "ring-primary");
      });
      target?.addEventListener("dragleave", () => {
        inputBar.classList.remove("ring-2", "ring-primary");
      });
      target?.addEventListener("drop", (event) => {
        event.preventDefault();
        inputBar.classList.remove("ring-2", "ring-primary");
        const file = pickImageFile((event as DragEvent).dataTransfer?.files);
        if (file) setPendingChatPhoto(doc, file);
      });
    });
  }

  function bindChatSubmit(doc: Document) {
    const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
    const sendButton = textarea?.parentElement?.querySelector("button.bg-primary") as HTMLButtonElement | null;
    if (!textarea || !sendButton) return;
    const chatInput = textarea;
    const chatSendButton = sendButton;
    let isSubmitting = false;

    async function submit() {
      if (isSubmitting) return;
      const question = chatInput.value.trim();
      if (!question) return;
      isSubmitting = true;

      if (hasSupabaseAuthConfig() && !getAccessToken()) {
        isSubmitting = false;
        frameAlert(doc, "AI 상담은 로그인 후 사용할 수 있습니다.");
        navigate("login");
        return;
      }

      const file = pendingChatPhotoRef.current;
      appendUserMessage(doc, question, file);
      chatInput.value = "";

      const loading = appendAssistantLoading(doc);
      try {
        const plantId = await resolvePlantId(doc);
        const responseMode = chatResponseModeRef.current;
        let photoId: string | undefined;
        const localMemory = loadLocalChatMemory(plantId, responseMode);
        const newSession = forceNewChatSessionRef.current || !getLastSessionId(plantId, responseMode);

        if (file) {
          const photo = await uploadPlantPhoto(plantId, file, pendingChatPhotoNoteRef.current || question);
          photoId = photo.id;
        }

        const progressLabel = loading?.querySelector("p") as HTMLParagraphElement | null;
        const answer = await askPlantCareStream(
          question,
          plantId,
          {
            photoId,
            newSession,
            responseMode,
            recentMessages: localMemory
          },
          (progress) => {
            if (progressLabel) {
              progressLabel.textContent = `${progress.label} (${progress.step}/${progress.total})`;
            }
          }
        );
        forceNewChatSessionRef.current = false;
        setLastSessionId(answer.sessionId);
        if (loading) renderAssistantAnswer(doc, loading, answer);
        renderReferences(doc, answer.citations);
        appendLocalChatMemory(
          plantId,
          responseMode,
          { role: "user", content: question },
          { role: "assistant", content: answer.summary }
        );
        void renderChatSessions(doc, { autoLoadLast: false });
      } catch (error) {
        if (handleApiError(doc, error)) return;
        if (loading) {
          loading.innerHTML = `<div class="bg-error-container text-on-error-container p-4 rounded-2xl shadow-sm">
            상담 요청 중 오류가 발생했습니다. ${escapeHtml(error instanceof Error ? error.message : "")}
          </div>`;
        }
      } finally {
        pendingChatPhotoRef.current = null;
        pendingChatPhotoNoteRef.current = "";
        setChatAttachmentStatus(doc, null);
        isSubmitting = false;
      }
    }

    chatSendButton.addEventListener("click", (event) => {
      event.preventDefault();
      void submit();
    });
    chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
        event.preventDefault();
        void submit();
      }
    });

    const pendingDiagnosisQuestion = localStorage.getItem(PENDING_DIAGNOSIS_QUESTION_KEY);
    if (pendingDiagnosisQuestion) {
      localStorage.removeItem(PENDING_DIAGNOSIS_QUESTION_KEY);
      chatInput.value = pendingDiagnosisQuestion;
      doc.defaultView?.setTimeout(() => void submit(), 250);
    }
  }

  function bindChatQuickPrompts(doc: Document) {
    const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
    if (!textarea) return;

    const promptMap: Record<string, string> = {
      "흔한 해충": "잎 뒷면에 작은 점과 끈적임이 보이는데 흔한 해충 가능성이 있을까요?",
      "빛 요구량": "이 식물은 실내에서 어느 정도 빛을 받아야 건강하게 자랄까요?",
      "몬스테라 번식": "몬스테라를 번식시키려면 어떤 시기와 방법이 안전할까요?"
    };

    doc.querySelectorAll("span, button").forEach((element) => {
      const text = normalizedText(element);
      const prompt = promptMap[text];
      if (!prompt) return;
      element.addEventListener("click", (event) => {
        event.preventDefault();
        textarea.value = prompt;
        textarea.focus();
      });
    });
  }

  return {
    bindChatModelInfo,
    bindChatModeSelector,
    bindReferencePaneControls,
    initializeChatCanvas,
    bindChatPhotoPicker,
    bindChatImageDropAndPaste,
    bindChatSubmit,
    bindChatQuickPrompts,
    renderChatSessions
  };
}
