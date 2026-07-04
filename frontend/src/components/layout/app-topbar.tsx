"use client";

import Link from "next/link";
import { Menu, LogOut, BellIcon } from "lucide-react";

import { logoutAction } from "@/actions/auth";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import type { NavItem } from "@/lib/nav";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function AppTopbar({
  companyName,
  fullName,
  matricule,
  roleLabel,
  unreadNotifications,
  navItems,
}: {
  companyName: string;
  fullName: string;
  matricule: string;
  roleLabel: string;
  unreadNotifications: number;
  navItems: NavItem[];
}) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden">
            <Menu />
            <span className="sr-only">Ouvrir le menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 bg-sidebar p-0 text-sidebar-foreground">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex h-14 items-center px-4 text-sm font-semibold">D-Transfert</div>
          <SidebarNav items={navItems} />
        </SheetContent>
      </Sheet>

      <div className="flex flex-1 items-center gap-2 overflow-hidden">
        <span className="truncate text-sm font-medium">{companyName}</span>
        <Badge variant="outline" className="hidden shrink-0 sm:inline-flex">
          {matricule}
        </Badge>
      </div>

      <Button variant="ghost" size="icon" asChild className="relative">
        <Link href="/notifications">
          <BellIcon />
          {unreadNotifications > 0 && (
            <span className="absolute top-1.5 right-1.5 flex size-2 rounded-full bg-destructive" />
          )}
          <span className="sr-only">Notifications</span>
        </Link>
      </Button>

      <ThemeToggle />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="gap-2 px-2">
            <Avatar className="size-7">
              <AvatarFallback>{initials(fullName)}</AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium sm:inline">{fullName}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="font-medium text-foreground">{fullName}</span>
            <span className="text-xs font-normal text-muted-foreground">
              {matricule} · {roleLabel}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <form action={logoutAction}>
            <DropdownMenuItem asChild variant="destructive">
              <button type="submit" className="w-full">
                <LogOut />
                Se déconnecter
              </button>
            </DropdownMenuItem>
          </form>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
