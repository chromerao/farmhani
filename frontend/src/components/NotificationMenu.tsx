import { useEffect, useRef, useState } from "react";
import { getWateringReminders } from "../api";
import type { DesignPage } from "../lib/constants";
import {
  getWateringNotifiedDate,
  isNotificationsEnabled,
  setNotificationsEnabled,
  setSelectedPlantId,
  setWateringNotifiedDate
} from "../lib/storage";
import type { WateringReminder } from "../types";

interface NotificationMenuProps {
  onNavigate: (page: DesignPage) => void;
  onOpenChecklist: () => void;
}

export function NotificationMenu({ onNavigate, onOpenChecklist }: NotificationMenuProps) {
  const menuRef = useRef<HTMLDetailsElement>(null);
  const [reminders, setReminders] = useState<WateringReminder[]>([]);
  const [enabled, setEnabled] = useState(() => isNotificationsEnabled() && typeof Notification !== "undefined" && Notification.permission === "granted");
  const [message, setMessage] = useState("");
  const supported = typeof window !== "undefined" && "Notification" in window;
  const dueReminders = reminders.filter((reminder) => reminder.status === "due");
  const visibleReminders = reminders.filter((reminder) => reminder.status === "due" || reminder.status === "upcoming").slice(0, 3);

  useEffect(() => {
    let active = true;
    getWateringReminders()
      .then((rows) => {
        if (active) setReminders(rows);
      })
      .catch(() => {
        if (active) setMessage("알림 목록을 불러오지 못했어요. 잠시 후 다시 확인해 주세요.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!enabled || !supported || Notification.permission !== "granted" || dueReminders.length === 0) return;
    const today = new Date().toISOString().slice(0, 10);
    if (getWateringNotifiedDate() === today) return;

    new Notification("Farm하니? 오늘의 식물 케어", {
      body: `물주기 확인이 필요한 식물이 ${dueReminders.length}개 있어요. 흙 상태부터 살펴보세요.`
    });
    setWateringNotifiedDate(today);
  }, [dueReminders.length, enabled, supported]);

  async function toggleNotifications() {
    setMessage("");
    if (!supported) {
      setMessage("이 브라우저에서는 알림을 사용할 수 없어요.");
      return;
    }
    if (Notification.permission === "denied") {
      setNotificationsEnabled(false);
      setEnabled(false);
      setMessage("브라우저 사이트 설정에서 알림 권한을 허용해 주세요.");
      return;
    }
    if (enabled) {
      setNotificationsEnabled(false);
      setEnabled(false);
      setMessage("물주기 알림을 껐어요. 목록은 계속 확인할 수 있습니다.");
      return;
    }

    const permission = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
    const nextEnabled = permission === "granted";
    setNotificationsEnabled(nextEnabled);
    setEnabled(nextEnabled);
    setMessage(nextEnabled ? "물주기 알림을 켰어요." : "알림 권한이 허용되지 않았어요.");
    if (nextEnabled) {
      new Notification("Farm하니? 알림이 켜졌어요", { body: "필요한 식물 케어를 놓치지 않도록 알려드릴게요." });
    }
  }

  function openPlant(reminder: WateringReminder) {
    menuRef.current?.removeAttribute("open");
    setSelectedPlantId(reminder.plantId);
    onNavigate("detail");
  }

  function openChecklist() {
    menuRef.current?.removeAttribute("open");
    onOpenChecklist();
  }

  return (
    <details className="notification-menu" ref={menuRef}>
      <summary aria-label={`알림 메뉴${dueReminders.length ? `, 확인 필요 ${dueReminders.length}건` : ""}`}>
        <span className="material-symbols-outlined" aria-hidden="true">notifications</span>
        {dueReminders.length > 0 && <span className="notification-badge" aria-hidden="true">{dueReminders.length > 9 ? "9+" : dueReminders.length}</span>}
      </summary>
      <div className="notification-popover">
        <div className="notification-heading">
          <div><strong>오늘의 알림</strong><small>식물 상태를 확인할 시점을 모았어요.</small></div>
          <button className={enabled ? "notification-toggle is-active" : "notification-toggle"} type="button" role="switch" aria-checked={enabled} onClick={toggleNotifications}>
            <span aria-hidden="true" />{enabled ? "알림 켜짐" : "알림 켜기"}
          </button>
        </div>

        {visibleReminders.length > 0 ? (
          <ul className="notification-list">
            {visibleReminders.map((reminder) => (
              <li key={reminder.plantId}>
                <button type="button" onClick={() => openPlant(reminder)}>
                  <span className={`notification-status status-${reminder.status}`}><span className="material-symbols-outlined" aria-hidden="true">water_drop</span></span>
                  <span><strong>{reminder.name}</strong><small>{reminder.status === "due" ? "물주기 전 흙 상태를 확인해 주세요." : "곧 물주기 확인 시점이에요."}</small></span>
                  <span className="material-symbols-outlined notification-arrow" aria-hidden="true">arrow_forward</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="notification-empty"><span className="material-symbols-outlined" aria-hidden="true">task_alt</span><div><strong>지금 확인할 알림이 없어요</strong><small>새로운 관리 시점이 생기면 여기에 알려드릴게요.</small></div></div>
        )}

        {message && <p className="notification-message" role="status">{message}</p>}
        <button className="notification-checklist" type="button" onClick={openChecklist}>전체 체크리스트 보기<span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span></button>
      </div>
    </details>
  );
}
