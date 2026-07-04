import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-between p-8 sm:p-12">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          D-Transfert
        </Link>
        <div className="mx-auto w-full max-w-sm py-12">{children}</div>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} D-Transfert. Plateforme de gestion multi-entreprises.
        </p>
      </div>
      <div className="relative hidden overflow-hidden bg-primary lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,color-mix(in_oklch,var(--primary-foreground)_12%,transparent),transparent_60%)]" />
        <div className="flex h-full flex-col justify-end gap-4 p-12 text-primary-foreground">
          <blockquote className="max-w-md text-xl leading-relaxed font-medium text-balance">
            « Un seul solde partagé, des taux clairs, une confiance entre collaborateurs. »
          </blockquote>
          <p className="text-sm text-primary-foreground/70">
            Wallets, opérations nationales, collaborations et envois internationaux — au même endroit.
          </p>
        </div>
      </div>
    </div>
  );
}
