import { hasSupabaseAuthConfig, signInWithPassword, signUpWithPassword } from "../api";
import { createHiddenFileInput, fileToResizedDataUrl, frameAlert, normalizedText } from "../lib/dom";
import { setUserProfilePhoto } from "../lib/storage";
import type { AppContext } from "./context";

export function createLoginPage(ctx: AppContext) {
  const { navigate } = ctx;

  function bindAuth(doc: Document) {
    const submit = doc.getElementById("auth-submit") as HTMLButtonElement | null;
    const email = doc.getElementById("email") as HTMLInputElement | null;
    const password = doc.getElementById("password") as HTMLInputElement | null;
    const toggle = doc.getElementById("toggle-auth") as HTMLButtonElement | null;
    if (!submit) return;

    let isLogin = true;
    let selectedProfilePhoto: File | null = null;
    const profileUpload = doc.createElement("div");
    profileUpload.dataset.profileUpload = "true";
    profileUpload.className = "hidden rounded-2xl border border-outline-variant/20 bg-surface-container-low p-4 space-y-3";
    profileUpload.innerHTML = `
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-label-md font-bold text-on-surface">프로필 사진</p>
          <p class="text-label-sm text-on-surface-variant">가입 후 상단 네비게이션에 표시됩니다.</p>
        </div>
        <button type="button" class="px-3 py-2 rounded-full bg-growth-light text-primary text-label-sm font-bold" data-profile-photo-pick>사진 선택</button>
      </div>
      <p class="text-label-sm text-outline" data-profile-photo-label>선택된 사진 없음</p>`;
    const authFormHost = submit.parentElement;
    authFormHost?.insertBefore(profileUpload, submit);
    const profileInput = createHiddenFileInput(doc);
    profileUpload.querySelector("[data-profile-photo-pick]")?.addEventListener("click", (event) => {
      event.preventDefault();
      profileInput.click();
    });
    profileInput.addEventListener("change", () => {
      selectedProfilePhoto = profileInput.files?.[0] ?? null;
      const label = profileUpload.querySelector("[data-profile-photo-label]");
      if (label) label.textContent = selectedProfilePhoto ? selectedProfilePhoto.name : "선택된 사진 없음";
    });

    if (toggle) {
      const cleanToggle = toggle.cloneNode(true) as HTMLButtonElement;
      toggle.replaceWith(cleanToggle);
      cleanToggle.addEventListener("click", (event) => {
        event.preventDefault();
        isLogin = !isLogin;
        profileUpload.classList.toggle("hidden", isLogin);
        const title = doc.querySelector("h2");
        const subtitle = title?.nextElementSibling;
        if (title) title.textContent = isLogin ? "시작하기" : "회원가입";
        if (subtitle) {
          subtitle.textContent = isLogin ? "회원이 되어 스마트한 식물 생활을 시작하세요." : "식물 관리의 시작, Farm하니? 와 함께하세요.";
        }
        submit.innerHTML = isLogin
          ? '로그인 <span class="material-symbols-outlined text-[18px]" data-icon="arrow_forward">arrow_forward</span>'
          : '가입하기 <span class="material-symbols-outlined text-[18px]" data-icon="person_add">person_add</span>';
        cleanToggle.textContent = isLogin ? "회원가입" : "로그인하기";
      });
    }

    doc.querySelectorAll("button").forEach((button) => {
      if (normalizedText(button).includes("비밀번호 찾기")) {
        button.addEventListener("click", () => frameAlert(doc, "비밀번호 재설정은 Supabase Auth 메일 설정 후 연결 예정입니다."));
      }
    });

    submit.addEventListener("click", async (event) => {
      event.preventDefault();

      if (!hasSupabaseAuthConfig()) {
        if (!isLogin && selectedProfilePhoto) {
          setUserProfilePhoto(await fileToResizedDataUrl(selectedProfilePhoto));
        }
        navigate("dashboard");
        return;
      }

      const emailValue = email?.value.trim() ?? "";
      const passwordValue = password?.value ?? "";
      if (!emailValue || !passwordValue) {
        frameAlert(doc, "이메일과 비밀번호를 입력해 주세요.");
        return;
      }

      submit.setAttribute("disabled", "true");
      try {
        if (isLogin) {
          await signInWithPassword(emailValue, passwordValue);
          navigate("dashboard");
          return;
        }

        const result = await signUpWithPassword(emailValue, passwordValue);
        if (selectedProfilePhoto) {
          setUserProfilePhoto(await fileToResizedDataUrl(selectedProfilePhoto));
        }
        if (!result.access_token) {
          frameAlert(doc, "회원가입은 완료됐지만 세션이 발급되지 않았습니다. Supabase 이메일 인증을 완료한 뒤 로그인해 주세요.");
          isLogin = true;
          submit.innerHTML = '로그인 <span class="material-symbols-outlined text-[18px]" data-icon="arrow_forward">arrow_forward</span>';
          return;
        }
        navigate("dashboard");
      } catch (error) {
        frameAlert(doc, `인증에 실패했습니다. ${error instanceof Error ? error.message : ""}`);
      } finally {
        submit.removeAttribute("disabled");
      }
    });
  }

  return { bindAuth };
}
