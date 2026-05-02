import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Database, Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createDataset, listDatasets } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, sentenceCase } from "@/lib/format";
import { workspacePath } from "@/lib/routes";

export default function DatasetsPage() {
  const { apiKey, workspaceId, workspaceSlug } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    domain: "general",
  });

  const datasetsQuery = useQuery({
    queryKey: ["datasets", workspaceId],
    queryFn: () => listDatasets(apiKey!, workspaceId),
    enabled: Boolean(apiKey && workspaceId),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey || !workspaceId) {
        throw new Error("Create a workspace before creating datasets.");
      }

      return createDataset(apiKey, {
        workspace_id: workspaceId,
        name: form.name.trim(),
        domain: form.domain.trim() || "general",
      });
    },
    onSuccess: (dataset) => {
      toast.success("Dataset created.");
      setForm({ name: "", domain: "general" });
      setShowCreateForm(false);
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["agents"] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      navigate(workspacePath(workspaceSlug, `/datasets/${dataset.dataset_id}`));
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to create the dataset.";
      toast.error(message);
    },
  });

  const filteredDatasets = useMemo(() => {
    const datasets = datasetsQuery.data ?? [];
    const value = search.trim().toLowerCase();
    if (!value) return datasets;
    return datasets.filter((dataset) =>
      [dataset.name, dataset.domain].some((field) => field.toLowerCase().includes(value)),
    );
  }, [datasetsQuery.data, search]);

  if (!workspaceId) {
    return (
      <div className="max-w-3xl">
        <div className="rounded-2xl border bg-card p-10 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Database className="h-7 w-7 text-muted-foreground" />
          </div>
          <h1 className="text-xl font-semibold text-foreground mb-2">Create a workspace first</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Datasets belong to a workspace. Finish onboarding first, then return here to create your source-of-truth collections.
          </p>
          <Link to="/onboarding">
            <Button className="rounded-full bg-accent text-accent-foreground hover:bg-accent/90">
              Continue onboarding
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Datasets</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Datasets are the source of truth for your grounded agents.
          </p>
        </div>
        <Button variant="pill-accent" size="sm" onClick={() => setShowCreateForm((current) => !current)}>
          <Plus className="h-3.5 w-3.5 mr-1" /> {showCreateForm ? "Hide form" : "Create dataset"}
        </Button>
      </div>

      {showCreateForm && (
        <div className="rounded-2xl border bg-card p-6 mb-6">
          <h2 className="text-sm font-semibold text-foreground mb-4">Create a dataset</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="dataset-name">Name</Label>
              <Input
                id="dataset-name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Policy Library"
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
            <div>
              <Label htmlFor="dataset-domain">Domain</Label>
              <Input
                id="dataset-domain"
                value={form.domain}
                onChange={(event) => setForm((current) => ({ ...current, domain: event.target.value }))}
                placeholder="compliance"
                className="mt-1.5 h-11 rounded-xl"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button
              variant="pill-accent"
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={!form.name.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create dataset"}
            </Button>
          </div>
        </div>
      )}

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search datasets..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="pl-10 h-10 rounded-xl"
        />
      </div>

      {datasetsQuery.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-24 rounded-2xl border bg-card animate-pulse" />
          ))}
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="rounded-2xl border bg-card p-12 text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <Database className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No datasets yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
            Create your first dataset so agents have documents and evidence to reason over.
          </p>
          <Button variant="pill-accent" onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4 mr-1" /> Create your first dataset
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDatasets.map((dataset, index) => (
            <motion.div
              key={dataset.dataset_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Link
                to={workspacePath(workspaceSlug, `/datasets/${dataset.dataset_id}`)}
                className="block rounded-2xl border bg-card p-5 hover-lift group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center mt-0.5">
                      <Database className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground group-hover:text-accent transition-colors">
                        {dataset.name}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {sentenceCase(dataset.domain)} • {sentenceCase(dataset.freshness_profile)} freshness
                      </p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <Badge variant="outline" className="text-[10px]">
                          {sentenceCase(dataset.min_execution_tier)}
                        </Badge>
                        <Badge variant="outline" className="text-[10px]">
                          {sentenceCase(dataset.sensitivity_level)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Created {formatDateTime(dataset.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
