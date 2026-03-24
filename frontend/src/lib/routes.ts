export function workspaceBasePath(workspaceSlug?: string | null) {
  return workspaceSlug ? `/app/workspace/${workspaceSlug}` : "/app";
}

export function workspacePath(workspaceSlug?: string | null, subpath = "") {
  if (!subpath) {
    return `${workspaceBasePath(workspaceSlug)}/overview`;
  }
  const normalizedSubpath = subpath
    ? subpath.startsWith("/")
      ? subpath
      : `/${subpath}`
    : "";
  return `${workspaceBasePath(workspaceSlug)}${normalizedSubpath}`;
}
