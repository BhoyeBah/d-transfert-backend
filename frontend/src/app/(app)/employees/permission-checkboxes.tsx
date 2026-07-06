"use client";

import { PermissionCode, PERMISSION_LABELS } from "@/lib/permissions";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

const ALL_PERMISSIONS = Object.values(PermissionCode);

export function PermissionCheckboxes({
  name,
  selected,
  onChange,
}: {
  name: string;
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  function toggle(code: string, checked: boolean) {
    onChange(checked ? [...selected, code] : selected.filter((c) => c !== code));
  }

  return (
    <div className="grid grid-cols-1 gap-2 rounded-md border border-border p-3 sm:grid-cols-2">
      {selected.map((code) => (
        <input key={code} type="hidden" name={name} value={code} />
      ))}
      {ALL_PERMISSIONS.map((code) => (
        <label key={code} className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={selected.includes(code)}
            onCheckedChange={(checked) => toggle(code, checked === true)}
          />
          <Label className="font-normal">{PERMISSION_LABELS[code]}</Label>
        </label>
      ))}
    </div>
  );
}
