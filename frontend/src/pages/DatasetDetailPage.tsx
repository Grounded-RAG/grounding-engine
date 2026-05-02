import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Database,
  File,
  Upload,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getDataset,
  listDatasetDocuments,
  listDatasetJobs,
  uploadDatasetDocument,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, formatFileSize, formatRelativeOrDate, sentenceCase } from "@/lib/format";
import { workspacePath } from "@/lib/routes";
import type { DatasetIngestionJobResponse } from "@/lib/types";

function StatusBadge({
  label,
  variant,
  icon: Icon,
}: {
  label: string;
  variant: "success" | "warning" | "destructive" | "outline";
  icon?: LucideIcon;
}) {
  return (
    <Badge variant={variant} className="text-[10px]">
      {Icon ? <Icon className="h-2.5 w-2.5 mr-0.5" /> : null}
      {label}
    </Badge>
  );
}

export default function DatasetDetailPage() {
  const { id } = useParams();
  const { apiKey, workspaceSlug } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [title, setTitle] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const datasetQuery = useQuery({
    queryKey: ["dataset", id],
    queryFn: () => getDataset(apiKey!, id!),
    enabled: Boolean(apiKey && id),
  });

  const documentsQuery = useQuery({
    queryKey: ["dataset", id, "documents"],
    queryFn: () => listDatasetDocuments(apiKey!, id!),
    enabled: Boolean(apiKey && id),
  });

  const jobsQuery = useQuery({
    queryKey: ["dataset", id, "jobs"],
    queryFn: () => listDatasetJobs(apiKey!, id!),
    enabled: Boolean(apiKey && id),
    refetchInterval: (query) => {
      const jobs = (query.state.data as DatasetIngestionJobResponse[] | undefined) ?? [];
      return jobs.some((job) => job.status === "queued" || job.status === "running") ? 4000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      if (!apiKey || !id) {
        throw new Error("Dataset upload requires an authenticated dataset context.");
      }
      return uploadDatasetDocument(apiKey, id, file, title.trim() || undefined);
    },
    onSuccess: (response) => {
      toast.success(
        response.already_exists
          ? "This file is already indexed in the dataset."
          : "Upload accepted. Ingestion started.",
      );
      setTitle("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      void queryClient.invalidateQueries({ queryKey: ["dataset", id, "documents"] });
      void queryClient.invalidateQueries({ queryKey: ["dataset", id, "jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Unable to upload the file.";
      toast.error(message);
    },
  });

  const uploadJobs = jobsQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const dataset = datasetQuery.data;
  const indexedCount = documents.filter((document) => document.status === "indexed").length;

  const onSelectFile = (file?: File | null) => {
    if (!file) return;
    uploadMutation.mutate(file);
  };

  if (datasetQuery.isLoading) {
    return <div className="h-48 rounded-2xl border bg-card animate-pulse" />;
  }

  if (!dataset) {
    return (
      <div className="max-w-4xl">
        <Link to={workspacePath(workspaceSlug, "/datasets")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to datasets
        </Link>
        <div className="rounded-2xl border bg-card p-10 text-center">
          <h1 className="text-lg font-semibold text-foreground mb-2">Dataset not found</h1>
          <p className="text-sm text-muted-foreground">This dataset may have been removed or you may not have access to it.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl">
      <Link to={workspacePath(workspaceSlug, "/datasets")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to datasets
      </Link>

      <div className="grid xl:grid-cols-[minmax(0,1fr)_300px] gap-6">
        <div>
          <div className="flex items-start justify-between mb-8 gap-4">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-xl bg-accent/10 flex items-center justify-center">
                <Database className="h-6 w-6 text-accent" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">{dataset.name}</h1>
                <p className="text-sm text-muted-foreground mt-0.5">{sentenceCase(dataset.domain)} dataset</p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <StatusBadge label="Indexed ready" variant="success" icon={CheckCircle2} />
                  <StatusBadge label={sentenceCase(dataset.min_execution_tier)} variant="outline" />
                  <span className="text-xs text-muted-foreground">
                    {indexedCount}/{documents.length} indexed documents
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              onSelectFile(event.dataTransfer.files?.[0]);
            }}
            className={`rounded-2xl border-2 border-dashed p-8 text-center mb-8 transition-colors ${
              dragOver ? "border-accent bg-accent/5" : "border-border bg-secondary/30"
            }`}
          >
            <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-sm font-medium text-foreground mb-1">Upload documents</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Drag and drop a file here or browse manually. Duplicate uploads resolve to the existing indexed document.
            </p>
            <div className="max-w-md mx-auto text-left mb-4">
              <Label htmlFor="upload-title">Optional title</Label>
              <Input
                id="upload-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Policy update memo"
                className="mt-1.5 h-10 rounded-xl"
              />
            </div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(event) => onSelectFile(event.target.files?.[0])}
            />
            <Button
              variant="pill-outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Uploading..." : "Browse files"}
            </Button>
          </div>

          <div className="mb-8">
            <h3 className="text-sm font-semibold text-foreground mb-4">Documents</h3>
            <div className="rounded-2xl border bg-card overflow-hidden">
              {documentsQuery.isLoading ? (
                <div className="p-5 text-sm text-muted-foreground">Loading documents...</div>
              ) : documents.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No documents yet. Upload your first source file to start building grounded answers.
                </div>
              ) : (
                <div className="divide-y">
                  {documents.map((document) => (
                    <div
                      key={document.document_id}
                      className="flex items-center justify-between px-5 py-3.5 hover:bg-secondary/30 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <File className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="min-w-0">
                          <span className="text-sm font-medium text-foreground block truncate">
                            {document.title || "Untitled document"}
                          </span>
                          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                            <span className="text-xs text-muted-foreground">{document.mime_type}</span>
                            <span className="text-xs text-muted-foreground">• {formatFileSize(document.file_size_bytes)}</span>
                            <span className="text-xs text-muted-foreground">• {formatRelativeOrDate(document.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      {document.status === "indexed" ? (
                        <StatusBadge label="Indexed" variant="success" icon={CheckCircle2} />
                      ) : document.status === "failed" ? (
                        <StatusBadge label="Failed" variant="destructive" />
                      ) : (
                        <StatusBadge label={sentenceCase(document.status)} variant="warning" icon={Clock} />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground mb-4">Ingestion Jobs</h3>
            <div className="rounded-2xl border bg-card overflow-hidden">
              {jobsQuery.isLoading ? (
                <div className="p-5 text-sm text-muted-foreground">Loading ingestion jobs...</div>
              ) : uploadJobs.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No ingestion jobs yet. Jobs appear as soon as you upload a file into this dataset.
                </div>
              ) : (
                <div className="divide-y">
                  {uploadJobs.map((job) => (
                    <div key={job.job_id} className="flex items-center justify-between px-5 py-3.5">
                      <div>
                        <div className="text-sm text-foreground">{job.document_id.slice(0, 8)} • attempt {job.attempt_count}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          Started {job.started_at ? formatRelativeOrDate(job.started_at) : "not started"} • Created {formatDateTime(job.created_at)}
                        </div>
                        {job.error_detail ? (
                          <div className="text-xs text-destructive mt-1">{job.error_detail}</div>
                        ) : null}
                      </div>
                      {job.status === "indexed" ? (
                        <StatusBadge label="Indexed" variant="success" icon={CheckCircle2} />
                      ) : job.status === "failed" ? (
                        <StatusBadge label="Failed" variant="destructive" />
                      ) : (
                        <StatusBadge label={sentenceCase(job.status)} variant="warning" icon={Clock} />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border bg-card p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">Dataset Policy</h3>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-muted-foreground">Sensitivity</div>
                <div className="text-foreground">{sentenceCase(dataset.sensitivity_level)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Freshness profile</div>
                <div className="text-foreground">{sentenceCase(dataset.freshness_profile)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Minimum tier</div>
                <div className="text-foreground">{sentenceCase(dataset.min_execution_tier)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Web fallback</div>
                <div className="text-foreground">{dataset.allow_web_fallback ? "Allowed" : "Disabled"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Internal model retrieval</div>
                <div className="text-foreground">
                  {dataset.allow_internal_model_retrieval ? "Allowed" : "Disabled"}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border bg-card p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">Readiness</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Documents</span>
                <span className="text-foreground">{documents.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Indexed</span>
                <span className="text-foreground">{indexedCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Pending jobs</span>
                <span className="text-foreground">
                  {uploadJobs.filter((job) => job.status === "queued" || job.status === "running").length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
