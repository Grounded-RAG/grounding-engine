export function workspaceBasePath(workspaceSlug?: string | null) {
  return workspaceSlug ? `/app/workspace/${workspaceSlug}` : "/app";
}

export function workspacePath(workspaceSlug?: string | null, subpath = "") {
  const normalizedSubpath = subpath
    ? subpath.startsWith("/")
      ? subpath
      : `/${subpath}`
    : "";
  return `${workspaceBasePath(workspaceSlug)}${normalizedSubpath}`;
}
