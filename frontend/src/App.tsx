import { useEffect, useRef, useState } from "react";
import { deletePlant, getPlants, isAuthRequiredError } from "./api";
import type { ChatResponseMode, Plant } from "./types";
import type { DesignPage } from "./lib/constants";
import { SELECTED_PLANT_ID_KEY, getInitialPage, pageSources } from "./lib/constants";
import {
  frameAlert,
  removeAddPhotoSkipButton,
  removeCategoryAddButtons,
  removeChatConfidence,
  simplifyDashboardViewButtons
} from "./lib/dom";
import { getSelectedPlantId, getStoredChatResponseMode, setSelectedPlantId } from "./lib/storage";
import type { AppContext } from "./pages/context";
import { createChrome } from "./pages/chrome";
import { createLoginPage } from "./pages/login";
import { createAddPage } from "./pages/add";
import { createDashboardPage } from "./pages/dashboard";
import { createDetailPage } from "./pages/detail";
import { createChatPage } from "./pages/chat";

function App() {
  const [page, setPage] = useState<DesignPage>(getInitialPage);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const selectedSpeciesRef = useRef("");
  const profilePhotoRef = useRef<File | null>(null);
  const pendingChatPhotoRef = useRef<File | null>(null);
  const pendingChatPhotoNoteRef = useRef("");
  const forceNewChatSessionRef = useRef(false);
  const chatResponseModeRef = useRef<ChatResponseMode>(getStoredChatResponseMode());
  const dashboardPlantsRef = useRef<Plant[]>([]);

  useEffect(() => {
    const handleHashChange = () => {
      setPage(getInitialPage());
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function navigate(nextPage: DesignPage) {
    window.location.hash = nextPage;
    setPage(nextPage);
  }

  function handleApiError(doc: Document, error: unknown) {
    if (isAuthRequiredError(error)) {
      frameAlert(doc, "로그인 세션이 없습니다. 로그인 후 다시 시도해 주세요.");
      navigate("login");
      return true;
    }
    return false;
  }

  async function removePlant(doc: Document, plantId: string) {
    const ok = doc.defaultView?.confirm("이 식물을 삭제할까요? 관리 기록과 상담 연결 정보도 더 이상 목록에서 보이지 않습니다.");
    if (!ok) return;

    try {
      await deletePlant(plantId);
      if (getSelectedPlantId() === plantId) {
        localStorage.removeItem(SELECTED_PLANT_ID_KEY);
      }
      frameAlert(doc, "식물을 삭제했습니다.");
      if (page === "detail") {
        navigate("dashboard");
        return;
      }
      void dashboardPage.bindDashboardData(doc);
    } catch (error) {
      if (!handleApiError(doc, error)) {
        frameAlert(doc, `식물 삭제에 실패했습니다. ${error instanceof Error ? error.message : ""}`);
      }
    }
  }

  async function resolvePlantId(doc: Document) {
    const selected = getSelectedPlantId();
    if (selected) return selected;

    const plants = await getPlants();
    if (plants[0]?.id) {
      setSelectedPlantId(plants[0].id);
      return plants[0].id;
    }

    frameAlert(doc, "등록된 식물이 없습니다. 먼저 식물을 추가해 주세요.");
    navigate("add");
    throw new Error("No plant profile exists.");
  }

  const ctx: AppContext = {
    page,
    navigate,
    handleApiError,
    removePlant,
    resolvePlantId,
    selectedSpeciesRef,
    profilePhotoRef,
    pendingChatPhotoRef,
    pendingChatPhotoNoteRef,
    forceNewChatSessionRef,
    chatResponseModeRef,
    dashboardPlantsRef
  };

  const chrome = createChrome(ctx);
  const loginPage = createLoginPage(ctx);
  const addPage = createAddPage(ctx);
  const dashboardPage = createDashboardPage(ctx);
  const detailPage = createDetailPage(ctx);
  const chatPage = createChatPage(ctx);

  function bindFrame() {
    const frame = frameRef.current;
    const doc = frame?.contentDocument;
    if (!doc) return;
    if (page !== "chat") {
      pendingChatPhotoRef.current = null;
      pendingChatPhotoNoteRef.current = "";
    }

    removeCategoryAddButtons(doc);
    removeChatConfidence(doc);
    chrome.bindGenericControls(doc);
    chrome.bindFrameNavigation(doc);
    chrome.bindLogoHome(doc);
    chrome.bindSessionControls(doc);
    chrome.bindTopSearch(doc);
    if (page === "login") loginPage.bindAuth(doc);
    if (page === "dashboard") {
      simplifyDashboardViewButtons(doc);
      void dashboardPage.bindDashboardData(doc);
      dashboardPage.bindDashboardUpload(doc);
    }
    if (page === "add") {
      profilePhotoRef.current = null;
      selectedSpeciesRef.current = "";
      removeAddPhotoSkipButton(doc);
      addPage.bindSpeciesAutocomplete(doc);
      addPage.bindAddDateShortcuts(doc);
      addPage.bindAddPhotoPicker(doc);
      addPage.bindAddPlantSubmit(doc);
    }
    if (page === "detail") {
      detailPage.bindDetailData(doc);
      detailPage.bindDetailSidebar(doc);
      detailPage.renderDetailCollectionSidebar(doc);
      detailPage.bindQuickCareButtons(doc);
      detailPage.bindDetailEditButton(doc);
      detailPage.bindDetailDeleteButton(doc);
    }
    if (page === "chat") {
      chatPage.bindChatModelInfo(doc);
      chatPage.bindChatModeSelector(doc);
      chatPage.initializeChatCanvas(doc);
      chatPage.bindChatPhotoPicker(doc);
      chatPage.bindChatImageDropAndPaste(doc);
      chatPage.bindChatSubmit(doc);
      chatPage.bindChatQuickPrompts(doc);
      void chatPage.renderChatSessions(doc, { autoLoadLast: true });
    }
  }

  return (
    <iframe
      ref={frameRef}
      className="design-frame"
      key={page}
      src={pageSources[page]}
      title="Farm하니 UI"
      onLoad={bindFrame}
    />
  );
}

export default App;
