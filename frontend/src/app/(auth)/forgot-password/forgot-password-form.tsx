"use client";

import { useActionState } from "react";
import Link from "next/link";
import { useFormStatus } from "react-dom";

import { forgotPasswordAction } from "@/actions/auth";
import { initialActionState } from "@/lib/action-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" className="w-full" disabled={pending}>
      {pending ? "Envoi..." : "Recevoir un code"}
    </Button>
  );
}

export function ForgotPasswordForm() {
  const [state, action] = useActionState(forgotPasswordAction, initialActionState);

  return (
    <form action={action} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-xl font-semibold tracking-tight">Mot de passe oublié</h1>
        <p className="text-sm text-muted-foreground">
          Un code de réinitialisation valable 10 minutes sera envoyé au titulaire du matricule.
        </p>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="matricule">Matricule</Label>
        <Input id="matricule" name="matricule" placeholder="DT-XXXXXXXX" required />
        {state.fieldErrors?.matricule && (
          <p className="text-sm text-destructive">{state.fieldErrors.matricule[0]}</p>
        )}
      </div>

      {state.status === "error" && state.message && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{state.message}</p>
      )}

      <SubmitButton />

      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-foreground hover:underline">
          Retour à la connexion
        </Link>
      </p>
    </form>
  );
}
