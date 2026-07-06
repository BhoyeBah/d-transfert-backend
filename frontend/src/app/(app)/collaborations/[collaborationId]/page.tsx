import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import {
  getCollaboration,
  getCollaboratorBalance,
  getRateHistory,
  listPrivateRates,
} from "@/lib/data/collaborations";
import { getMe } from "@/lib/data/me";
import { formatDate, formatMoney } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CollaborationDecisionButtons,
  ProposeRateDialog,
  RateProposalDecisionButtons,
} from "./collaboration-actions";
import { CreatePrivateRateDialog } from "./create-private-rate-dialog";

export const metadata: Metadata = { title: "Détail collaboration — D-Transfert" };

export default async function CollaborationDetailPage({
  params,
}: {
  params: Promise<{ collaborationId: string }>;
}) {
  const { collaborationId } = await params;
  const [collaboration, rateHistory, me] = await Promise.all([
    getCollaboration(collaborationId),
    getRateHistory(collaborationId),
    getMe(),
  ]);

  const balance = collaboration.status === "accepted" ? await getCollaboratorBalance(collaborationId) : null;
  const privateRates =
    collaboration.status === "accepted"
      ? (await listPrivateRates()).filter((rate) => rate.collaboration_id === collaborationId)
      : [];

  const isTarget = collaboration.target_company_id === me.company_id;
  const pendingProposal = rateHistory.find((entry) => entry.status === "proposed");
  const canDecideProposal = pendingProposal && pendingProposal.proposed_by_company_id !== me.company_id;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/collaborations"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Collaborations
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Collaboration en {collaboration.currency}
            </h1>
            <p className="text-sm text-muted-foreground">{collaboration.note ?? "Aucune note."}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={collaboration.status} />
            {collaboration.status === "pending" && isTarget && (
              <CollaborationDecisionButtons collaborationId={collaboration.id} />
            )}
          </div>
        </div>
      </div>

      {collaboration.status === "accepted" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="py-4">
            <CardContent className="px-4">
              <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                Solde collaborateur
              </span>
              {balance && (
                <p
                  className={`text-2xl font-semibold tabular-nums ${
                    Number(balance.balance) < 0 ? "text-destructive" : "text-success"
                  }`}
                >
                  {formatMoney(balance.balance, balance.currency)}
                </p>
              )}
            </CardContent>
          </Card>
          <Card className="py-4">
            <CardContent className="flex items-center justify-between px-4">
              <div>
                <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  Taux collaboratif actuel
                </span>
                <p className="text-2xl font-semibold tabular-nums">{collaboration.current_rate}</p>
              </div>
              {!pendingProposal && <ProposeRateDialog collaborationId={collaboration.id} />}
            </CardContent>
          </Card>
        </div>
      )}

      {pendingProposal && (
        <Card className="border-warning/40">
          <CardContent className="flex items-center justify-between px-4 py-3">
            <div>
              <span className="text-sm font-medium">
                Proposition en cours : nouveau taux {pendingProposal.new_rate}
              </span>
              {pendingProposal.note && (
                <p className="text-xs text-muted-foreground">{pendingProposal.note}</p>
              )}
            </div>
            {canDecideProposal ? (
              <RateProposalDecisionButtons collaborationId={collaboration.id} proposalId={pendingProposal.id} />
            ) : (
              <span className="text-xs text-muted-foreground">En attente de l&apos;autre partie</span>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Historique des taux</CardTitle>
        </CardHeader>
        <CardContent>
          {rateHistory.length === 0 ? (
            <EmptyState message="Aucun historique de taux." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ancien taux</TableHead>
                  <TableHead>Nouveau taux</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rateHistory.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="tabular-nums">{entry.old_rate ?? "—"}</TableCell>
                    <TableCell className="tabular-nums">{entry.new_rate}</TableCell>
                    <TableCell>
                      <StatusBadge status={entry.status} />
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(entry.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {collaboration.status === "accepted" && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Taux d&apos;envoi privé pour cette collaboration</CardTitle>
            <CreatePrivateRateDialog collaborationId={collaboration.id} defaultCurrency={collaboration.currency} />
          </CardHeader>
          <CardContent>
            {privateRates.length === 0 ? (
              <EmptyState message="Aucun taux privé défini pour cette collaboration." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Devise</TableHead>
                    <TableHead>Pays</TableHead>
                    <TableHead className="text-right">Taux</TableHead>
                    <TableHead>Statut</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {privateRates.map((rate) => (
                    <TableRow key={rate.id}>
                      <TableCell>{rate.currency}</TableCell>
                      <TableCell>{rate.country ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{rate.rate}</TableCell>
                      <TableCell>
                        <StatusBadge status={rate.is_active ? "active" : "inactive"} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
