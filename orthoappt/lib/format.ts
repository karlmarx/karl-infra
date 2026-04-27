export const APPOINTMENT_DATE = new Date("2026-04-28T09:00:00-04:00");

export interface Countdown {
  passed: boolean;
  label: string;
}

export function appointmentCountdown(now: Date = new Date()): Countdown {
  const diffMs = APPOINTMENT_DATE.getTime() - now.getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  if (diffMs < -dayMs) {
    return { passed: true, label: "Past appointment — Tuesday April 28, 2026" };
  }
  if (diffMs < 0) {
    return { passed: false, label: "Today is appointment day" };
  }
  const days = Math.floor(diffMs / dayMs);
  if (days === 0) return { passed: false, label: "Tomorrow — Tuesday April 28" };
  if (days === 1) return { passed: false, label: "1 day until appointment" };
  return { passed: false, label: `${days} days until appointment` };
}

export function formatBuildTime(iso: string): string {
  const d = new Date(iso);
  const opts: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  };
  return d.toLocaleString("en-US", opts);
}
