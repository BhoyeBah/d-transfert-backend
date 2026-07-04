import type { Metadata } from "next";

import { ResetPasswordForm } from "./reset-password-form";

export const metadata: Metadata = { title: "Réinitialiser le mot de passe — D-Transfert" };

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ matricule?: string }>;
}) {
  const params = await searchParams;
  return <ResetPasswordForm matricule={params.matricule} />;
}
