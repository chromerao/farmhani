import { clearAuthSession, hasAuthSession, hasSupabaseAuthConfig, searchRagDocuments } from "../api";
import { PENDING_DIAGNOSIS_QUESTION_KEY } from "../lib/constants";
import { createHiddenFileInput, escapeHtml, fileToResizedDataUrl, frameAlert, normalizedText } from "../lib/dom";
import { getSelectedPlantId, getUserProfilePhoto, isNotificationsEnabled, setNotificationsEnabled, setUserProfilePhoto } from "../lib/storage";
import type { AppContext } from "./context";
import type { DesignPage } from "../lib/constants";

export function createChrome(ctx: AppContext) {
  const { page, navigate } = ctx;

  function bindTopSearch(doc: Document) {
    const searchInput = doc.querySelector("header input[type='text']") as HTMLInputElement | null;
    if (!searchInput) return;
    searchInput.placeholder = "공식 문서/식물 데이터 검색...";

    const parent = searchInput.parentElement as HTMLElement | null;
    if (!parent) return;
    parent.style.position = "relative";
    const dropdown = doc.createElement("div");
    dropdown.className =
      "absolute top-full left-0 right-0 mt-2 z-50 bg-surface-container-lowest border border-outline-variant/20 rounded-xl shadow-lg overflow-hidden hidden min-w-[360px]";
    dropdown.dataset.searchResults = "true";
    parent.appendChild(dropdown);

    let timer: ReturnType<typeof setTimeout> | undefined;
    searchInput.addEventListener("input", () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(async () => {
        const query = searchInput.value.trim();
        if (query.length < 2) {
          dropdown.classList.add("hidden");
          dropdown.innerHTML = "";
          return;
        }
        try {
          const results = await searchRagDocuments(query, 5);
          dropdown.innerHTML = results.length
            ? results
                .map(
                  (item) => `<button class="w-full text-left px-4 py-3 hover:bg-growth-light transition-colors" data-query="${escapeHtml(query)}">
                    <span class="block text-label-md font-bold text-on-surface">${escapeHtml(item.title)}</span>
                    <span class="block text-[11px] text-primary font-bold mt-0.5">${escapeHtml(item.publisher || "공식 문서")}</span>
                    <span class="block text-label-sm text-on-surface-variant mt-1 line-clamp-2">${escapeHtml(item.excerpt)}</span>
                  </button>`
                )
                .join("")
            : `<div class="px-4 py-3 text-label-sm text-on-surface-variant">공식 문서 검색 결과가 없습니다.</div>`;
          dropdown.classList.toggle("hidden", false);
          dropdown.querySelectorAll("button[data-query]").forEach((button) => {
            button.addEventListener("click", (event) => {
              event.preventDefault();
              const selectedQuery = (button as HTMLElement).dataset.query || query;
              searchInput.value = selectedQuery;
              dropdown.classList.add("hidden");
              if (page === "chat") {
                const textarea = doc.querySelector("textarea") as HTMLTextAreaElement | null;
                if (textarea) {
                  textarea.value = `${selectedQuery}에 대해 공식 문서 기준으로 알려줘`;
                  textarea.focus();
                }
              } else {
                localStorage.setItem(PENDING_DIAGNOSIS_QUESTION_KEY, `${selectedQuery}에 대해 공식 문서 기준으로 알려줘`);
                navigate("chat");
              }
            });
          });
        } catch (error) {
          console.warn("[Farmhani] top search failed", error);
        }
      }, 250);
    });
  }

  function bindLogoHome(doc: Document) {
    const logo = Array.from(doc.querySelectorAll("header .flex.items-center.gap-2")).find((element) =>
      normalizedText(element).includes("Farm")
    ) as HTMLElement | undefined;
    if (!logo) return;
    logo.style.cursor = "pointer";
    logo.addEventListener("click", (event) => {
      event.preventDefault();
      navigate("dashboard");
    });
  }

  function bindSessionControls(doc: Document) {
    if (page === "login" || doc.querySelector("[data-session-controls]")) return;
    const header = doc.querySelector("header");
    if (!header) return;

    const rightArea =
      (Array.from(header.querySelectorAll(".flex.items-center.gap-4")).pop() as HTMLElement | undefined) ||
      (header.lastElementChild as HTMLElement | null);
    if (!rightArea) return;

    // 페이지마다 헤더 우측 컨테이너 클래스가 달라(.gap-4/.gap-2 등) rightArea 안에서만 찾으면
    // 아바타를 놓칠 수 있다 — 헤더 전체에서 원형(rounded-full) 컨테이너 속 img를 찾는다.
    const storedPhoto = getUserProfilePhoto();
    const existingProfileImage = (Array.from(header.querySelectorAll("img")).find((img) =>
      img.closest(".rounded-full")
    ) ?? null) as HTMLImageElement | null;
    // replaceWith 이후에는 closest가 동작하지 않으므로 컨테이너를 교체 전에 잡아둔다
    const existingAvatarContainer = (existingProfileImage?.closest(".rounded-full") ?? null) as HTMLElement | null;
    if (existingProfileImage && storedPhoto) {
      existingProfileImage.src = storedPhoto;
      existingProfileImage.alt = "사용자 프로필 사진";
    } else if (existingProfileImage) {
      // 저장된 사진이 없으면 목업의 타인 사진 대신 중립 아이콘을 보여준다
      const placeholder = doc.createElement("span");
      placeholder.className = "material-symbols-outlined text-primary text-[18px]";
      placeholder.dataset.avatarPlaceholder = "true";
      placeholder.textContent = "person";
      existingAvatarContainer?.classList.add("bg-primary-fixed-dim", "flex", "items-center", "justify-center");
      existingProfileImage.replaceWith(placeholder);
    }

    // 아바타 클릭으로 프로필 사진 등록/변경 (가입 시 저장에 실패했더라도 여기서 복구 가능)
    function attachAvatarPicker(container: HTMLElement) {
      if (container.dataset.avatarPicker === "true") return;
      container.dataset.avatarPicker = "true";
      container.style.cursor = "pointer";
      container.title = "프로필 사진 변경";
      const input = createHiddenFileInput(doc);
      container.addEventListener("click", (event) => {
        event.preventDefault();
        input.click();
      });
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (!file) return;
        const dataUrl = await fileToResizedDataUrl(file);
        setUserProfilePhoto(dataUrl);
        container.innerHTML = `<img alt="사용자 프로필 사진" class="w-full h-full object-cover" src="${escapeHtml(dataUrl)}">`;
        frameAlert(doc, "프로필 사진을 변경했습니다.");
      });
    }

    if (existingAvatarContainer) attachAvatarPicker(existingAvatarContainer);

    const isLoggedIn = hasAuthSession() || !hasSupabaseAuthConfig();
    const wrapper = doc.createElement("div");
    wrapper.dataset.sessionControls = "true";
    wrapper.className = "flex items-center gap-2";

    if (!existingProfileImage) {
      const avatar = doc.createElement("div");
      avatar.className =
        "w-8 h-8 rounded-full bg-primary-fixed-dim flex items-center justify-center overflow-hidden border border-outline-variant/20";
      avatar.innerHTML = storedPhoto
        ? `<img alt="사용자 프로필 사진" class="w-full h-full object-cover" src="${escapeHtml(storedPhoto)}">`
        : '<span class="material-symbols-outlined text-primary text-[18px]">person</span>';
      attachAvatarPicker(avatar);
      wrapper.appendChild(avatar);
    }

    const button = doc.createElement("button");
    button.type = "button";
    button.className =
      "px-3 py-2 rounded-full bg-surface-container-high text-on-surface text-label-sm font-bold border border-outline-variant/20 hover:bg-growth-light hover:text-primary transition-all";
    button.textContent = isLoggedIn ? "로그아웃" : "로그인";
    button.addEventListener("click", (event) => {
      event.preventDefault();
      if (isLoggedIn) {
        clearAuthSession();
        frameAlert(doc, "로그아웃되었습니다.");
      }
      navigate("login");
    });
    wrapper.appendChild(button);
    rightArea.appendChild(wrapper);
  }

  function styleNotificationButton(button: HTMLElement) {
    const win = button.ownerDocument.defaultView;
    const supported = Boolean(win && "Notification" in win);
    const enabled = supported && win?.Notification.permission === "granted" && isNotificationsEnabled();
    button.setAttribute(
      "title",
      supported
        ? enabled
          ? "물주기 알림 켜짐 - 클릭하면 끕니다"
          : "물주기 알림 켜기"
        : "이 브라우저는 알림을 지원하지 않습니다"
    );
    button.classList.toggle("text-primary", Boolean(enabled));
    button.classList.toggle("bg-growth-light", Boolean(enabled));
  }

  async function toggleNotifications(doc: Document, button: HTMLElement) {
    const win = doc.defaultView;
    if (!win || !("Notification" in win)) {
      frameAlert(doc, "이 브라우저는 알림을 지원하지 않습니다.");
      return;
    }

    if (win.Notification.permission === "denied") {
      setNotificationsEnabled(false);
      styleNotificationButton(button);
      frameAlert(doc, "브라우저에서 알림이 차단되어 있습니다. 사이트 설정에서 알림을 허용해 주세요.");
      return;
    }

    if (win.Notification.permission === "granted") {
      const nextEnabled = !isNotificationsEnabled();
      setNotificationsEnabled(nextEnabled);
      styleNotificationButton(button);
      if (nextEnabled) {
        new win.Notification("Farm하니 알림이 켜졌어요", {
          body: "물주기가 필요한 식물이 있으면 하루 한 번 알려드릴게요."
        });
      } else {
        frameAlert(doc, "물주기 알림을 껐습니다.");
      }
      return;
    }

    const permission = await win.Notification.requestPermission();
    const granted = permission === "granted";
    setNotificationsEnabled(granted);
    styleNotificationButton(button);
    if (granted) {
      new win.Notification("Farm하니 알림이 켜졌어요", {
        body: "물주기가 필요한 식물이 있으면 하루 한 번 알려드릴게요."
      });
    } else {
      frameAlert(doc, "알림 권한이 허용되지 않았습니다.");
    }
  }

  function bindMobileChrome(doc: Document) {
    // 1) 모바일 공통 스타일 — 주입 요소가 Tailwind CDN에 의존하지 않도록 핵심 레이아웃은 직접 CSS로 보장
    if (!doc.querySelector("[data-mobile-style]")) {
      const style = doc.createElement("style");
      style.dataset.mobileStyle = "true";
      style.textContent = `
        [data-mobile-nav] { position: fixed; bottom: 0; left: 0; right: 0; z-index: 90; display: flex;
          background: rgba(255,255,255,0.96); backdrop-filter: blur(8px); border-top: 1px solid rgba(0,0,0,0.08);
          padding-bottom: env(safe-area-inset-bottom); }
        [data-mobile-nav] button { flex: 1 1 0; display: flex; flex-direction: column; align-items: center; gap: 2px;
          padding: 8px 0 6px; border: 0; background: transparent; font-size: 11px; font-weight: 700;
          color: #5f6c64; cursor: pointer; -webkit-tap-highlight-color: transparent; }
        [data-mobile-nav] button[data-active="true"] { color: #0f5238; }
        @media (min-width: 768px) { [data-mobile-nav] { display: none; } }
        @media (max-width: 767px) {
          /* iOS에서 16px 미만 입력 포커스 시 자동 확대되는 것을 방지 */
          input, textarea, select { font-size: 16px !important; }
          /* 하단 네비게이션에 내용이 가려지지 않도록 여백 확보.
             스크롤이 내부 main에서 일어나는 구조(dashboard/chat)에서도 동작하도록
             body가 아닌 main에 패딩을 준다 (border-box라 overflow-hidden 플렉스도 함께 줄어든다) */
          body[data-has-mobile-nav="true"] main { padding-bottom: calc(76px + env(safe-area-inset-bottom)) !important; }
          /* 상세 페이지 플로팅 버튼을 네비 위로 올린다 */
          [data-detail-delete-plant] { bottom: calc(84px + env(safe-area-inset-bottom)) !important; }
          [data-detail-edit-plant] { bottom: calc(140px + env(safe-area-inset-bottom)) !important; }
        }
      `;
      doc.head.appendChild(style);
    }

    // 2) 하단 앱 네비게이션 (로그인 화면 제외)
    if (page === "login" || doc.querySelector("[data-mobile-nav]")) return;
    doc.body.dataset.hasMobileNav = "true";

    const tabs: { key: DesignPage; label: string; icon: string }[] = [
      { key: "dashboard", label: "홈", icon: "home" },
      { key: "chat", label: "AI 상담", icon: "forum" },
      { key: "add", label: "등록", icon: "add_circle" },
      { key: "detail", label: "내 식물", icon: "potted_plant" }
    ];

    const nav = doc.createElement("nav");
    nav.dataset.mobileNav = "true";
    nav.setAttribute("aria-label", "모바일 하단 메뉴");
    nav.innerHTML = tabs
      .map(
        (tab) => `<button type="button" data-mobile-tab="${tab.key}" data-active="${tab.key === page}">
          <span class="material-symbols-outlined" style="font-size:22px;${tab.key === page ? "font-variation-settings:'FILL' 1;" : ""}">${tab.icon}</span>
          ${tab.label}
        </button>`
      )
      .join("");
    doc.body.appendChild(nav);

    nav.querySelectorAll("[data-mobile-tab]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const target = (button as HTMLElement).dataset.mobileTab as DesignPage;
        if (target === page) return;
        // 등록된 식물이 없으면 '내 식물' 탭은 등록 화면으로 안내
        if (target === "detail" && !getSelectedPlantId()) {
          navigate("add");
          return;
        }
        navigate(target);
      });
    });
  }

  function bindGenericControls(doc: Document) {
    doc.querySelectorAll("button, a").forEach((element) => {
      const text = normalizedText(element);
      const target = element as HTMLElement;
      if (target.id === "auth-submit" || target.id === "toggle-auth") return;
      if (page === "add" && target.closest("#form-card")) return;
      if (page === "dashboard" && target.closest("aside")) return;
      if (page === "detail" && target.closest("aside")) return;

      if (text.includes("dark_mode")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          doc.documentElement.classList.toggle("dark");
        });
      } else if (text.includes("notifications")) {
        styleNotificationButton(target);
        if (target.dataset.notificationsBound === "true") return;
        target.dataset.notificationsBound = "true";
        element.addEventListener("click", (event) => {
          event.preventDefault();
          void toggleNotifications(doc, target);
        });
      } else if (text.includes("settings")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          frameAlert(doc, "설정 화면은 계정 설정 API 확정 후 연결됩니다.");
        });
      } else if (text.includes("share")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          doc.defaultView?.navigator.clipboard?.writeText(doc.defaultView.location.href);
          frameAlert(doc, "현재 화면 주소를 복사했습니다.");
        });
      } else if (text.includes("more_vert") || text.includes("filter_list") || text.includes("open_in_full") || text.includes("grid_view") || text.includes("view_list")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          frameAlert(doc, "보기 옵션을 적용했습니다.");
        });
      } else if (text.includes("출처 보기")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          doc.getElementById("reference-pane")?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      } else if (text.includes("모든 전문가 팁")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("chat");
        });
      } else if (text === "홈") {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("dashboard");
        });
      } else if (text === "채팅" || text.includes("AI 조언")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("chat");
        });
      } else if (text.includes("라이브러리") || text.includes("둘러보기") || text.includes("프로필")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          frameAlert(doc, "해당 메뉴는 다음 단계에서 실제 화면으로 확장됩니다.");
        });
      } else if (text.includes("개인정보") || text.includes("이용약관") || text.includes("지원") || text.includes("고객지원") || text.includes("도움말")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          frameAlert(doc, "문서/고객지원 페이지는 배포 단계에서 연결합니다.");
        });
      } else if (text.includes("카테고리 추가") || text.includes("새 카테고리")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          frameAlert(doc, "카테고리 기능은 식물 목록 저장 이후 확장 예정입니다.");
        });
      }
    });
  }

  function bindFrameNavigation(doc: Document) {
    doc.querySelectorAll("a, button, [role='button']").forEach((element) => {
      const text = normalizedText(element);
      const label = text.toLowerCase();
      const target = element as HTMLElement;
      const id = target.id;

      if (id === "auth-submit" || id === "toggle-auth") return;
      if (page === "add" && target.closest("#form-card")) return;
      if (page === "detail" && (text.includes("물주기 기록") || text.includes("새 일지 작성") || text.includes("edit"))) return;
      if (page === "detail" && target.closest("aside")) return;
      if (target.closest("[data-plant-card]") || target.closest("[data-water-plant]")) return;
      if (target.closest("button[title='사진 업로드']")) return;
      if (text.includes("카테고리")) return;

      if (text.includes("AI 상담") || text.includes("AI 조언") || text.includes("빠른 AI 진단") || label.includes("diagnosis")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("chat");
        });
        return;
      }

      if (text.includes("내 식물") || text.includes("대시보드") || text.includes("홈 개요")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("dashboard");
        });
        return;
      }

      if (text.includes("등록") || text.includes("추가") || label.includes("add")) {
        element.addEventListener("click", (event) => {
          if ((event.currentTarget as HTMLElement).closest("#form-nav")) return;
          event.preventDefault();
          navigate("add");
        });
        return;
      }

      if (text.includes("상세") || text.includes("성장 일지") || text.includes("몬스테라") || text.includes("몬티")) {
        element.addEventListener("click", (event) => {
          event.preventDefault();
          navigate("detail");
        });
      }
    });
  }

  return { bindTopSearch, bindLogoHome, bindSessionControls, bindGenericControls, bindFrameNavigation, bindMobileChrome };
}
