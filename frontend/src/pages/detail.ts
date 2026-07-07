import { createCareLog, getPlant, hasAuthSession, hasSupabaseAuthConfig, storagePathToPublicUrl, updatePlant, uploadPlantPhoto } from "../api";
import type { Plant } from "../types";
import { createHiddenFileInput, escapeHtml, frameAlert, normalizedText, showFormModal, showTextInputModal } from "../lib/dom";
import { formatDate, todayDateInput } from "../lib/format";
import { getSelectedPlantId } from "../lib/storage";
import type { AppContext, DashboardPlantCategory } from "./context";

export function createDetailPage(ctx: AppContext) {
  const { navigate, handleApiError, removePlant } = ctx;
  // 편집 모달 프리필용 — bindDetailData가 마지막으로 불러온 식물 정보
  let currentPlant: Plant | null = null;

  function bindDetailSidebar(doc: Document) {
    const items = Array.from(doc.querySelectorAll("aside nav > div")) as HTMLElement[];
    items.forEach((item) => {
      const text = normalizedText(item);
      item.addEventListener("click", (event) => {
        event.preventDefault();
        if (text.includes("홈")) {
          navigate("dashboard");
          return;
        }
        if (text.includes("다육") || text.includes("식물")) {
          localStorage.setItem("farmhani_dashboard_filter", "indoor");
          navigate("dashboard");
          return;
        }
        if (text.includes("작물") || text.includes("텃밭")) {
          localStorage.setItem("farmhani_dashboard_filter", "crop");
          navigate("dashboard");
          return;
        }
        if (text.includes("이파리") || text.includes("대엽") || text.includes("관엽") || text.includes("고사리") || text.includes("화훼") || text.includes("꽃")) {
          localStorage.setItem("farmhani_dashboard_filter", "ornamental");
          navigate("dashboard");
          return;
        }
        if (text.includes("최근")) {
          navigate("chat");
        }
      });
    });

    const addCategory = Array.from(doc.querySelectorAll("aside button")).find((button) => normalizedText(button).includes("카테고리"));
    addCategory?.addEventListener("click", (event) => {
      event.preventDefault();
      frameAlert(doc, "카테고리는 내 식물 목록 필터로 연결됩니다. 새 분류 저장은 다음 단계에서 계정 설정과 함께 확장합니다.");
    });
  }

  function renderDetailCollectionSidebar(doc: Document) {
    const aside = doc.querySelector("aside") as HTMLElement | null;
    const nav = aside?.querySelector("nav") as HTMLElement | null;
    if (!aside || !nav) return;

    const heading = aside.querySelector("h2");
    const subtitle = heading?.nextElementSibling as HTMLElement | null;
    if (heading) heading.textContent = "내 컬렉션";
    if (subtitle) subtitle.textContent = "분류별 식물 관리";

    const menuItems: { label: string; icon: string; action: DashboardPlantCategory | "chat" }[] = [
      { label: "내 식물", icon: "potted_plant", action: "indoor" },
      { label: "내 작물", icon: "agriculture", action: "crop" },
      { label: "화훼", icon: "local_florist", action: "ornamental" },
      { label: "최근 상담", icon: "forum", action: "chat" }
    ];

    nav.innerHTML = menuItems
      .map(
        (item, index) => `<div class="flex items-center gap-3 p-3 mb-1 cursor-pointer ${
          index === 0 ? "bg-growth-light dark:bg-tertiary-container text-primary font-bold" : "hover:bg-growth-light dark:hover:bg-tertiary-container text-on-surface-variant"
        } rounded-lg transition-all duration-200" data-detail-sidebar="${item.action}">
          <span class="material-symbols-outlined">${item.icon}</span>
          <span class="text-label-md font-label-md">${item.label}</span>
        </div>`
      )
      .join("");

    nav.querySelectorAll("[data-detail-sidebar]").forEach((item) => {
      item.addEventListener("click", (event) => {
        event.preventDefault();
        const action = (item as HTMLElement).dataset.detailSidebar as DashboardPlantCategory | "chat";
        if (action === "chat") {
          navigate("chat");
          return;
        }
        localStorage.setItem("farmhani_dashboard_filter", action);
        navigate("dashboard");
      });
    });

    const addButton = aside.querySelector("button");
    if (addButton) {
      addButton.innerHTML = `<span class="material-symbols-outlined">add</span>새 식물 추가`;
      addButton.addEventListener("click", (event) => {
        event.preventDefault();
        navigate("add");
      });
    }
  }

  function bindDetailEditButton(doc: Document) {
    if (doc.querySelector("[data-detail-edit-plant]")) return;
    const button = doc.createElement("button");
    button.type = "button";
    button.dataset.detailEditPlant = "true";
    button.className =
      "fixed right-6 bottom-20 z-50 inline-flex items-center gap-2 rounded-full bg-primary text-white px-4 py-3 text-label-md font-bold shadow-lg hover:brightness-95 transition-all";
    button.innerHTML = '<span class="material-symbols-outlined text-[18px]">edit</span>정보 수정';
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const plantId = getSelectedPlantId();
      if (!plantId) return;
      let plant = currentPlant && currentPlant.id === plantId ? currentPlant : null;
      if (!plant) {
        try {
          plant = await getPlant(plantId);
          currentPlant = plant;
        } catch (error) {
          if (!handleApiError(doc, error)) frameAlert(doc, "식물 정보를 불러오지 못했습니다.");
          return;
        }
      }
      showFormModal(
        doc,
        {
          title: "식물 정보 수정",
          description: "별명, 품종, 위치, 햇빛 환경을 최신 상태로 바꾸면 물주기 추천과 상담 정확도가 함께 올라갑니다.",
          submitLabel: "저장",
          fields: [
            { key: "name", label: "별명", value: plant.name, placeholder: "예: 초록이", required: true },
            { key: "species", label: "품종", value: plant.species ?? "", placeholder: "예: 몬스테라 델리시오사" },
            { key: "location", label: "키우는 위치", value: plant.location ?? "", placeholder: "예: 거실 창가" },
            { key: "sunlight", label: "햇빛 환경", value: plant.sunlight ?? "", placeholder: "예: 오전 직사광선" }
          ],
          photoField: {
            label: "대표 사진 변경",
            description: plant.imageUrl ? "현재 사진 유지 (바꾸려면 선택)" : "선택된 사진 없음"
          }
        },
        async (values, photoFile) => {
          try {
            let imageUrl: string | undefined;
            if (photoFile) {
              const photo = await uploadPlantPhoto(plantId, photoFile, `${values.name} 프로필 사진`);
              imageUrl = storagePathToPublicUrl(photo.storagePath);
            }
            await updatePlant(plantId, {
              name: values.name,
              species: values.species,
              location: values.location,
              sunlight: values.sunlight,
              ...(imageUrl ? { imageUrl } : {})
            });
            currentPlant = null;
            frameAlert(doc, photoFile ? "식물 정보와 대표 사진을 수정했습니다." : "식물 정보를 수정했습니다.");
            bindDetailData(doc);
          } catch (error) {
            if (!handleApiError(doc, error)) frameAlert(doc, "식물 정보 수정에 실패했습니다.");
          }
        }
      );
    });
    doc.body.appendChild(button);
  }

  function bindDetailDeleteButton(doc: Document) {
    if (doc.querySelector("[data-detail-delete-plant]")) return;
    const button = doc.createElement("button");
    button.type = "button";
    button.dataset.detailDeletePlant = "true";
    button.className =
      "fixed right-6 bottom-6 z-50 inline-flex items-center gap-2 rounded-full bg-diagnostic-red text-white px-4 py-3 text-label-md font-bold shadow-lg hover:brightness-95 transition-all";
    button.innerHTML = '<span class="material-symbols-outlined text-[18px]">delete</span>식물 삭제';
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const plantId = getSelectedPlantId();
      if (plantId) void removePlant(doc, plantId);
    });
    doc.body.appendChild(button);
  }

  function bindDetailData(doc: Document) {
    const plantId = getSelectedPlantId();
    if (!plantId || (hasSupabaseAuthConfig() && !hasAuthSession())) return;

    void getPlant(plantId)
      .then((plant) => {
        currentPlant = plant;
        const heroName = doc.querySelector("h1");
        const heroSpecies = heroName?.nextElementSibling;
        const primaryImage = plant.imageUrl || storagePathToPublicUrl(plant.photos?.[0]?.storagePath);
        if (heroName) heroName.textContent = plant.name;
        if (heroSpecies) heroSpecies.textContent = plant.species || "품종 미지정";
        const heroImage = doc.querySelector(".lg\\:col-span-5 img") as HTMLImageElement | null;
        if (heroImage) {
          if (primaryImage) {
            heroImage.src = primaryImage;
            heroImage.alt = `${plant.name} 사진`;
          } else {
            const placeholder = doc.createElement("div");
            placeholder.className = "w-full h-full min-h-[320px] bg-surface-container flex flex-col items-center justify-center text-on-surface-variant";
            placeholder.innerHTML = `<span class="material-symbols-outlined text-5xl mb-3">hide_image</span><span class="text-label-lg font-bold">사진 등록안함</span>`;
            heroImage.replaceWith(placeholder);
          }
        }
        const breadcrumb = Array.from(doc.querySelectorAll("span")).find((element) => normalizedText(element).includes("몬스테라 델리시오사"));
        if (breadcrumb) breadcrumb.textContent = plant.name;

        const overviewTitle = Array.from(doc.querySelectorAll("h2")).find((element) => normalizedText(element).includes("활력 개요"));
        const overviewCopy = overviewTitle?.nextElementSibling as HTMLElement | undefined;
        if (overviewCopy) {
          const logCount = plant.careLogs?.length ?? 0;
          const photoCount = plant.photos?.length ?? 0;
          overviewCopy.textContent = `${logCount}개의 관리 기록과 ${photoCount}장의 사진을 기준으로 확인 중입니다.`;
        }

        const aiTitle = Array.from(doc.querySelectorAll("h3")).find((element) => normalizedText(element).includes("AI 조언"));
        const aiCopy = aiTitle?.nextElementSibling as HTMLElement | undefined;
        if (aiTitle) aiTitle.textContent = `${plant.name}를 위한 AI 조언 받기`;
        if (aiCopy) aiCopy.textContent = "최근 사진과 관리 기록을 바탕으로 맞춤 조언을 확인합니다.";

        const journalTitle = Array.from(doc.querySelectorAll("h2")).find((element) => normalizedText(element).includes("성장 일지"));
        const journalCopy = journalTitle?.nextElementSibling as HTMLElement | undefined;
        if (journalCopy) journalCopy.textContent = `${plant.name}의 사진과 관리 기록입니다.`;

        const waterLog = [...(plant.careLogs ?? [])]
          .filter((log) => log.wateredAt)
          .sort((a, b) => String(b.wateredAt).localeCompare(String(a.wateredAt)))[0];
        const waterIcon = Array.from(doc.querySelectorAll("span.material-symbols-outlined")).find((element) => normalizedText(element) === "water_drop");
        const waterText = waterIcon?.parentElement?.parentElement?.querySelectorAll("p")[1] as HTMLElement | undefined;
        if (waterText) waterText.textContent = waterLog?.wateredAt ? formatDate(waterLog.wateredAt) : "기록 없음";

        const timeline = doc.querySelector(".space-y-12") as HTMLElement | null;
        if (timeline) {
          const careEntries = (plant.careLogs ?? []).map((log) => ({
            type: log.wateredAt ? "물주기" : "관리 기록",
            date: log.wateredAt || log.createdAt,
            title: log.wateredAt ? "물주기 기록" : "관리 메모",
            body: [log.leafCondition, log.soilCondition, log.memo].filter(Boolean).join(" · ") || "관리 기록을 남겼습니다.",
            image: ""
          }));
          const photoEntries = (plant.photos ?? []).map((photo) => ({
            type: "AI진단",
            date: photo.capturedAt || photo.createdAt,
            title: photo.note || "사진 기록",
            body: `${plant.name}의 상태 사진을 저장했습니다. 상담에서 사진 진단 근거로 활용할 수 있습니다.`,
            image: storagePathToPublicUrl(photo.storagePath) || ""
          }));
          const entries = [...careEntries, ...photoEntries]
            .sort((a, b) => String(b.date).localeCompare(String(a.date)))
            .slice(0, 8);

          const entryMatchesFilter = (entry: (typeof entries)[number], filter: string) => {
            if (filter === "전체") return true;
            if (filter === "물주기") return entry.type.includes("물주기");
            if (filter === "영양") return /영양|비료|퇴비|분갈이|양분/.test(entry.body);
            if (filter.includes("AI")) return entry.type.includes("AI") || /진단|상담|사진/.test(entry.body);
            return true;
          };

          const renderTimeline = (filter = "전체") => {
            const filtered = entries.filter((entry) => entryMatchesFilter(entry, filter));
            timeline.innerHTML = filtered.length
              ? filtered
                  .map(
                    (entry, index) => `<div class="relative flex flex-col md:flex-row items-start md:items-center">
                      <div class="${index % 2 === 0 ? "md:w-1/2 md:pr-12 md:text-right" : "md:w-1/2 md:ml-auto md:pl-12"} order-2 mt-4 md:mt-0">
                        <div class="bg-white p-6 rounded-2xl shadow-sm border border-outline-variant/20 hover:shadow-md transition-all">
                          <span class="text-label-sm text-primary font-bold block mb-2">${escapeHtml(formatDate(entry.date))} · ${escapeHtml(entry.type)}</span>
                          <h4 class="text-headline-md font-bold mb-2">${escapeHtml(entry.title)}</h4>
                          <p class="text-body-md text-on-surface-variant mb-4">${escapeHtml(entry.body)}</p>
                          ${
                            entry.image
                              ? `<div class="rounded-xl overflow-hidden h-44"><img alt="${escapeHtml(entry.title)}" class="w-full h-full object-cover" src="${escapeHtml(entry.image)}"></div>`
                              : ""
                          }
                        </div>
                      </div>
                      <div class="absolute left-[-24px] md:left-1/2 md:transform md:-translate-x-1/2 z-10 w-8 h-8 rounded-full bg-primary border-4 border-white flex items-center justify-center text-white shadow-sm order-1">
                        <span class="material-symbols-outlined text-[16px]">${entry.image ? "image" : "water_drop"}</span>
                      </div>
                    </div>`
                  )
                  .join("")
              : `<div class="bg-white p-8 rounded-2xl shadow-sm border border-outline-variant/20 text-center">
                  <p class="text-headline-sm font-bold text-on-surface mb-2">${escapeHtml(filter)} 기록이 없습니다.</p>
                  <p class="text-body-md text-on-surface-variant">사진을 추가하거나 물주기 기록을 남기면 이곳에 ${escapeHtml(plant.name)}의 기록이 쌓입니다.</p>
                </div>`;
          };

          renderTimeline("전체");
          Array.from(doc.querySelectorAll("button"))
            .filter((button) => ["전체", "물주기", "영양", "AI진단", "AI 진단"].includes(normalizedText(button)))
            .forEach((button) => {
              (button as HTMLButtonElement).onclick = (event) => {
                event.preventDefault();
                const filter = normalizedText(button);
                renderTimeline(filter);
              };
            });
        }
      })
      .catch((error) => {
        if (!handleApiError(doc, error)) console.warn("[Farmhani] detail load failed", error);
      });
  }

  function bindQuickCareButtons(doc: Document) {
    doc.querySelectorAll("button").forEach((button) => {
      const text = normalizedText(button);
      if (text.includes("물주기 기록")) {
        button.addEventListener("click", async (event) => {
          event.preventDefault();
          event.stopImmediatePropagation();
          const plantId = getSelectedPlantId();
          if (!plantId) return;
          try {
            await createCareLog(plantId, {
              wateredAt: todayDateInput(),
              leafCondition: "상세 화면에서 물주기를 기록함",
              soilCondition: "미기록",
              memo: "상세 화면 빠른 기록"
            });
            frameAlert(doc, "물주기 기록을 저장했습니다.");
            bindDetailData(doc);
          } catch (error) {
            if (!handleApiError(doc, error)) frameAlert(doc, "물주기 저장에 실패했습니다.");
          }
        });
      }
      if (text.includes("새 일지 작성")) {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopImmediatePropagation();
          const input = createHiddenFileInput(doc);
          input.click();
          input.addEventListener("change", async () => {
            const plantId = getSelectedPlantId();
            const file = input.files?.[0];
            if (!plantId || !file) return;
            try {
              await uploadPlantPhoto(plantId, file, "성장 일지 사진");
              frameAlert(doc, "성장 일지 사진을 저장했습니다.");
              bindDetailData(doc);
            } catch (error) {
              if (!handleApiError(doc, error)) frameAlert(doc, "사진 저장에 실패했습니다.");
            }
          });
        });
      }
      if (text === "edit") {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopImmediatePropagation();
          const plantId = getSelectedPlantId();
          if (!plantId) return;
          showTextInputModal(
            doc,
            {
              title: "활력 상태 기록",
              description: "오늘 보이는 잎, 줄기, 흙 상태를 짧게 남겨두면 다음 상담에서 함께 참고합니다.",
              placeholder: "예: 새잎은 잘 펴졌고 아래쪽 잎 끝이 조금 마른 상태예요.",
              submitLabel: "기록 저장"
            },
            async (memo) => {
              try {
                await createCareLog(plantId, {
                  wateredAt: undefined,
                  leafCondition: memo,
                  soilCondition: "미기록",
                  memo: "활력 개요 메모"
                });
                frameAlert(doc, "활력 기록을 저장했습니다.");
                bindDetailData(doc);
              } catch (error) {
                if (!handleApiError(doc, error)) frameAlert(doc, "활력 기록 저장에 실패했습니다.");
              }
            }
          );
        });
      }
    });
  }

  return { bindDetailData, bindDetailSidebar, renderDetailCollectionSidebar, bindQuickCareButtons, bindDetailEditButton, bindDetailDeleteButton };
}
