// 대시보드 식물 카드 HTML 템플릿
import type { Plant } from "../types";
import { escapeHtml } from "./dom";
import { formatDate } from "./format";

export function plantCardHtml(plant: Plant, index: number) {
  const image = plant.imageUrl;
  const status = plant.healthScore == null ? "관찰 전" : plant.healthScore < 70 ? "주의 필요" : "건강함";
  const badgeClass =
    status === "주의 필요"
      ? "bg-diagnostic-red/10 border border-diagnostic-red/20 text-diagnostic-red"
      : status === "관찰 전"
        ? "bg-white/80 text-on-surface-variant"
        : "bg-white/80 text-primary";

  return `<div class="bg-surface-container-lowest rounded-3xl overflow-hidden shadow-sm hover:shadow-md transition-all group cursor-pointer border border-outline-variant/10" data-plant-card="${escapeHtml(plant.id)}">
    <div class="relative h-48 overflow-hidden">
      ${
        image
          ? `<img alt="${escapeHtml(plant.name)} 식물 사진" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" src="${escapeHtml(image)}">`
          : `<div class="w-full h-full bg-surface-container flex flex-col items-center justify-center text-on-surface-variant">
              <span class="material-symbols-outlined text-4xl mb-2">hide_image</span>
              <span class="text-label-md font-bold">사진 등록안함</span>
            </div>`
      }
      <div class="absolute top-4 right-4 ${badgeClass} backdrop-blur-md px-3 py-1 rounded-full text-label-sm font-bold flex items-center gap-1">
        <span class="material-symbols-outlined text-[14px]" style="font-variation-settings: 'FILL' 1;">${status === "주의 필요" ? "warning" : status === "관찰 전" ? "visibility" : "check_circle"}</span>
        ${status}
      </div>
    </div>
    <div class="p-6">
      <h3 class="text-headline-sm font-headline-md mb-1">${escapeHtml(plant.name)}</h3>
      <p class="text-label-sm text-on-surface-variant mb-4">${escapeHtml(plant.species || "품종 미지정")} · ${escapeHtml(plant.location || "위치 미지정")}</p>
      <div class="flex items-center justify-between border-t border-outline-variant/10 pt-4">
        <div class="flex flex-col">
          <span class="text-[10px] uppercase tracking-wider text-outline">등록일</span>
          <span class="text-label-md font-medium">${formatDate(plant.createdAt)}</span>
          <span class="text-[10px] uppercase tracking-wider text-tertiary mt-2">다음 관리</span>
          <span class="text-label-sm font-medium text-tertiary">${escapeHtml(plant.nextTask || "관찰 기록 대기")}</span>
        </div>
        <button class="w-10 h-10 rounded-full bg-growth-light text-primary flex items-center justify-center hover:bg-primary hover:text-white transition-all" data-water-plant="${escapeHtml(plant.id)}" title="오늘 물주기 기록">
          <span class="material-symbols-outlined">water_drop</span>
        </button>
      </div>
    </div>
  </div>`;
}

export function addPlantCardHtml() {
  return `<div class="border-2 border-dashed border-outline-variant rounded-3xl flex flex-col items-center justify-center p-6 hover:bg-surface-container-low transition-all cursor-pointer group" data-add-plant="true">
    <div class="w-16 h-16 rounded-full bg-growth-light flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
      <span class="material-symbols-outlined text-primary text-3xl">add</span>
    </div>
    <p class="text-headline-sm font-headline-md text-tertiary">새 식물 추가</p>
    <p class="text-label-sm text-on-surface-variant text-center mt-2">나만의 정원을 넓혀보세요</p>
  </div>`;
}
