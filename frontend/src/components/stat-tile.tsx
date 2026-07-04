import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

export function StatTile({
  label,
  value,
  icon: Icon,
  tone = "default",
  hint,
}: {
  label: string;
  value: React.ReactNode;
  icon?: LucideIcon;
  tone?: "default" | "warning" | "destructive" | "success";
  hint?: string;
}) {
  return (
    <Card className="gap-3 py-4">
      <CardContent className="flex items-start justify-between gap-3 px-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {label}
          </span>
          <span
            className={cn(
              "text-2xl font-semibold tabular-nums",
              tone === "warning" && "text-warning",
              tone === "destructive" && "text-destructive",
              tone === "success" && "text-success"
            )}
          >
            {value}
          </span>
          {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
        </div>
        {Icon && (
          <div
            className={cn(
              "flex size-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground",
              tone === "warning" && "bg-warning/15 text-warning",
              tone === "destructive" && "bg-destructive/10 text-destructive",
              tone === "success" && "bg-success/15 text-success"
            )}
          >
            <Icon className="size-4.5" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
