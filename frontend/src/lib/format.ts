const numberFormatterCache = new Map<string, Intl.NumberFormat>();

function getNumberFormatter(currency?: string) {
  const key = currency ?? "plain";
  let formatter = numberFormatterCache.get(key);
  if (!formatter) {
    formatter = currency
      ? new Intl.NumberFormat("fr-FR", {
          style: "currency",
          currency,
          currencyDisplay: "code",
          maximumFractionDigits: 2,
        })
      : new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
    numberFormatterCache.set(key, formatter);
  }
  return formatter;
}

export function formatMoney(value: string | number, currency?: string): string {
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return String(value);
  return getNumberFormatter(currency).format(amount);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value)
  );
}
