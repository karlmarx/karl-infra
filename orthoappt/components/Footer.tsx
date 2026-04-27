"use client";

import { appointmentCountdown, formatBuildTime } from "@/lib/format";
import { useEffect, useState } from "react";

interface Props {
  builtAt: string;
}

export function Footer({ builtAt }: Props) {
  const [cd, setCd] = useState(() => appointmentCountdown());

  useEffect(() => {
    const id = window.setInterval(() => setCd(appointmentCountdown()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <footer className="mt-16 mb-10 px-4 text-xs text-ink-faint text-center no-print">
      <div className="font-medium text-ink-muted">{cd.label}</div>
      <div className="mt-1">
        Tuesday April 28, 2026 · Dr. Almodovar
      </div>
      <div className="mt-2">Built {formatBuildTime(builtAt)}</div>
    </footer>
  );
}
