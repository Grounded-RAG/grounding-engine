import { Link } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Database,
  Eye,
  Menu,
  Play,
  Quote,
  Search,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import heroVisual from "@/assets/hero-visual.png";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: index * 0.08, duration: 0.45, ease: "easeOut" },
  }),
};

function MarketingNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-border/60 bg-background/92 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/grounded-mark.svg" alt="Grounded AI" className="h-8 w-8" />
          <span className="text-lg font-semibold tracking-[-0.03em] text-foreground">
            Grounded AI
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {["Product", "Solutions", "Trust", "Pricing"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {item}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link to="/login" className="hidden md:inline-flex">
            <Button variant="ghost" size="sm" className="rounded-full">
              Log in
            </Button>
          </Link>
          <Link to="/login" className="hidden md:inline-flex">
            <Button className="h-10 rounded-full bg-foreground px-5 text-sm font-medium text-background hover:bg-foreground/90">
              Try free
            </Button>
          </Link>
          <button
            type="button"
            className="text-foreground md:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-border/60 bg-background px-6 py-4 md:hidden"
        >
          <div className="space-y-3">
            {["Product", "Solutions", "Trust", "Pricing"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="block py-1 text-sm text-foreground"
                onClick={() => setMobileOpen(false)}
              >
                {item}
              </a>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <Link to="/login" className="flex-1">
              <Button variant="outline" className="w-full rounded-full">
                Log in
              </Button>
            </Link>
            <Link to="/login" className="flex-1">
              <Button className="w-full rounded-full bg-foreground text-background">
                Try free
              </Button>
            </Link>
          </div>
        </motion.div>
      )}
    </header>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-32 pb-24 md:pt-44 md:pb-32">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-16 left-1/4 h-[28rem] w-[28rem] rounded-full bg-accent/6 blur-[120px]" />
        <div className="absolute right-1/4 bottom-0 h-[22rem] w-[22rem] rounded-full bg-accent-teal/8 blur-[110px]" />
      </div>

      <div className="relative mx-auto grid max-w-7xl gap-14 px-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-center">
        <motion.div initial="hidden" animate="visible" className="max-w-2xl">
          <motion.div variants={fadeUp} custom={0} className="mb-8">
            <span className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/5 px-4 py-1.5 text-sm font-medium text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Standard tier is live now
            </span>
          </motion.div>

          <motion.h1
            variants={fadeUp}
            custom={1}
            className="font-display text-[3.35rem] font-semibold leading-[0.96] tracking-[-0.06em] text-foreground md:text-[4.75rem] lg:text-[5.75rem]"
          >
            Grounded intelligence for{" "}
            <span className="text-gradient">high-trust work</span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            custom={2}
            className="mt-7 max-w-xl text-lg leading-8 text-muted-foreground"
          >
            Build agents that reason over policies, technical documentation, procedures,
            and institutional knowledge with citations, confidence, and traceability.
          </motion.p>

          <motion.div
            variants={fadeUp}
            custom={3}
            className="mt-8 flex flex-wrap gap-x-6 gap-y-3"
          >
            {[
              "Reduce hallucination",
              "Resolve ambiguity",
              "Inspect every answer",
            ].map((item) => (
              <span key={item} className="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-accent" />
                {item}
              </span>
            ))}
          </motion.div>

          <motion.div variants={fadeUp} custom={4} className="mt-10 flex flex-wrap gap-4">
            <Link to="/login">
              <Button className="h-12 rounded-full bg-foreground px-8 text-base font-medium text-background hover:bg-foreground/90">
                Start building
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Button variant="outline" className="h-12 rounded-full px-8 text-base">
              <Play className="mr-2 h-4 w-4" />
              Watch demo
            </Button>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="hidden lg:block"
        >
          <img
            src={heroVisual}
            alt="Grounded AI interface preview"
            className="w-full rounded-[2rem] border border-border/60 shadow-[0_24px_80px_-30px_rgba(20,35,28,0.18)]"
          />
        </motion.div>
      </div>
    </section>
  );
}

function TrustStrip() {
  return (
    <section className="border-y border-border/60 py-12">
      <div className="mx-auto max-w-7xl px-6">
        <p className="mb-6 text-center text-xs uppercase tracking-[0.25em] text-muted-foreground">
          Trusted by teams building on critical knowledge
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 opacity-50">
          {["Enterprise Co.", "TechCorp", "Legal Partners", "Global Compliance", "InnovateLab"].map(
            (name) => (
              <span key={name} className="text-sm font-semibold tracking-wide text-foreground">
                {name}
              </span>
            ),
          )}
        </div>
      </div>
    </section>
  );
}

