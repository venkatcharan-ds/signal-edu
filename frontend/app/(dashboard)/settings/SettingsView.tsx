"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { FadeUp, Stagger } from "@/components/ui/motion";
import { Separator } from "@/components/ui/separator";
import { updateProfile } from "@/lib/api";
import { Check, Loader2 } from "lucide-react";

interface Props {
  defaultName: string;
  githubUsername: string;
  email: string;
  avatar: string;
}

export function SettingsView({ defaultName, githubUsername, email, avatar }: Props) {
  const [name, setName]               = useState(defaultName);
  const [institution, setInstitution] = useState("");
  const [saving, setSaving]           = useState(false);
  const [saved, setSaved]             = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ full_name: name, institution });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-10">
      <FadeUp>
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="text-muted-foreground text-sm">Manage your account and profile information.</p>
        </div>
      </FadeUp>

      <Stagger className="space-y-1">
        {/* Profile section */}
        <SettingSection title="Profile" subtitle="Your public identity on SIGNAL.">
          <div className="flex items-center gap-4 mb-6">
            <Avatar className="w-14 h-14">
              <AvatarImage src={avatar} />
              <AvatarFallback className="text-lg bg-signal-dim text-signal">
                {name?.[0] ?? githubUsername?.[0] ?? "U"}
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="text-sm font-medium">{githubUsername}</p>
              <p className="text-xs text-muted-foreground">{email}</p>
            </div>
          </div>

          <div className="space-y-4">
            <FieldRow label="Display name">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="w-full bg-white/5 border border-white/8 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-signal/50 focus:border-signal/40 transition-all placeholder:text-muted-foreground/50"
              />
            </FieldRow>

            <FieldRow label="Institution">
              <input
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="Your university or college"
                className="w-full bg-white/5 border border-white/8 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-signal/50 focus:border-signal/40 transition-all placeholder:text-muted-foreground/50"
              />
            </FieldRow>

            <FieldRow label="GitHub">
              <input
                type="text"
                value={githubUsername}
                disabled
                className="w-full bg-white/3 border border-white/5 rounded-lg px-3 py-2.5 text-sm text-muted-foreground cursor-not-allowed"
              />
            </FieldRow>
          </div>

          <div className="mt-6 flex gap-3">
            <Button
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-foreground text-background hover:bg-foreground/90 h-9 px-5 text-sm"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" />
              ) : saved ? (
                <Check className="w-3.5 h-3.5 mr-2 text-green-400" />
              ) : null}
              {saved ? "Saved" : "Save changes"}
            </Button>
          </div>
        </SettingSection>

        <Separator className="bg-white/5" />

        {/* Connected accounts */}
        <SettingSection title="Connected accounts" subtitle="Services connected to your SIGNAL account.">
          <div className="flex items-center gap-3 p-4 rounded-xl border border-white/5 bg-card">
            <GitHubIcon className="w-5 h-5 text-foreground" />
            <div className="flex-1">
              <p className="text-sm font-medium">GitHub</p>
              <p className="text-xs text-muted-foreground">@{githubUsername} · Connected</p>
            </div>
            <span className="text-[11px] text-green-400 bg-green-500/10 border border-green-500/20 px-2 py-0.5 rounded-full">
              Active
            </span>
          </div>
        </SettingSection>

        <Separator className="bg-white/5" />

        {/* Danger zone */}
        <SettingSection title="Data" subtitle="Manage your SIGNAL data.">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Re-run analysis at any time to update your profile as you add new repositories and artifacts.
            </p>
            <Button asChild variant="outline" size="sm" className="rounded-lg border-white/10 hover:bg-white/5 text-sm h-9">
              <a href="/analysis">Re-run analysis</a>
            </Button>
          </div>
        </SettingSection>
      </Stagger>
    </div>
  );
}

function SettingSection({
  title, subtitle, children,
}: {
  title: string; subtitle: string; children: React.ReactNode;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 12 },
        show:   { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
      }}
      className="py-8 space-y-6"
    >
      <div className="space-y-1">
        <h2 className="text-base font-medium">{title}</h2>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
      {children}
    </motion.div>
  );
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid sm:grid-cols-[160px_1fr] gap-2 sm:gap-4 items-center">
      <label className="text-sm text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
    </svg>
  );
}
