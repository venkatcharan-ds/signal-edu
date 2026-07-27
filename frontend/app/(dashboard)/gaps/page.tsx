import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { GapsView } from "./GapsView";

export const metadata = { title: "Gap Analysis" };

export default function GapsPage() {
  return (
    <>
      <Header pageTitle="Gap Analysis" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-4xl w-full mx-auto">
        <PageEnter>
          <GapsView />
        </PageEnter>
      </main>
    </>
  );
}
