"use client";

import { useActionState, useEffect } from "react";
import Link from "next/link";
import { useFormStatus } from "react-dom";
import { toast } from "sonner";

import { loginAction } from "@/actions/auth";
import { initialActionState } from "@/lib/action-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" className="w-full" disabled={pending}>
      {pending ? "Connexion..." : "Se connecter"}
    </Button>
  );
}

export function LoginForm({
  next,
  registeredMatricule,
  resetSuccess,
}: {
  next?: string;
  registeredMatricule?: string;
  resetSuccess?: boolean;
}) {
  const [state, action] = useActionState(loginAction, initialActionState);

  useEffect(() => {
    if (registeredMatricule) {
      toast.success("Entreprise créée avec succès.", {
        description: `Votre matricule : ${registeredMatricule}`,
      });
    }
    if (resetSuccess) {
      toast.success("Mot de passe réinitialisé, vous pouvez vous connecter.");
    }
  }, [registeredMatricule, resetSuccess]);

  return (
    <form action={action} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-xl font-semibold tracking-tight">Connexion</h1>
        <p className="text-sm text-muted-foreground">
          Owner : matricule entreprise. Employé : matricule personnel attribué par votre entreprise.
        </p>
      </div>

      {next && <input type="hidden" name="next" value={next} />}

      <div className="grid gap-1.5">
        <Label htmlFor="matricule">Matricule</Label>
        <Input id="matricule" name="matricule" placeholder="DT-XXXXXXXX" autoComplete="username" required />
        {state.fieldErrors?.matricule && (
          <p className="text-sm text-destructive">{state.fieldErrors.matricule[0]}</p>
        )}
      </div>

      <div className="grid gap-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Mot de passe</Label>
          <Link href="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground">
            Mot de passe oublié ?
          </Link>
        </div>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
        {state.fieldErrors?.password && (
          <p className="text-sm text-destructive">{state.fieldErrors.password[0]}</p>
        )}
      </div>

      {state.status === "error" && state.message && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{state.message}</p>
      )}

      <SubmitButton />

      <p className="text-center text-sm text-muted-foreground">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-medium text-foreground hover:underline">
          Inscrire votre entreprise
        </Link>
      </p>
    </form>
  );
}
