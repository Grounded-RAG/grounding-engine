import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  Shield,
  Layers,
  Zap,
  Brain,
  CheckCircle2,
  ArrowRight,
  Database,
  Bot,
  Eye,
  ChevronRight,
  Building2,
  Play,
  Quote,
  AlertTriangle,
  Search,
  Activity,
  Leaf,
  Menu,
  X,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import heroVisual from "@/assets/hero-visual.png";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: "easeOut" },
  }),
};

function MarketingNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border/50">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <Leaf className="h-7 w-7 text-accent" />
          <span className="text-xl font-bold text-foreground tracking-tight">Grounded AI</span>
        </Link>
        <nav className="hidden md:flex items-center gap-8">
          {[
            { label: "Product", target: "product" },
            { label: "Solutions", target: "solutions" },
            { label: "Trust", target: "trust" },
            { label: "Pricing", target: "pricing" },
          ].map((item) => (
            <a
              key={item.label}
              href={`#${item.target}`}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link to="/login" className="hidden md:inline-flex">
            <Button variant="ghost" size="sm">
              Log in
            </Button>
          </Link>
          <Link to="/login" className="hidden md:inline-flex">
            <Button className="rounded-full bg-foreground text-background hover:bg-foreground/90 px-5 h-9 text-sm font-medium">
              Try free
            </Button>
          </Link>
          <Button variant="outline" className="rounded-full px-5 h-9 text-sm hidden lg:inline-flex">
            Request demo
          </Button>
          <button
            className="md:hidden text-foreground"
            onClick={() => setMobileOpen(!mobileOpen)}
            type="button"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden border-t bg-background px-6 py-4 space-y-3"
        >
          {[
            { label: "Product", target: "product" },
            { label: "Solutions", target: "solutions" },
            { label: "Trust", target: "trust" },
            { label: "Pricing", target: "pricing" },
          ].map((item) => (
            <a
              key={item.label}
              href={`#${item.target}`}
              className="block text-sm text-foreground py-2"
              onClick={() => setMobileOpen(false)}
            >
              {item.label}
            </a>
          ))}
          <div className="flex gap-3 pt-2">
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
    <section className="relative pt-32 pb-20 md:pt-44 md:pb-28 overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-20 left-1/4 w-[500px] h-[500px] rounded-full bg-accent/5 blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] rounded-full bg-accent-teal/5 blur-[80px]" />
      </div>
      <div className="max-w-7xl mx-auto px-6 relative">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div initial="hidden" animate="visible" className="max-w-xl">
            <motion.div variants={fadeUp} custom={0} className="mb-8">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/5 px-4 py-1.5 text-sm text-accent font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                Now available - Standard tier live
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              custom={1}
              className="text-5xl md:text-6xl lg:text-[4.25rem] font-serif leading-[1.08] text-foreground mb-6"
            >
              The grounded intelligence layer for{" "}
              <span className="text-gradient italic">expert work</span>
            </motion.h1>
            <motion.p
              variants={fadeUp}
              custom={2}
              className="text-lg text-muted-foreground leading-relaxed mb-8 max-w-md"
            >
              Build agents that reason over your documents, policies, specifications, and
              institutional knowledge with citations, confidence, and traceability.
            </motion.p>
            <motion.div variants={fadeUp} custom={3} className="flex flex-wrap items-center gap-x-5 gap-y-2 mb-10">
              {["Reduce hallucination", "Resolve ambiguity", "Inspect every answer"].map((t) => (
                <span key={t} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                  {t}
                </span>
              ))}
            </motion.div>
            <motion.div variants={fadeUp} custom={4} className="flex flex-wrap items-center gap-4">
              <Link to="/login">
                <Button className="rounded-full bg-foreground text-background hover:bg-foreground/90 px-8 h-12 text-base font-medium gap-2">
                  Start building <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Button variant="outline" className="rounded-full px-8 h-12 text-base gap-2">
                <Play className="h-4 w-4" /> Watch demo
              </Button>
            </motion.div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.7 }}
            className="hidden lg:block"
          >
            <img
              src={heroVisual}
              alt="Abstract visual representing grounded intelligence"
              className="w-full rounded-2xl shadow-float"
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function TrustStrip() {
  return (
    <section className="py-12 border-y border-border/50">
      <div className="max-w-7xl mx-auto px-6">
        <p className="text-center text-xs tracking-widest uppercase text-muted-foreground mb-6">
          Trusted by teams building on critical knowledge
        </p>
        <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-4 opacity-40">
          {["Policy teams", "Compliance operations", "Research groups", "Technical operations", "Knowledge teams"].map((name) => (
            <span key={name} className="text-sm font-semibold text-foreground tracking-wide">
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function CapabilitiesSection() {
  const features = [
    {
      icon: Database,
      title: "Dataset-Backed Intelligence",
      desc: "Organize documents into datasets as the source of truth. Index specifications, policies, logs, and any institutional knowledge.",
    },
    {
      icon: Bot,
      title: "Grounded Agents",
      desc: "Build agents that reason over your datasets. Each agent can access multiple datasets and maintain conversation context.",
    },
    {
      icon: Layers,
      title: "Evidence-First Retrieval",
      desc: "Every answer starts with evidence. The system retrieves relevant passages before generating, ensuring answers are grounded in your data.",
    },
    {
      icon: Quote,
      title: "Sentence-Level Citations",
      desc: "Inspect exactly where answers come from. Citations link to source documents with page numbers and confidence scores.",
    },
    {
      icon: Eye,
      title: "Full Traceability",
      desc: "Every run is inspectable. View the query, retrieved evidence, confidence levels, and verification status for complete transparency.",
    },
    {
      icon: Activity,
      title: "Execution Modes",
      desc: "Choose the right depth for each question. From instant answers to verified responses for sensitive work.",
    },
    {
      icon: Shield,
      title: "Degraded Honesty",
      desc: "When evidence is weak, the system says so. No confident bluffing - just honest answers about what it can and cannot support.",
    },
    {
      icon: Building2,
      title: "Enterprise Scale",
      desc: "Handle millions of documents across thousands of users. Built for production workloads with flexible deployment options.",
    },
  ];

  return (
    <section id="product" className="py-24 md:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-semibold tracking-widest uppercase text-accent mb-4">Platform Capabilities</p>
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">Built for trustworthy answers</h2>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Turn your enterprise documents into a trusted intelligence layer. Grounded combines deep retrieval with strict citation controls.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={i}
              className="rounded-2xl border bg-card p-6 hover:shadow-elevated hover:border-accent/20 transition-all duration-300 group"
            >
              <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center mb-5 group-hover:bg-accent/15 transition-colors">
                <f.icon className="h-5 w-5 text-accent" />
              </div>
              <h3 className="text-base font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  return (
    <section id="trust" className="py-24 md:py-32 bg-secondary/50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">
            Reduce hallucination. Resolve ambiguity.
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Grounded is designed to solve the two most critical problems in enterprise RAG systems without compromising on speed or usability.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="rounded-2xl border bg-card p-8 md:p-10">
            <div className="h-10 w-10 rounded-xl bg-destructive/10 flex items-center justify-center mb-5">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <h3 className="text-2xl font-serif text-foreground mb-2">The hallucination problem</h3>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Most AI answers confidently even when wrong. In many AI systems, the model answers confidently even when the evidence is weak or missing. This creates risk in enterprise contexts where accuracy matters.
            </p>
            <h4 className="text-sm font-semibold text-foreground mb-3">How Grounded solves this</h4>
            <ul className="space-y-2.5">
              {[
                "Retrieves evidence before generating answers",
                "Ties every claim to specific citations",
                "Shows confidence and verification status",
                "Exposes trace and run details",
                "Uses degraded behavior when support is weak",
              ].map((t) => (
                <li key={t} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                  <CheckCircle2 className="h-4 w-4 text-accent mt-0.5 shrink-0" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border bg-card p-8 md:p-10">
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center mb-5">
              <Search className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="text-2xl font-serif text-foreground mb-2">The ambiguity problem</h3>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Vague questions need smarter retrieval. Many questions are vague, multi-part, comparative, or underspecified. Simple retrieval often fails on these harder queries.
            </p>
            <h4 className="text-sm font-semibold text-foreground mb-3">How Grounded solves this</h4>
            <ul className="space-y-2.5">
              {[
                "Tiered execution for different query complexity",
                "Standard tier for fast, everyday questions",
                ["Enterprise tier for deeper retrieval", true],
                ["Critical tier for highest-assurance work", true],
                "Automatic mode selection for optimal results",
              ].map((t, i) => {
                const text = Array.isArray(t) ? t[0] : t;
                const coming = Array.isArray(t);
                return (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-accent mt-0.5 shrink-0" />
                    {text as string}
                    {coming ? (
                      <Badge variant="coming" className="text-[9px] ml-1">
                        Coming soon
                      </Badge>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function ModesSection() {
  const modes = [
    {
      name: "Auto",
      tag: "Recommended",
      desc: "System chooses the best available execution path. Optimizes for speed and quality based on query complexity.",
      live: true,
      icon: Zap,
    },
    {
      name: "Instant",
      tag: "Live",
      desc: "Fast grounded answers for everyday work. Best for straightforward document questions.",
      live: true,
      icon: Activity,
    },
    {
      name: "Thinking",
      tag: "Coming soon",
      desc: "Deeper reasoning and retrieval for ambiguity-heavy questions. Multiple retrieval passes and stronger evidence selection.",
      live: false,
      icon: Brain,
    },
    {
      name: "Verified",
      tag: "Coming soon",
      desc: "Highest-assurance path for sensitive work. Additional verification and stricter trust controls.",
      live: false,
      icon: Shield,
    },
  ];

  return (
    <section className="py-24 md:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-semibold tracking-widest uppercase text-accent mb-4">Execution Modes</p>
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">Choose the right depth for each question</h2>
          <p className="text-lg text-muted-foreground">Different modes balance speed, accuracy, and assurance.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {modes.map((m, i) => (
            <motion.div
              key={m.name}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={i}
              className={`rounded-2xl border p-7 transition-all duration-300 ${m.live ? "bg-card hover:shadow-elevated hover:border-accent/20" : "bg-secondary/50 opacity-80"}`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="h-9 w-9 rounded-lg bg-accent/10 flex items-center justify-center">
                  <m.icon className="h-4 w-4 text-accent" />
                </div>
                <Badge
                  variant={m.live ? (m.name === "Auto" ? "accent" : "success") : "coming"}
                  className="text-[10px]"
                >
                  {m.tag}
                </Badge>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{m.name}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{m.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TiersSection() {
  const tiers = [
    {
      name: "Standard",
      status: "Live",
      desc: "Fast grounded baseline optimized for speed, citation quality, and predictable behavior. Powers Auto and Instant modes.",
      live: true,
    },
    {
      name: "Enterprise",
      status: "Coming soon",
      desc: "Deeper retrieval, better ranking, smarter evidence selection. Designed for harder, more ambiguous questions. Powers Thinking mode.",
      live: false,
    },
    {
      name: "Critical",
      status: "Coming soon",
      desc: "Highest-assurance path with stronger verification and stricter trust controls. Powers Verified mode.",
      live: false,
    },
  ];

  return (
    <section className="py-24 md:py-32 bg-secondary/50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-semibold tracking-widest uppercase text-accent mb-4">Execution Tiers</p>
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">Under the hood</h2>
          <p className="text-lg text-muted-foreground">
            Modes map to execution tiers that determine retrieval depth and verification behavior.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {tiers.map((t, i) => (
            <motion.div
              key={t.name}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={i}
              className={`rounded-2xl border p-8 ${t.live ? "bg-card" : "bg-card/50"}`}
            >
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-xl font-semibold text-foreground">{t.name}</h3>
                <Badge variant={t.live ? "success" : "coming"} className="text-[10px]">
                  {t.status}
                </Badge>
              </div>
              <p className="text-muted-foreground leading-relaxed">{t.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function UseCasesSection() {
  const cases = [
    {
      num: "01",
      cat: "Technical Documentation",
      title: "Customer engineering",
      desc: "Reliably automate responses to technical inquiries using context from datasheets, call logs, and product data.",
    },
    {
      num: "02",
      cat: "Root Cause Analysis",
      title: "Device log analysis",
      desc: "Quickly diagnose errors and anomalies in large, complex log files with cited evidence.",
    },
    {
      num: "03",
      cat: "Compliance Research",
      title: "IP & regulatory analysis",
      desc: "Create detailed reports identifying IP conflicts and compliance gaps based on prior art and regulatory requirements.",
    },
    {
      num: "04",
      cat: "Knowledge Management",
      title: "Enterprise search",
      desc: "Empower internal teams to find answers fast by searching across scattered knowledge sources.",
    },
    {
      num: "05",
      cat: "Report Generation",
      title: "Qualification reports",
      desc: "Cross-reference documents across multiple systems to generate audit-ready requirements traceability matrices.",
    },
    {
      num: "06",
      cat: "Data Extraction",
      title: "Data room analysis",
      desc: "Accurately extract key data from hundreds of messy documents and prepare them for analysis.",
    },
  ];

  return (
    <section id="solutions" className="py-24 md:py-32">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-semibold tracking-widest uppercase text-accent mb-4">Use Cases</p>
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">
            AI smart enough to tackle any expert task
          </h2>
          <p className="text-lg text-muted-foreground">
            From technical documentation to compliance research, Grounded handles the work that matters most.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {cases.map((c, i) => (
            <motion.div
              key={c.num}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={i}
              className="rounded-2xl border bg-card p-7 hover:shadow-elevated hover:border-accent/20 transition-all duration-300 group"
            >
              <div className="flex items-center gap-3 mb-4">
                <span className="text-sm font-medium text-accent">{c.cat}</span>
                <span className="text-xs text-muted-foreground ml-auto font-mono">{c.num}</span>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{c.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed mb-4">{c.desc}</p>
              <span className="text-sm text-accent font-medium group-hover:underline inline-flex items-center gap-1">
                Learn more <ChevronRight className="h-3.5 w-3.5" />
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PricingSection() {
  const plans = [
    { name: "Free", price: "$0", modes: ["Auto", "Instant"], cta: "Get started", featured: false },
    { name: "Pro", price: "$25", modes: ["Auto", "Instant", "Thinking"], cta: "Get started", featured: true },
    { name: "Business", price: "$199", modes: ["Auto", "Instant", "Thinking", "Verified*"], cta: "Get started", featured: false },
    { name: "Enterprise", price: "Custom", modes: ["Auto", "Instant", "Thinking", "Verified"], cta: "Contact us", featured: false },
  ];

  return (
    <section id="pricing" className="py-24 md:py-32 bg-secondary/50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-sm font-semibold tracking-widest uppercase text-accent mb-4">Plans</p>
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">
            Start free, scale with your needs.
          </h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {plans.map((p, i) => (
            <motion.div
              key={p.name}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              custom={i}
              className={`rounded-2xl border p-7 flex flex-col ${p.featured ? "border-accent shadow-glow bg-card ring-1 ring-accent/20" : "bg-card"}`}
            >
              {p.featured ? (
                <Badge variant="accent" className="text-[10px] w-fit mb-3">
                  Most popular
                </Badge>
              ) : null}
              <h3 className="text-xl font-semibold text-foreground">{p.name}</h3>
              <div className="mt-2 mb-6">
                <span className="text-3xl font-bold text-foreground">{p.price}</span>
                {p.price !== "Custom" ? <span className="text-sm text-muted-foreground">/mo</span> : null}
              </div>
              <ul className="space-y-2.5 mb-8 flex-1">
                {p.modes.map((m) => (
                  <li key={m} className="flex items-center gap-2 text-sm text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                    {m}
                  </li>
                ))}
              </ul>
              <Button
                className={`w-full rounded-full h-10 ${p.featured ? "bg-accent text-accent-foreground hover:bg-accent/90 shadow-glow" : ""}`}
                variant={p.featured ? "default" : "outline"}
              >
                {p.cta}
              </Button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="py-24 md:py-32 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-accent/5 blur-[100px]" />
      </div>
      <div className="max-w-3xl mx-auto text-center px-6 relative">
        <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-5">Ground your agents in real evidence</h2>
        <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
          Build agents that reason over your data, not around it. Get started with Grounded today.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/login">
            <Button className="rounded-full bg-foreground text-background hover:bg-foreground/90 px-8 h-12 text-base font-medium gap-2">
              Start building <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Button variant="outline" className="rounded-full px-8 h-12 text-base">
            Request demo
          </Button>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const cols = [
    { title: "Product", links: ["Platform", "Agents", "Datasets", "Runs", "Pricing"] },
    { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
    { title: "Resources", links: ["Documentation", "API Reference", "Status", "Security"] },
  ];

  return (
    <footer className="border-t py-16 bg-card/50">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-12">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-6 w-6 rounded-md gradient-accent flex items-center justify-center">
                <Leaf className="h-3 w-3 text-accent-foreground" />
              </div>
              <span className="text-lg font-bold text-foreground">Grounded AI</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The grounded intelligence layer for expert work. Reduce hallucination. Resolve ambiguity.
            </p>
          </div>
          {cols.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground mb-4">{col.title}</h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t mt-12 pt-8 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Grounded AI. All rights reserved.
        </div>
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
      <ModesSection />
      <TiersSection />
      <UseCasesSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </div>
  );
}
