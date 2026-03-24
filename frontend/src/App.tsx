import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";
import RequireAuth from "@/components/RequireAuth";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";
import OnboardingPage from "./pages/OnboardingPage";
import AppShell from "./components/AppShell";
import DashboardPage from "./pages/DashboardPage";
import DatasetsPage from "./pages/DatasetsPage";
import DatasetDetailPage from "./pages/DatasetDetailPage";
import AgentsPage from "./pages/AgentsPage";
import AgentChatPage from "./pages/AgentChatPage";
import RunsPage from "./pages/RunsPage";
import SettingsPage from "./pages/SettingsPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/sign-up" element={<SignUpPage />} />
            <Route element={<RequireAuth />}>
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/app" element={<AppShell />}>
                <Route index element={<Navigate to="overview" replace />} />
                <Route path="overview" element={<DashboardPage />} />
                <Route path="datasets" element={<DatasetsPage />} />
                <Route path="datasets/:id" element={<DatasetDetailPage />} />
                <Route path="agents" element={<AgentsPage />} />
                <Route path="agents/:id" element={<AgentChatPage />} />
                <Route path="runs" element={<RunsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="api-keys" element={<SettingsPage />} />
              </Route>
              <Route path="/app/workspace/:workspaceSlug" element={<AppShell />}>
                <Route index element={<Navigate to="overview" replace />} />
                <Route path="overview" element={<DashboardPage />} />
                <Route path="datasets" element={<DatasetsPage />} />
                <Route path="datasets/:id" element={<DatasetDetailPage />} />
                <Route path="agents" element={<AgentsPage />} />
                <Route path="agents/:id" element={<AgentChatPage />} />
                <Route path="runs" element={<RunsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="api-keys" element={<SettingsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
