import { Outlet, Link, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  LayoutDashboard,
  Database,
  Bot,
  Activity,
  BarChart3,
  MessageSquareText,
  CreditCard,
  Settings,
  Key,
  BookOpen,
  Leaf,
  Menu,
  ChevronLeft,
  Eye,
  Bell,
  LogOut,
  type LucideIcon,
} from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

const navItems: Array<{
  label?: string;
  icon?: LucideIcon;
  path?: string;
  exact?: boolean;
  coming?: boolean;
  divider?: boolean;
  external?: boolean;
}> = [
  { label: "Overview", icon: LayoutDashboard, path: "/app", exact: true },
  { label: "Agents", icon: Bot, path: "/app/agents" },
  { label: "Datasets", icon: Database, path: "/app/datasets" },
  { label: "Runs", icon: Activity, path: "/app/runs" },
  { label: "Monitoring", icon: Eye, path: "/app/monitoring", coming: true },
  { label: "Feedback", icon: MessageSquareText, path: "/app/feedback", coming: true },
  { label: "Usage", icon: BarChart3, path: "/app/usage", coming: true },
  { label: "Billing", icon: CreditCard, path: "/app/billing", coming: true },
  { divider: true },
  { label: "Settings", icon: Settings, path: "/app/settings" },
  { label: "API Keys", icon: Key, path: "/app/api-keys" },
  { label: "Docs", icon: BookOpen, path: "#", external: true },
] as const;

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const { auth, workspaceName, signOut } = useAuth();

  const isActive = (path: string, exact?: boolean) => {
    if (exact) return location.pathname === path;
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 bottom-0 z-40 flex flex-col border-r bg-card transition-all duration-200",
        sidebarOpen ? "w-60" : "w-14"
      )}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b gap-2.5 shrink-0">
          <div className="h-7 w-7 rounded-lg gradient-accent flex items-center justify-center shrink-0">
            <Leaf className="h-3.5 w-3.5 text-accent-foreground" />
          </div>
          {sidebarOpen && <span className="text-sm font-bold text-foreground truncate">Grounded AI</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          {navItems.map((item, i) => {
            if ('divider' in item && item.divider) return <div key={i} className="border-t my-2 mx-2" />;
            const navItem = item as { label: string; icon: LucideIcon; path: string; exact?: boolean; coming?: boolean };
            const Icon = navItem.icon;
            const active = isActive(navItem.path, navItem.exact);
            return (
              <Link
                key={navItem.label}
                to={navItem.coming ? "#" : navItem.path}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors mb-0.5",
                  active ? "bg-accent/10 text-accent font-medium" : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                  navItem.coming && "opacity-50 cursor-default"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {sidebarOpen && (
                  <>
                    <span className="truncate">{navItem.label}</span>
                    {navItem.coming && <Badge variant="coming" className="ml-auto text-[9px] px-1.5">Soon</Badge>}
                  </>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="border-t p-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="flex items-center justify-center w-full h-8 rounded-lg hover:bg-secondary text-muted-foreground transition-colors"
          >
            <ChevronLeft className={cn("h-4 w-4 transition-transform", !sidebarOpen && "rotate-180")} />
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className={cn("flex-1 flex flex-col transition-all duration-200", sidebarOpen ? "ml-60" : "ml-14")}>
        {/* Topbar */}
        <header className="h-14 border-b bg-card/80 backdrop-blur-lg flex items-center px-6 gap-4 sticky top-0 z-30">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="md:hidden text-muted-foreground hover:text-foreground"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1" />
          <div className="hidden md:block text-right">
            <div className="text-xs text-muted-foreground">{workspaceName || "Workspace"}</div>
            <div className="text-sm font-medium text-foreground">{auth?.tenant_name || "Grounded AI"}</div>
          </div>
          <ThemeToggle />
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
            <Bell className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground"
            onClick={signOut}
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
          <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
            <span className="text-xs font-medium text-accent">
              {(auth?.tenant_name || "G").slice(0, 1).toUpperCase()}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
