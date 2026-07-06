"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { mergeEntriesAction } from "@/actions/entries";
import { formatDate, formatMoney } from "@/lib/format";
import type { Entry } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/status-badge";

const MERGEABLE_STATUSES = new Set(["unallocated", "partially_allocated"]);

function availableSummary(entry: Entry) {
  const parts = Object.entries(entry.available_by_currency).map(([currency, amount]) =>
    formatMoney(amount, currency)
  );
  return parts.length > 0 ? parts.join(" · ") : "—";
}

export function EntriesTable({ entries }: { entries: Entry[] }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function toggle(entryId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) next.delete(entryId);
      else next.add(entryId);
      return next;
    });
  }

  function merge() {
    startTransition(async () => {
      const result = await mergeEntriesAction([...selected]);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success(`Entrées fusionnées en ${result.data.reference}.`);
      setSelected(new Set());
      router.refresh();
    });
  }

  return (
    <div className="flex flex-col gap-3">
      {selected.size >= 2 && (
        <div className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2">
          <span className="text-sm">{selected.size} entrées sélectionnées</span>
          <Button size="sm" onClick={merge} disabled={isPending}>
            {isPending ? "Fusion..." : "Fusionner"}
          </Button>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead>Référence</TableHead>
            <TableHead>Statut</TableHead>
            <TableHead>Client</TableHead>
            <TableHead className="text-right">Disponible</TableHead>
            <TableHead>Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell>
                {MERGEABLE_STATUSES.has(entry.status) && !entry.merged_into_id && (
                  <Checkbox
                    checked={selected.has(entry.id)}
                    onCheckedChange={() => toggle(entry.id)}
                    aria-label="Sélectionner pour fusion"
                  />
                )}
              </TableCell>
              <TableCell className="font-mono text-xs">
                <Link href={`/entries/${entry.id}`} className="hover:underline">
                  {entry.reference}
                </Link>
              </TableCell>
              <TableCell>
                <StatusBadge status={entry.status} />
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{entry.client_name ?? "—"}</TableCell>
              <TableCell className="text-right tabular-nums">{availableSummary(entry)}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{formatDate(entry.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
