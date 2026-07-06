// 날짜 포맷/입력 유틸리티
export function formatDate(value?: string | null) {
  if (!value) return "기록 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

export function todayDateInput() {
  return new Date().toISOString().slice(0, 10);
}

export function daysAgoDateInput(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}
