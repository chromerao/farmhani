import { createCareLog, getPlants, getTodayChecklist, hasAuthSession, hasSupabaseAuthConfig } from "../api";
import type { ChecklistTask, Plant } from "../types";
import { PENDING_DIAGNOSIS_QUESTION_KEY } from "../lib/constants";
import { createHiddenFileInput, escapeHtml, findPlantGrid, frameAlert, normalizedText, showTextInputModal } from "../lib/dom";
import { todayDateInput } from "../lib/format";
import { clearLastSessionId, getSelectedPlantId, setSelectedPlantId } from "../lib/storage";
import { addPlantCardHtml, plantCardHtml } from "../lib/plantCards";
import type { AppContext, DashboardPlantCategory } from "./context";

export function createDashboardPage(ctx: AppContext) {
  const {
    navigate,
    handleApiError,
    removePlant,
    dashboardPlantsRef,
    pendingChatPhotoRef,
    pendingChatPhotoNoteRef,
    chatResponseModeRef
  } = ctx;

  function renderDashboardPlants(doc: Document, plants: Plant[]) {
    const grid = findPlantGrid(doc);
    if (!grid) return;

    grid.innerHTML = `${plants.map((plant, index) => plantCardHtml(plant, index)).join("")}${addPlantCardHtml()}`;
    grid.querySelectorAll("[data-plant-card]").forEach((card) => {
      const plantId = (card as HTMLElement).dataset.plantCard;
      const imageArea = card.querySelector(".relative") as HTMLElement | null;
      if (plantId && imageArea && !imageArea.querySelector("[data-delete-plant]")) {
        const deleteButton = doc.createElement("button");
        deleteButton.type = "button";
        deleteButton.dataset.deletePlant = plantId;
        deleteButton.title = "식물 삭제";
        deleteButton.className =
          "absolute top-4 left-4 w-9 h-9 rounded-full bg-white/85 text-diagnostic-red backdrop-blur-md flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-diagnostic-red hover:text-white transition-all";
        deleteButton.innerHTML = '<span class="material-symbols-outlined text-[18px]">delete</span>';
        deleteButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void removePlant(doc, plantId);
        });
        imageArea.appendChild(deleteButton);
      }
      card.addEventListener("click", () => {
        if (plantId) {
          setSelectedPlantId(plantId);
          navigate("detail");
        }
      });
    });
    grid.querySelectorAll("[data-water-plant]").forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.stopPropagation();
        const plantId = (button as HTMLElement).dataset.waterPlant;
        if (!plantId) return;
        try {
          await createCareLog(plantId, {
            wateredAt: todayDateInput(),
            leafCondition: "사용자가 대시보드에서 빠른 물주기를 기록함",
            soilCondition: "미기록",
            memo: "빠른 물주기 버튼"
          });
          frameAlert(doc, "오늘 물주기 기록을 저장했습니다.");
        } catch (error) {
          if (!handleApiError(doc, error)) frameAlert(doc, "물주기 기록 저장에 실패했습니다.");
        }
      });
    });
    grid.querySelector("[data-add-plant]")?.addEventListener("click", () => navigate("add"));

    const overview = Array.from(doc.querySelectorAll("p")).find((element) => normalizedText(element).includes("식물이 잘 자라고"));
    if (overview) overview.textContent = `${plants.length}개 식물 프로필을 관리 중입니다`;
  }

  function plantSearchText(plant: Plant) {
    return `${plant.name} ${plant.species ?? ""} ${plant.location ?? ""} ${plant.sunlight ?? ""}`.toLowerCase();
  }

  function filterPlantsByQuery(plants: Plant[], query: string) {
    const term = query.trim().toLowerCase();
    if (!term) return plants;
    return plants.filter((plant) => plantSearchText(plant).includes(term));
  }

  function filterPlantsByCategory(plants: Plant[], category: DashboardPlantCategory) {
    if (category === "all") return plants;
    const keywordMap: Record<Exclude<DashboardPlantCategory, "all">, string[]> = {
      indoor: [
        "몬스테라",
        "스투키",
        "스파티필럼",
        "금전수",
        "선인장",
        "야자",
        "고무나무",
        "스킨답서스",
        "필로덴드론",
        "알로카시아",
        "monstera",
        "dracaena",
        "ficus",
        "pothos",
        "spathiphyllum"
      ],
      crop: [
        "토마토",
        "방울토마토",
        "고추",
        "파프리카",
        "상추",
        "배추",
        "딸기",
        "감자",
        "고구마",
        "오이",
        "가지",
        "호박",
        "수박",
        "참외",
        "무",
        "당근",
        "양파",
        "마늘",
        "lactuca",
        "solanum",
        "capsicum",
        "fragaria"
      ],
      ornamental: [
        "장미",
        "벚",
        "개나리",
        "해바라기",
        "국화",
        "튤립",
        "백합",
        "수국",
        "카네이션",
        "제라늄",
        "베고니아",
        "rose",
        "rosa",
        "forsythia",
        "helianthus",
        "hydrangea"
      ]
    };
    const keywords = keywordMap[category];
    return plants.filter((plant) => keywords.some((keyword) => plantSearchText(plant).includes(keyword.toLowerCase())));
  }

  function bindDashboardCategoryChips(doc: Document, plants: Plant[]) {
    const plantSection = Array.from(doc.querySelectorAll("section")).find((section) =>
      normalizedText(section.querySelector("h2")).includes("내 식물")
    ) as HTMLElement | undefined;
    const heading = plantSection?.querySelector("h2");
    const headerRow = heading?.parentElement as HTMLElement | null;
    if (!headerRow || headerRow.querySelector("[data-dashboard-category-chips]")) return;

    const chips = doc.createElement("div");
    chips.dataset.dashboardCategoryChips = "true";
    chips.className = "flex items-center gap-2 flex-wrap";
    const categories: { key: DashboardPlantCategory; label: string }[] = [
      { key: "all", label: "전체" },
      { key: "indoor", label: "실내식물" },
      { key: "crop", label: "작물" },
      { key: "ornamental", label: "화훼" }
    ];
    chips.innerHTML = categories
      .map(
        (category, index) =>
          `<button class="px-3 py-1.5 rounded-full text-label-sm font-bold border transition-colors ${
            index === 0 ? "bg-primary text-white border-primary" : "bg-white text-on-surface-variant border-outline-variant/30 hover:bg-growth-light"
          }" data-dashboard-category="${category.key}">${category.label}</button>`
      )
      .join("");
    headerRow.appendChild(chips);

    chips.querySelectorAll("button[data-dashboard-category]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const category = ((button as HTMLElement).dataset.dashboardCategory || "all") as DashboardPlantCategory;
        chips.querySelectorAll("button").forEach((item) => {
          item.classList.remove("bg-primary", "text-white", "border-primary");
          item.classList.add("bg-white", "text-on-surface-variant", "border-outline-variant/30");
        });
        button.classList.add("bg-primary", "text-white", "border-primary");
        button.classList.remove("bg-white", "text-on-surface-variant", "border-outline-variant/30");
        renderDashboardPlants(doc, filterPlantsByCategory(plants, category));
      });
    });
  }

  function setSidebarActive(items: HTMLElement[], activeItem: HTMLElement) {
    items.forEach((item) => {
      item.classList.remove("text-primary", "font-bold", "bg-growth-light");
      item.classList.add("text-on-surface-variant");
    });
    activeItem.classList.add("text-primary", "font-bold", "bg-growth-light");
    activeItem.classList.remove("text-on-surface-variant");
  }

  function bindDashboardSidebar(doc: Document, plants: Plant[]) {
    const items = Array.from(doc.querySelectorAll("aside .space-y-1 > div")) as HTMLElement[];
    const sidebarConfig: { label: string; icon: string; category: DashboardPlantCategory | "chat"; count?: number }[] = [
      { label: "내 식물", icon: "potted_plant", category: "indoor", count: filterPlantsByCategory(plants, "indoor").length },
      { label: "내 작물", icon: "agriculture", category: "crop", count: filterPlantsByCategory(plants, "crop").length },
      { label: "화훼", icon: "local_florist", category: "ornamental", count: filterPlantsByCategory(plants, "ornamental").length },
      { label: "최근 상담", icon: "forum", category: "chat" }
    ];

    items.forEach((item, index) => {
      const config = sidebarConfig[index];
      if (config) {
        const icon = item.querySelector(".material-symbols-outlined");
        const label = Array.from(item.querySelectorAll("span")).find((span) => !span.classList.contains("material-symbols-outlined") && !span.classList.contains("ml-auto"));
        const badge = item.querySelector(".ml-auto");
        if (icon) icon.textContent = config.icon;
        if (label) label.textContent = config.label;
        if (badge && typeof config.count === "number") badge.textContent = String(config.count);
        if (badge && typeof config.count !== "number") badge.textContent = "";
        item.dataset.dashboardSidebar = String(config.category);
      }
      item.addEventListener("click", (event) => {
        event.preventDefault();
        setSidebarActive(items, item);
        const category = (item.dataset.dashboardSidebar || "all") as DashboardPlantCategory | "chat";
        if (category === "chat") {
          navigate("chat");
          return;
        }
        if (category !== "all") {
          renderDashboardPlants(doc, filterPlantsByCategory(dashboardPlantsRef.current, category));
          return;
        }
        renderDashboardPlants(doc, dashboardPlantsRef.current);
      });
    });

    const categoryButton = Array.from(doc.querySelectorAll("aside button")).find((button) =>
      normalizedText(button).includes("카테고리 추가")
    ) as HTMLButtonElement | undefined;
    categoryButton?.addEventListener("click", (event) => {
      event.preventDefault();
      const keyword = doc.defaultView?.prompt("필터링할 식물 이름이나 품종 키워드를 입력해 주세요.")?.trim();
      if (!keyword) return;
      renderDashboardPlants(doc, filterPlantsByQuery(dashboardPlantsRef.current, keyword));
    });
  }

  function renderDashboardHealthOverview(doc: Document, plants: Plant[]) {
    const title = Array.from(doc.querySelectorAll("h3")).find((element) => normalizedText(element).includes("건강 개요"));
    const card = title?.closest(".glass-card") as HTMLElement | null;
    if (!card) return;

    const total = plants.length;
    const withProfile = plants.filter((plant) => plant.species && plant.imageUrl).length;
    const needsProfile = plants.find((plant) => !plant.imageUrl || !plant.species);
    const percent = total ? Math.round((withProfile / total) * 100) : 0;
    const actionPlant = needsProfile || plants[0];
    const actionTitle = !total ? "첫 식물 등록" : needsProfile ? `${needsProfile.name} 정보 보강` : `${actionPlant.name} 상태 기록`;
    const actionCopy = !total
      ? "대시보드를 시작하려면 식물을 먼저 등록해 주세요."
      : needsProfile
        ? "사진이나 품종 정보가 부족합니다. 상담 정확도를 높이려면 프로필을 보강해 주세요."
        : "오늘 관찰한 잎, 흙, 물주기 상태를 기록하면 다음 상담에 반영됩니다.";
    const actionIcon = !total ? "add_circle" : needsProfile ? "photo_camera" : "edit_note";

    card.innerHTML = `<div>
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-headline-md font-headline-md text-primary">건강 개요</h3>
        <span class="material-symbols-outlined text-primary">analytics</span>
      </div>
      <div class="flex items-center gap-4 mb-6">
        <div class="w-16 h-16 rounded-full border-4 border-sage-accent flex items-center justify-center">
          <span class="text-label-md font-bold text-primary">${percent}%</span>
        </div>
        <div>
          <p class="text-label-md font-bold">관리 준비도</p>
          <p class="text-label-sm text-on-surface-variant">${total ? `${withProfile}/${total}개 식물이 상담 준비 완료` : "등록된 식물이 없습니다"}</p>
        </div>
      </div>
    </div>
    <button class="w-full text-left p-4 ${needsProfile || !total ? "bg-error-container/50" : "bg-growth-light"} rounded-2xl flex items-center gap-3 hover:brightness-95 transition-all" data-dashboard-health-action="true">
      <span class="material-symbols-outlined ${needsProfile || !total ? "text-diagnostic-red" : "text-primary"}">${actionIcon}</span>
      <div>
        <p class="text-label-sm font-bold ${needsProfile || !total ? "text-on-error-container" : "text-primary"}">오늘 체크</p>
        <p class="text-label-sm text-on-surface-variant">${escapeHtml(actionTitle)}</p>
        <p class="text-[11px] text-on-surface-variant mt-1">${escapeHtml(actionCopy)}</p>
      </div>
    </button>`;

    card.querySelector("[data-dashboard-health-action]")?.addEventListener("click", (event) => {
      event.preventDefault();
      if (!total) {
        navigate("add");
        return;
      }
      setSelectedPlantId(actionPlant.id);
      navigate(needsProfile ? "detail" : "chat");
    });
  }

  function renderDashboardCareTips(doc: Document, plants: Plant[]) {
    const title = Array.from(doc.querySelectorAll("h3")).find((element) => normalizedText(element).includes("식물 케어 팁"));
    const card = title?.closest(".bg-surface-container-high") as HTMLElement | null;
    if (!card) return;

    const selectedPlant = plants.find((plant) => plant.id === getSelectedPlantId()) || plants[0];
    const plantLabel = selectedPlant?.name || "내 식물";
    const speciesLabel = selectedPlant?.species || plantLabel;
    card.innerHTML = `<div>
      <h3 class="text-headline-md text-tertiary mb-2">케어 액션</h3>
      <p class="text-body-md text-on-surface-variant mb-4">고정 팁 대신 현재 식물과 공식 문서를 바로 연결합니다.</p>
      <div class="space-y-4">
        <button class="w-full text-left flex gap-4 items-start p-3 bg-white/50 rounded-xl hover:bg-growth-light transition-all" data-care-tip-search="true">
          <span class="material-symbols-outlined text-primary">search</span>
          <div>
            <p class="text-label-md font-bold">${escapeHtml(plantLabel)} 공식 문서 검색</p>
            <p class="text-label-sm text-on-surface-variant">${escapeHtml(speciesLabel)}의 물주기, 빛, 흙 관리 근거를 찾아봅니다.</p>
          </div>
        </button>
        <button class="w-full text-left flex gap-4 items-start p-3 bg-white/50 rounded-xl hover:bg-growth-light transition-all" data-care-tip-photo="true">
          <span class="material-symbols-outlined text-primary">add_a_photo</span>
          <div>
            <p class="text-label-md font-bold">사진으로 상태 상담</p>
            <p class="text-label-sm text-on-surface-variant">잎이나 흙 사진을 첨부해 AI 상담으로 바로 이동합니다.</p>
          </div>
        </button>
      </div>
    </div>
    <button class="text-primary font-bold text-label-md flex items-center gap-2 hover:underline mt-4" data-care-tip-chat="true">
      최근 상담으로 이동
      <span class="material-symbols-outlined text-sm">arrow_forward</span>
    </button>`;

    card.querySelector("[data-care-tip-search]")?.addEventListener("click", (event) => {
      event.preventDefault();
      if (selectedPlant?.id) setSelectedPlantId(selectedPlant.id);
      localStorage.setItem(PENDING_DIAGNOSIS_QUESTION_KEY, `${speciesLabel} 물주기와 빛 관리 기준을 공식 문서 근거로 알려줘`);
      navigate("chat");
    });
    card.querySelector("[data-care-tip-photo]")?.addEventListener("click", (event) => {
      event.preventDefault();
      if (selectedPlant?.id) setSelectedPlantId(selectedPlant.id);
      localStorage.setItem(PENDING_DIAGNOSIS_QUESTION_KEY, `${plantLabel} 상태 사진을 기준으로 현재 관리 상태를 봐줘`);
      navigate("chat");
    });
    card.querySelector("[data-care-tip-chat]")?.addEventListener("click", (event) => {
      event.preventDefault();
      if (selectedPlant?.id) setSelectedPlantId(selectedPlant.id);
      navigate("chat");
    });
  }

  function checklistTaskIcon(task: ChecklistTask) {
    if (task.taskType === "water") return "water_drop";
    if (task.taskType === "observe") return "edit_note";
    return "photo_camera";
  }

  function renderTodayChecklist(doc: Document, tasks: ChecklistTask[]) {
    doc.querySelector("[data-today-checklist]")?.remove();
    if (!tasks.length) return;

    const plantsSection = Array.from(doc.querySelectorAll("section")).find((section) =>
      normalizedText(section.querySelector("h2")).includes("내 식물")
    );
    if (!plantsSection) return;

    const doneCount = tasks.filter((task) => task.done).length;
    const allDone = doneCount === tasks.length;

    const card = doc.createElement("div");
    card.dataset.todayChecklist = "true";
    card.className = "mb-6 rounded-2xl border border-primary/20 bg-white px-5 py-4 shadow-sm animate-fade-in";
    card.innerHTML = `<div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">checklist</span>
          <h3 class="text-headline-sm font-bold text-on-surface">오늘의 체크리스트</h3>
        </div>
        <span class="text-label-sm font-bold ${allDone ? "text-primary" : "text-on-surface-variant"}">${doneCount}/${tasks.length} 완료${allDone ? " 🎉" : ""}</span>
      </div>
      <div class="space-y-1">
        ${tasks
          .map(
            (task) => `<button class="w-full text-left flex items-center gap-3 p-2.5 rounded-xl transition-all ${
              task.done ? "opacity-60" : "hover:bg-growth-light"
            }" data-checklist-task="${escapeHtml(task.id)}">
              <span class="shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                task.done ? "bg-primary border-primary text-white" : "border-outline-variant/60 text-transparent"
              }"><span class="material-symbols-outlined text-[16px]">check</span></span>
              <span class="material-symbols-outlined text-primary text-[20px] shrink-0">${checklistTaskIcon(task)}</span>
              <span class="min-w-0">
                <span class="block text-label-md font-bold text-on-surface ${task.done ? "line-through" : ""}">${escapeHtml(task.title)}</span>
                <span class="block text-label-sm text-on-surface-variant truncate">${escapeHtml(task.description)}</span>
              </span>
            </button>`
          )
          .join("")}
      </div>`;
    plantsSection.insertBefore(card, plantsSection.firstChild);

    card.querySelectorAll("[data-checklist-task]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const taskId = (button as HTMLElement).dataset.checklistTask;
        const task = tasks.find((item) => item.id === taskId);
        if (!task || task.done) return;

        if (task.taskType === "water") {
          void (async () => {
            try {
              await createCareLog(task.plantId, {
                wateredAt: todayDateInput(),
                leafCondition: "오늘의 체크리스트에서 물주기를 기록함",
                soilCondition: "미기록",
                memo: "오늘의 체크리스트"
              });
              frameAlert(doc, `${task.plantName} 물주기 기록을 저장했습니다.`);
              void bindTodayChecklist(doc);
            } catch (error) {
              if (!handleApiError(doc, error)) frameAlert(doc, "물주기 기록 저장에 실패했습니다.");
            }
          })();
          return;
        }

        if (task.taskType === "observe") {
          showTextInputModal(
            doc,
            {
              title: `${task.plantName} 상태 기록`,
              description: "오늘 보이는 잎, 줄기, 흙 상태를 짧게 남기면 다음 상담에서 함께 참고합니다.",
              placeholder: "예: 새잎은 잘 펴졌고 흙은 아직 촉촉해요.",
              submitLabel: "기록 저장"
            },
            async (memo) => {
              try {
                await createCareLog(task.plantId, {
                  wateredAt: undefined,
                  leafCondition: memo,
                  soilCondition: "미기록",
                  memo: "오늘의 체크리스트 상태 기록"
                });
                frameAlert(doc, `${task.plantName} 상태 기록을 저장했습니다.`);
                void bindTodayChecklist(doc);
              } catch (error) {
                if (!handleApiError(doc, error)) frameAlert(doc, "상태 기록 저장에 실패했습니다.");
              }
            }
          );
          return;
        }

        // photo: 상세 페이지의 사진 업로드 플로우로 이동
        setSelectedPlantId(task.plantId);
        navigate("detail");
      });
    });

    // 브라우저 알림 (권한이 이미 허용된 경우에만, 하루 1회) — 물주기가 밀린 식물 기준
    const dueWaterCount = tasks.filter((task) => task.taskType === "water" && !task.done).length;
    const win = doc.defaultView;
    if (dueWaterCount > 0 && win && "Notification" in win && win.Notification.permission === "granted") {
      const NOTIFIED_KEY = "farmhani_watering_notified_date";
      const today = new Date().toISOString().slice(0, 10);
      if (localStorage.getItem(NOTIFIED_KEY) !== today) {
        localStorage.setItem(NOTIFIED_KEY, today);
        new win.Notification("Farm하니? 물주기 알림", {
          body: `물주기가 필요한 식물이 ${dueWaterCount}개 있어요. 오늘의 체크리스트를 확인해보세요.`
        });
      }
    }
  }

  async function bindTodayChecklist(doc: Document) {
    try {
      const tasks = await getTodayChecklist();
      renderTodayChecklist(doc, tasks);
    } catch (error) {
      // 체크리스트는 보조 기능 — 실패해도 대시보드 로딩을 막지 않는다
      console.warn("[Farmhani] today checklist unavailable:", error);
    }
  }

  async function bindDashboardData(doc: Document) {
    if (hasSupabaseAuthConfig() && !hasAuthSession()) {
      frameAlert(doc, "로그인 후 내 식물 목록을 불러올 수 있습니다.");
      navigate("login");
      return;
    }

    try {
      const plants = await getPlants();
      dashboardPlantsRef.current = plants;
      if (plants[0]?.id && !getSelectedPlantId()) setSelectedPlantId(plants[0].id);
      const pendingFilter = localStorage.getItem("farmhani_dashboard_filter") as DashboardPlantCategory | null;
      localStorage.removeItem("farmhani_dashboard_filter");
      renderDashboardPlants(doc, pendingFilter ? filterPlantsByCategory(plants, pendingFilter) : plants);
      bindDashboardCategoryChips(doc, plants);
      bindDashboardSidebar(doc, plants);
      renderDashboardHealthOverview(doc, plants);
      renderDashboardCareTips(doc, plants);
      void bindTodayChecklist(doc);
    } catch (error) {
      if (!handleApiError(doc, error)) frameAlert(doc, `식물 목록을 불러오지 못했습니다. ${error instanceof Error ? error.message : ""}`);
    }
  }

  function bindDashboardUpload(doc: Document) {
    const uploadBox = Array.from(doc.querySelectorAll(".border-dashed")).find((element) =>
      normalizedText(element).includes("이미지를 드래그하거나 클릭")
    ) as HTMLElement | undefined;
    if (!uploadBox) return;

    const input = createHiddenFileInput(doc);
    uploadBox.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      pendingChatPhotoRef.current = input.files?.[0] ?? null;
      if (pendingChatPhotoRef.current) {
        pendingChatPhotoNoteRef.current = "";
        localStorage.setItem(
          PENDING_DIAGNOSIS_QUESTION_KEY,
          "첨부한 사진을 기준으로 현재 식물 상태를 진단해 주세요."
        );
        clearLastSessionId(undefined, chatResponseModeRef.current);
        navigate("chat");
      }
    });
  }

  return { bindDashboardData, bindDashboardUpload };
}
