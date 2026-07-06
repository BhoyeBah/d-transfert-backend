"use client";

import { SUPPORTED_CURRENCIES } from "@/lib/validation/auth";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function CurrencySelect({
  name,
  value,
  onValueChange,
  id,
}: {
  name: string;
  value: string;
  onValueChange: (value: string) => void;
  id?: string;
}) {
  return (
    <>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SUPPORTED_CURRENCIES.map((code) => (
            <SelectItem key={code} value={code}>
              {code}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <input type="hidden" name={name} value={value} />
    </>
  );
}
