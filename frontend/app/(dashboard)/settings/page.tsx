import { createClient } from "@/lib/supabase-server";
import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { SettingsView } from "./SettingsView";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const meta = user?.user_metadata as Record<string, string> | undefined;

  return (
    <>
      <Header pageTitle="Settings" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-2xl w-full mx-auto">
        <PageEnter>
          <SettingsView
            defaultName={meta?.full_name ?? meta?.name ?? ""}
            githubUsername={meta?.user_name ?? ""}
            email={user?.email ?? ""}
            avatar={meta?.avatar_url ?? ""}
          />
        </PageEnter>
      </main>
    </>
  );
}
