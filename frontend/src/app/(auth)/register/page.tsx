import type { Metadata } from "next";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "Inscription — D-Transfert" };

export default function RegisterPage() {
  return <RegisterForm />;
}
