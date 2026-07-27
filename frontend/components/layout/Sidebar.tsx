"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { LayoutDashboard, User, Zap, Target, Lightbulb, Settings, LogOut } from "lucide-react";
import { signOut } from "@/lib/auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

const NAV_ITEMS = [
  { href: "/dashboard",       label: "Dashboard",       icon: LayoutDashboard },
  { href: "/analysis",        label: "Analysis",        icon: Zap             },
  { href: "/profile",         label: "Profile",         icon: User            },
  { href: "/gaps",            label: "Gaps",            icon: Target          },
  { href: "/recommendations", label: "Recommendations", icon: Lightbulb       },
  { href: "/settings",        label: "Settings",        icon: Settings        },
];

interface SidebarProps {
  user: {
    id: string;
    name: string | null;
    email: string | null;
    avatar: string | null;
    username: string | null;
  };
}

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const router   = useRouter();

  const handleLogout = async () => {
    await signOut();
    router.push("/");
  };

  const displayName = user.name ?? user.username ?? "Student";
  const initials    = displayName[0]?.toUpperCase() ?? "S";

  return (
    <aside className="hidden md:flex flex-col w-60 min-h-screen border-r border-white/5 bg-card/40 shrink-0">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-white/5">
        <Link href="/dashboard" className="font-semibold text-sm tracking-tight">
          SIGNAL
        </Link>
        <p className="text-[11px] text-muted-foreground mt-0.5">Capability Intelligence</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors group",
                active
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-white/5"
              )}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 bg-white/8 rounded-lg"
                  transition={{ type: "spring", bounce: 0.15, duration: 0.35 }}
                />
              )}
              <Icon
                className={cn(
                  "relative w-4 h-4 shrink-0",
                  active ? "text-signal" : "group-hover:text-foreground/80"
                )}
              />
              <span className="relative font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="px-3 py-4 border-t border-white/5 space-y-0.5">
        {user.username ? (
          <Link
            href={`/profile/${user.username}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors"
          >
            <UserAvatar avatar={user.avatar} initials={initials} />
            <UserMeta name={displayName} email={user.email} />
          </Link>
        ) : (
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
            <UserAvatar avatar={user.avatar} initials={initials} />
            <UserMeta name={displayName} email={user.email} />
          </div>
        )}

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}

function UserAvatar({ avatar, initials }: { avatar: string | null; initials: string }) {
  return (
    <Avatar className="w-7 h-7 shrink-0">
      <AvatarImage src={avatar ?? undefined} />
      <AvatarFallback className="text-xs bg-signal-dim text-signal">
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}

function UserMeta({ name, email }: { name: string; email: string | null }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs font-medium truncate">{name}</p>
      {email && <p className="text-[11px] text-muted-foreground truncate">{email}</p>}
    </div>
  );
}
