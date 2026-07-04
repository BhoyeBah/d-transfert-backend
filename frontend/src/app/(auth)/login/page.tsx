import type { Metadata } from "next";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Connexion — D-Transfert" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; registered?: string; reset?: string }>;
}) {
  const params = await searchParams;

  return (
    <LoginForm
      next={params.next}
      registeredMatricule={params.registered}
      resetSuccess={params.reset === "success"}
    />
  );
}
