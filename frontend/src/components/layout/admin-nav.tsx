"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const ADMIN_NAV_ITEMS = [
  { href: "/admin", label: "Vue d'ensemble" },
  { href: "/admin/companies", label: "Entreprises" },
  { href: "/admin/platform-admins", label: "Comptes Super Admin" },
  { href: "/admin/audit-logs", label: "Journal d'audit" },
  { href: "/admin/system-logs", label: "Logs système" },
  { href: "/admin/settings", label: "Paramètres" },
];

export function AdminNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-0.5 px-3">
      {ADMIN_NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
