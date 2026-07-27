import { Header } from "@/components/layout/Header";
import { PageEnter } from "@/components/ui/motion";
import { AnalysisView } from "./AnalysisView";

export const metadata = { title: "Analysis" };

export default function AnalysisPage() {
  return (
    <>
      <Header pageTitle="Analysis" />
      <main className="flex-1 px-6 md:px-8 py-8 max-w-3xl w-full mx-auto">
        <PageEnter>
          <AnalysisView />
        </PageEnter>
      </main>
    </>
  );
}
