interface PageStateProps {
  kind: "loading" | "empty" | "error";
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function PageState({ kind, title, description, actionLabel, onAction }: PageStateProps) {
  if (kind === "loading") {
    return (
      <section className="page-state page-state-loading" aria-live="polite" aria-busy="true">
        <div className="loading-visual" aria-hidden="true">
          <span className="loading-ring" />
          <span className="material-symbols-outlined">potted_plant</span>
        </div>
        <h2>{title}</h2>
        <p>{description || "식물 기록을 차분히 정리하고 있어요."}</p>
        <div className="loading-lines" aria-hidden="true"><span /><span /><span /></div>
      </section>
    );
  }

  return (
    <section className={`page-state page-state-${kind}`} aria-live={kind === "error" ? "assertive" : "polite"}>
      <span className="page-state-icon" aria-hidden="true">
        <span className="material-symbols-outlined">
          {kind === "error" ? "error" : "potted_plant"}
        </span>
      </span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {actionLabel && onAction && (
        <button className="button button-primary" type="button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </section>
  );
}
