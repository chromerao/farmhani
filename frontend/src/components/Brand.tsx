interface BrandProps {
  inverse?: boolean;
}

export function Brand({ inverse = false }: BrandProps) {
  return (
    <span className={`brand ${inverse ? "brand-inverse" : ""}`}>
      <svg className="brand-logo" viewBox="0 0 32 34" aria-hidden="true">
        <path d="M15 13.5V8.4c0-3.7 2.7-6.2 7.5-6.4.1 4.9-2.5 7.6-7.5 7.8" />
        <path d="M14.7 10.6C9.9 10.5 7.1 7.8 7.2 3c4.7.2 7.4 2.6 7.5 6.4" />
        <path d="M5 13.2h22v5H5z" />
        <path d="M8 19.7h16L22.4 30H9.6L8 19.7z" />
      </svg>
      <span className="brand-copy">
        <strong>Farm하니?</strong>
      </span>
    </span>
  );
}
