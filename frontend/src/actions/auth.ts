"use server";

import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api-error";
import { serverFetch } from "@/lib/api";
import type { ActionState } from "@/lib/action-state";
import { clearAuthCookies, getRefreshToken, setAuthCookies } from "@/lib/session";
import {
  forgotPasswordSchema,
  loginSchema,
  registerSchema,
  resetPasswordSchema,
} from "@/lib/validation/auth";

type TokenResponse = { access_token: string; refresh_token: string };
type RegisterResponse = { company_id: string; registration_code: string; owner_user_id: string };

export async function registerAction(_prevState: ActionState, formData: FormData): Promise<ActionState> {
  const parsed = registerSchema.safeParse({
    company_name: formData.get("company_name"),
    company_phone: formData.get("company_phone"),
    address: formData.get("address"),
    default_currency: formData.get("default_currency"),
    owner_full_name: formData.get("owner_full_name"),
    password: formData.get("password"),
    password_confirmation: formData.get("password_confirmation"),
  });

  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  let registration: RegisterResponse;
  try {
    registration = await serverFetch<RegisterResponse>("/api/v1/auth/register", {
      method: "POST",
      body: { ...parsed.data, address: parsed.data.address || null },
      skipAuth: true,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  let tokens: TokenResponse;
  try {
    tokens = await serverFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { matricule: registration.registration_code, password: parsed.data.password },
      skipAuth: true,
    });
  } catch {
    redirect(`/login?registered=${registration.registration_code}`);
  }

  await setAuthCookies(tokens.access_token, tokens.refresh_token);
  redirect("/dashboard");
}

export async function loginAction(_prevState: ActionState, formData: FormData): Promise<ActionState> {
  const parsed = loginSchema.safeParse({
    matricule: formData.get("matricule"),
    password: formData.get("password"),
  });

  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  let tokens: TokenResponse;
  try {
    tokens = await serverFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: parsed.data,
      skipAuth: true,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  await setAuthCookies(tokens.access_token, tokens.refresh_token);
  const next = String(formData.get("next") ?? "/dashboard");
  redirect(next.startsWith("/") ? next : "/dashboard");
}

export async function logoutAction() {
  await clearAuthCookies();
  redirect("/login");
}

export async function forgotPasswordAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const parsed = forgotPasswordSchema.safeParse({ matricule: formData.get("matricule") });
  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/auth/forgot-password", {
      method: "POST",
      body: parsed.data,
      skipAuth: true,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  redirect(`/reset-password?matricule=${encodeURIComponent(parsed.data.matricule)}`);
}

export async function resetPasswordAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const parsed = resetPasswordSchema.safeParse({
    matricule: formData.get("matricule"),
    otp_code: formData.get("otp_code"),
    new_password: formData.get("new_password"),
    new_password_confirmation: formData.get("new_password_confirmation"),
  });

  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/auth/reset-password", {
      method: "POST",
      body: parsed.data,
      skipAuth: true,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  redirect("/login?reset=success");
}

export async function ensureRefreshTokenPresent() {
  const token = await getRefreshToken();
  return Boolean(token);
}
