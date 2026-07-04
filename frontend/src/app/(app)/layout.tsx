import { redirect } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { getCompanyMe } from "@/lib/data/company";
import { getMe } from "@/lib/data/me";
import { getDashboard } from "@/lib/data/dashboard";
import { NAV_ITEMS } from "@/lib/nav";
import { hasPermission } from "@/lib/permissions";
import { UnauthenticatedError } from "@/lib/api-error";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  let me: Awaited<ReturnType<typeof getMe>>;
  let companyName: string;
  let unreadNotifications = 0;

  try {
    [me, companyName] = await Promise.all([
      getMe(),
      getCompanyMe().then((company) => company.name),
    ]);
    unreadNotifications = (await getDashboard()).unread_notifications_count;
  } catch (error) {
    if (error instanceof UnauthenticatedError) {
      redirect("/login");
    }
    throw error;
  }

  const navItems = NAV_ITEMS.filter(
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
    >
      {children}
    </AppShell>
  );
}
