import { createClient } from "@/lib/supabase-server";
import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { DashboardHome } from "./DashboardHome";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const meta = user?.user_metadata as Record<string, string> | undefined;
  const name = meta?.full_name ?? meta?.name ?? meta?.user_name ?? "there";

  return (
    <>
      <Header pageTitle="Dashboard" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-5xl w-full mx-auto">
        <PageEnter>
          <DashboardHome firstName={name.split(" ")[0]} />
        </PageEnter>
      </main>
    </>
  );
}
