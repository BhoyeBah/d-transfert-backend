import { AppTopbar } from "@/components/layout/app-topbar";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import type { NavItem } from "@/lib/nav";

export function AppShell({
  navItems,
  companyName,
  fullName,
  matricule,
  roleLabel,
  unreadNotifications,
  children,
}: {
  navItems: NavItem[];
  companyName: string;
  fullName: string;
  matricule: string;
  roleLabel: string;
  unreadNotifications: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex">
        <div className="flex h-14 items-center px-5 text-sm font-semibold tracking-tight">
          D-Transfert
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          <SidebarNav items={navItems} />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar
          companyName={companyName}
          fullName={fullName}
          matricule={matricule}
          roleLabel={roleLabel}
          unreadNotifications={unreadNotifications}
          navItems={navItems}
        />
        <main className="flex-1 bg-muted/30 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
