import { LandingNav, LandingFooter } from "@/components/landing/LandingNav";
import { HeroSection } from "@/components/landing/HeroSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { DifferentiationSection } from "@/components/landing/DifferentiationSection";
import { StatsSection } from "@/components/landing/StatsSection";
import { CtaSection } from "@/components/landing/CtaSection";

export default function LandingPage() {
  return (
    <>
      <LandingNav />
      <main className="flex-1">
        <HeroSection />
        <div id="how-it-works">
          <HowItWorks />
        </div>
        <div id="why-signal">
          <DifferentiationSection />
        </div>
        <StatsSection />
        <CtaSection />
      </main>
      <LandingFooter />
    </>
  );
}
