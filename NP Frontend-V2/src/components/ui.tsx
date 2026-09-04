import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-surface border border-border rounded-xl ${className}`}>{children}</div>
  );
}

export function Badge({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${className}`}
    >
      {children}
    </span>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="bg-danger/10 border border-danger/30 text-danger text-sm rounded-xl px-4 py-3">
      {message}
    </div>
  );
}
