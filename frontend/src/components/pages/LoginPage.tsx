import { useState, type FormEvent } from "react";
import { hasSupabaseAuthConfig, isDevelopmentMockMode, signInWithPassword, signUpWithPassword } from "../../api";
import dashboardPlantImage from "../../assets/dashboard-plant.webp";
import { Brand } from "../Brand";

interface LoginPageProps {
  onAuthenticated: () => void;
}

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const configured = hasSupabaseAuthConfig();
  const previewMode = isDevelopmentMockMode();

  function changeMode(nextMode: "login" | "signup") {
    setMode(nextMode);
    setError("");
    setStatus("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setError("");
    setStatus("");
    setSubmitting(true);

    try {
      if (mode === "signup") {
        const response = await signUpWithPassword(email.trim(), password);
        if (response.access_token) {
          onAuthenticated();
          return;
        }
        setStatus("가입 요청을 완료했습니다. 이메일 인증 후 로그인해 주세요.");
        setMode("login");
        return;
      }

      await signInWithPassword(email.trim(), password);
      onAuthenticated();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "로그인 처리 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <a className="auth-brand-link" href="#login" aria-label="Farm하니 로그인">
        <Brand />
      </a>

      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="auth-panel-inner">
          <div className="auth-card">
            <span className="eyebrow">WELCOME TO FARMHANI</span>
            <h1 id="auth-title">{mode === "login" ? "다시 만나 반가워요" : "식물과의 기록을 시작해요"}</h1>
            <p>{mode === "login" ? "오늘 필요한 케어부터 지난 성장 기록까지, 내 식물의 하루를 이어서 살펴보세요." : "계정을 만들면 식물별 관리 기록과 상담 내역, 물주기 알림 설정을 안전하게 이어갈 수 있어요."}</p>

            <div className="auth-mode-tabs" role="tablist" aria-label="계정 접근 방식">
              <button className={mode === "login" ? "is-active" : ""} type="button" role="tab" aria-selected={mode === "login"} onClick={() => changeMode("login")}>로그인</button>
              <button className={mode === "signup" ? "is-active" : ""} type="button" role="tab" aria-selected={mode === "signup"} onClick={() => changeMode("signup")}>회원가입</button>
            </div>

            {!configured && !previewMode && (
              <div className="alert alert-error" role="alert">
                로그인 서비스 설정이 없습니다. 배포 환경의 Supabase 공개 설정을 확인해 주세요.
              </div>
            )}
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            {status && <div className="alert alert-success" role="status">{status}</div>}

            <form className="stack-form" onSubmit={handleSubmit} aria-busy={submitting}>
              <label className="field">
                <span>이메일</span>
                <span className="input-with-icon">
                  <span className="material-symbols-outlined" aria-hidden="true">mail</span>
                  <input autoComplete="email" disabled={submitting} inputMode="email" name="email" onChange={(event) => setEmail(event.target.value)} placeholder="example@farm.com" required type="email" value={email} />
                </span>
              </label>
              <label className="field">
                <span>비밀번호</span>
                <span className="input-with-icon">
                  <span className="material-symbols-outlined" aria-hidden="true">lock</span>
                  <input autoComplete={mode === "login" ? "current-password" : "new-password"} disabled={submitting} minLength={mode === "signup" ? 8 : undefined} name="password" onChange={(event) => setPassword(event.target.value)} placeholder={mode === "login" ? "비밀번호 입력" : "8자 이상 입력"} required type="password" value={password} />
                </span>
                <small className="field-hint">{mode === "login" ? "가입할 때 사용한 비밀번호를 입력해 주세요." : "영문, 숫자 등을 조합해 8자 이상 입력해 주세요."}</small>
              </label>
              <button className="button button-primary button-block" disabled={!configured || submitting} type="submit">
                {submitting ? (mode === "login" ? "로그인 확인 중…" : "계정 만드는 중…") : mode === "login" ? "로그인" : "가입하기"}
                <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
              </button>
            </form>

            {previewMode && <div className="preview-access"><span>개발용 mock 데이터로 전체 기능을 확인할 수 있어요.</span><button className="button button-secondary button-block" type="button" onClick={onAuthenticated}>체험 화면 시작<span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span></button></div>}
          </div>
          <p className="auth-legal">계속하면 Farm하니의 이용약관 및 개인정보 처리방침에 동의하게 됩니다.</p>
        </div>
      </section>

      <section className="auth-hero" aria-labelledby="auth-hero-title">
        <div className="auth-hero-glow" />
        <div className="auth-hero-content">
          <header className="auth-hero-copy">
            <span className="auth-kicker"><span className="material-symbols-outlined" aria-hidden="true">verified</span> 기록이 쌓일수록 선명해지는 식물 생활</span>
            <h2 id="auth-hero-title">작은 변화를 발견하는<br />나만의 초록 루틴</h2>
            <p>사진과 물주기, 잎과 흙의 변화를 한곳에 기록하세요. Farm하니가 오늘 확인할 일과 근거 있는 다음 행동을 보기 좋게 정리합니다.</p>
          </header>

          <div className="auth-hero-showcase">
            <ul className="auth-benefits" aria-label="Farm하니 주요 기능">
              <li><span className="material-symbols-outlined" aria-hidden="true">photo_camera</span><div><strong>성장 타임라인</strong><small>사진과 관찰 메모를 날짜별로 비교</small></div></li>
              <li><span className="material-symbols-outlined" aria-hidden="true">event_available</span><div><strong>오늘의 케어</strong><small>물주기와 관찰 시점을 놓치지 않게 안내</small></div></li>
              <li><span className="material-symbols-outlined" aria-hidden="true">menu_book</span><div><strong>근거 있는 상담</strong><small>답변마다 참고 자료와 관찰 기준 제공</small></div></li>
            </ul>

            <article className="auth-plant-card" aria-label="식물 관리 화면 미리보기">
              <img className="auth-hero-plant" src={dashboardPlantImage} alt="햇빛이 드는 실내에서 자라는 몬스테라와 관엽식물" />
              <div className="auth-plant-card-body">
                <div>
                  <small>오늘의 관찰</small>
                  <strong>몬티의 새 잎이 펼쳐졌어요</strong>
                </div>
                <span className="preview-status">기록 완료</span>
              </div>
              <dl className="auth-plant-metrics">
                <div><dt><span className="material-symbols-outlined" aria-hidden="true">eco</span>이번 주 컨디션</dt><dd>안정적 · 92%</dd></div>
                <div><dt><span className="material-symbols-outlined" aria-hidden="true">water_drop</span>다음 물주기</dt><dd>흙 상태 먼저 확인</dd></div>
              </dl>
            </article>
          </div>
        </div>
      </section>
    </main>
  );
}
