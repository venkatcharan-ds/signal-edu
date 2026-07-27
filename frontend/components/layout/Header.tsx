"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, LayoutDashboard, User, Zap, Target, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/dashboard",    label: "Dashboard",    icon: LayoutDashboard },
  { href: "/analysis",     label: "Analysis",     icon: Zap             },
  { href: "/gap-analysis", label: "Gap Analysis", icon: Target          },
  { href: "/profile",      label: "Profile",      icon: User            },
  { href: "/settings",     label: "Settings",     icon: Settings        },
];

interface HeaderProps {
  pageTitle?: string;
}

export function Header({ pageTitle }: HeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <>
      {/* Mobile header bar */}
      <header className="md:hidden flex items-center justify-between px-5 py-4 border-b border-white/5 bg-card/60 backdrop-blur-xl sticky top-0 z-40">
        <span className="font-semibold text-sm tracking-tight">SIGNAL</span>
        {pageTitle && (
          <span className="text-sm text-muted-foreground absolute left-1/2 -translate-x-1/2">{pageTitle}</span>
        )}
        <button
          onClick={() => setMobileOpen(true)}
          className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-50 md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", bounce: 0, duration: 0.3 }}
              className="fixed right-0 top-0 bottom-0 w-72 bg-card border-l border-white/5 z-50 flex flex-col md:hidden"
            >
              <div className="flex items-center justify-between px-5 py-5 border-b border-white/5">
                <span className="font-semibold text-sm">SIGNAL</span>
                <button
                  onClick={() => setMobileOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <nav className="flex-1 px-3 py-4 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition-colors",
                        active
                          ? "bg-white/8 text-foreground"
                          : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                      )}
                    >
                      <Icon className={cn("w-4 h-4", active && "text-signal")} />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>

              <div className="px-3 py-4 border-t border-white/5">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
                >
                  Sign out
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop page header */}
      {pageTitle && (
        <div className="hidden md:flex items-center px-8 py-5 border-b border-white/5">
          <h1 className="text-sm font-medium text-muted-foreground">{pageTitle}</h1>
        </div>
      )}
    </>
  );
}
