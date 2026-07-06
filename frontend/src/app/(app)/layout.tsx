import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { getCompanyMe } from "@/lib/data/company";
import { getMe } from "@/lib/data/me";
import { getDashboard } from "@/lib/data/dashboard";
import { NAV_ITEMS, SUPER_ADMIN_NAV_ITEMS } from "@/lib/nav";
import { hasPermission } from "@/lib/permissions";
import { UnauthenticatedError } from "@/lib/api-error";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  let me: Awaited<ReturnType<typeof getMe>>;
  let companyName = "Plateforme D-Transfert";
  let unreadNotifications = 0;

  try {
    me = await getMe();
    // Super Admin users have no company_id: every company-scoped endpoint
    // (company, dashboard, notifications, ...) would reject them, so they
    // only ever see the platform-wide /admin section.
    if (!me.is_super_admin) {
      [companyName, unreadNotifications] = await Promise.all([
        getCompanyMe().then((company) => company.name),
        getDashboard().then((dashboard) => dashboard.unread_notifications_count),
      ]);
    }
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }

  const navItems = me.is_super_admin
    ? SUPER_ADMIN_NAV_ITEMS
    : NAV_ITEMS.filter(
        (item) =>
          item.requiredPermission === null ||
          hasPermission(me.permissions, me.is_owner, me.is_super_admin, item.requiredPermission)
      );

  const roleLabel = me.is_super_admin ? "Super Admin" : me.is_owner ? "Owner" : "Employé";

  return (
    <AppShell
      navItems={navItems}
      companyName={companyName}
      fullName={me.full_name}
      matricule={me.matricule}
      roleLabel={roleLabel}
      unreadNotifications={unreadNotifications}
      showNotifications={!me.is_super_admin}
    >
      {children}
    </AppShell>
  );
}