function CapabilitiesSection() {
  const features = [
    {
      icon: Database,
      title: "Datasets as source of truth",
      desc: "Organize documents into governed datasets that power every grounded answer.",
    },
    {
      icon: Bot,
      title: "Agents over real knowledge",
      desc: "Build agents that work across your documents instead of improvising around them.",
    },
    {
      icon: Quote,
      title: "Inspectable citations",
      desc: "Show where the answer came from with traceable evidence and source snippets.",
    },
    {
      icon: Eye,
      title: "Runs you can inspect",
      desc: "Review query routing, confidence, degraded reasons, and evidence used for each run.",
    },
  ];

  return (
    <section id="product" className="py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-accent">
            Platform capabilities
          </p>
          <h2 className="font-display text-4xl font-semibold tracking-[-0.05em] text-foreground md:text-5xl">
            Built for trustworthy answers
          </h2>
          <p className="mt-5 text-lg leading-8 text-muted-foreground">
            Grounded turns enterprise documents into a calm, inspectable intelligence
            layer for expert work.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={index}
              className="rounded-3xl border border-border/70 bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-accent/10">
                <feature.icon className="h-5 w-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">{feature.title}</h3>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  return (
    <section id="trust" className="bg-secondary/55 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto mb-18 max-w-3xl text-center">
          <h2 className="font-display text-4xl font-semibold tracking-[-0.05em] text-foreground md:text-5xl">
            Reduce hallucination. Resolve ambiguity.
          </h2>
          <p className="mt-5 text-lg leading-8 text-muted-foreground">
            Grounded is designed to solve the two most damaging failure modes in
            enterprise RAG systems.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          <div className="rounded-3xl border border-border/70 bg-card p-8 md:p-10">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <h3 className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
              Hallucination risk
            </h3>
            <p className="mt-4 text-sm leading-7 text-muted-foreground">
              Many AI systems answer confidently even when support is weak or missing.
              Grounded reduces that risk by anchoring responses in retrieved evidence.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                "Retrieve evidence before generation",
                "Tie claims to citations",
                "Expose confidence and verification status",
                "Degrade honestly when support is weak",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-muted-foreground">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-3xl border border-border/70 bg-card p-8 md:p-10">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-500/10">
              <Search className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
              Ambiguous questions
            </h3>
            <p className="mt-4 text-sm leading-7 text-muted-foreground">
              Harder questions need stronger retrieval and clearer execution paths.
              Grounded uses tiered modes so depth matches difficulty and risk.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                "Auto for the best live path",
                "Instant for fast grounded answers",
                "Thinking for deeper reasoning - coming soon",
                "Verified for highest assurance - coming soon",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-muted-foreground">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function TiersSection() {
  const tiers = [
    {
      name: "Standard",
      badge: "Live",
      desc: "Fast grounded baseline for everyday document questions. Powers the current live backend.",
      live: true,
    },
    {
      name: "Enterprise",
      badge: "Coming soon",
      desc: "Deeper retrieval, stronger evidence selection, and better handling for harder questions.",
      live: false,
    },
    {
      name: "Critical",
      badge: "Coming soon",
      desc: "Highest-assurance path for sensitive work with stronger verification and trust controls.",
      live: false,
    },
  ];

  return (
    <section id="solutions" className="py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-accent">
            Execution tiers
          </p>
          <h2 className="font-display text-4xl font-semibold tracking-[-0.05em] text-foreground md:text-5xl">
            Match execution depth to question risk
          </h2>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {tiers.map((tier, index) => (
            <motion.div
              key={tier.name}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={index}
              className="rounded-3xl border border-border/70 bg-card p-8"
            >
              <div className="mb-4 flex items-center gap-3">
                <h3 className="text-xl font-semibold text-foreground">{tier.name}</h3>
                <Badge variant={tier.live ? "success" : "coming"} className="text-[10px]">
                  {tier.badge}
                </Badge>
              </div>
              <p className="text-sm leading-7 text-muted-foreground">{tier.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border/60 bg-card/60 py-14">
      <div className="mx-auto flex max-w-7xl flex-col gap-10 px-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-md">
          <div className="mb-3 flex items-center gap-3">
            <img src="/grounded-mark.svg" alt="Grounded AI" className="h-7 w-7" />
            <span className="text-lg font-semibold tracking-[-0.03em] text-foreground">
              Grounded AI
            </span>
          </div>
          <p className="text-sm leading-7 text-muted-foreground">
            Grounded intelligence for high-trust work. Reduce hallucination, resolve
            ambiguity, and inspect every answer.
          </p>
        </div>

        <div className="grid gap-3 text-sm text-muted-foreground md:text-right">
          <span>Datasets</span>
          <span>Agents</span>
          <span>Runs</span>
          <span>API keys</span>
        </div>
      </div>
      <div className="mx-auto mt-10 max-w-7xl border-t border-border/60 px-6 pt-6 text-sm text-muted-foreground">
        © {new Date().getFullYear()} Grounded AI. All rights reserved.
      </div>
    </footer>
  );
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingNav />
      <HeroSection />
      <TrustStrip />
      <CapabilitiesSection />
      <ProblemSection />
      <TiersSection />
      <Footer />
    </div>
  );
}
