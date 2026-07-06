import Link from "next/link";
import { Settings2, ShieldCheck, Users } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function PlatformAdminOverview() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Espace Super Admin</h1>
        <p className="text-sm text-muted-foreground">
          Vue d&apos;ensemble de la plateforme. Ce compte n&apos;est lié à aucune entreprise.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="space-y-2">
            <ShieldCheck className="size-5 text-primary" />
            <CardTitle className="text-base">Accès plateforme</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Gère les entreprises, consulte les journaux d&apos;audit et supervise les accès globaux
            depuis les routes d&apos;administration.
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-2">
            <Users className="size-5 text-primary" />
            <CardTitle className="text-base">Connexion</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Matricule de connexion: <span className="font-medium text-foreground">MAT-AD-001</span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-2">
            <Settings2 className="size-5 text-primary" />
            <CardTitle className="text-base">Actions rapides</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Link href="/dashboard" className="font-medium text-foreground hover:underline">
              Ouvrir le tableau de bord plateforme
            </Link>
            <Link href="/notifications" className="font-medium text-foreground hover:underline">
              Voir les notifications
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
