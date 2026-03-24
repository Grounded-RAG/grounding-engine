import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authenticateWithApiKey } from "@/lib/api";
import type { AuthSmokeResponse } from "@/lib/types";

const API_KEY_STORAGE_KEY = "grounded_api_key";
const WORKSPACE_ID_STORAGE_KEY = "grounded_workspace_id";
const WORKSPACE_NAME_STORAGE_KEY = "grounded_workspace_name";

function readStorage(key: string) {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

function writeStorage(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  if (value === null) {
    window.localStorage.removeItem(key);
    return;
  }
  window.localStorage.setItem(key, value);
}

interface AuthContextValue {
  apiKey: string | null;
  auth: AuthSmokeResponse | null;
  isLoading: boolean;
  workspaceId: string | null;
  workspaceName: string | null;
  signInWithApiKey: (apiKey: string) => Promise<AuthSmokeResponse>;
  signOut: () => void;
  setWorkspace: (workspaceId: string | null, workspaceName?: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(() => readStorage(API_KEY_STORAGE_KEY));
  const [auth, setAuth] = useState<AuthSmokeResponse | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(() => readStorage(WORKSPACE_ID_STORAGE_KEY));
  const [workspaceName, setWorkspaceName] = useState<string | null>(() => readStorage(WORKSPACE_NAME_STORAGE_KEY));
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(apiKey));

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (!apiKey) {
        setIsLoading(false);
        setAuth(null);
        return;
      }

      setIsLoading(true);
      try {
        const authenticated = await authenticateWithApiKey(apiKey);
        if (!cancelled) {
          setAuth(authenticated);
        }
      } catch {
        if (!cancelled) {
          writeStorage(API_KEY_STORAGE_KEY, null);
          setApiKey(null);
          setAuth(null);
          setWorkspaceId(null);
          setWorkspaceName(null);
          writeStorage(WORKSPACE_ID_STORAGE_KEY, null);
          writeStorage(WORKSPACE_NAME_STORAGE_KEY, null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void restore();

    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  const signInWithApiKey = useCallback(async (rawApiKey: string) => {
    const trimmed = rawApiKey.trim();
    const authenticated = await authenticateWithApiKey(trimmed);
    writeStorage(API_KEY_STORAGE_KEY, trimmed);
    setApiKey(trimmed);
    setAuth(authenticated);
    return authenticated;
  }, []);

  const signOut = useCallback(() => {
    writeStorage(API_KEY_STORAGE_KEY, null);
    writeStorage(WORKSPACE_ID_STORAGE_KEY, null);
    writeStorage(WORKSPACE_NAME_STORAGE_KEY, null);
    setApiKey(null);
    setAuth(null);
    setWorkspaceId(null);
    setWorkspaceName(null);
  }, []);

  const setWorkspace = useCallback((nextWorkspaceId: string | null, nextWorkspaceName?: string | null) => {
    setWorkspaceId(nextWorkspaceId);
    setWorkspaceName(nextWorkspaceName ?? null);
    writeStorage(WORKSPACE_ID_STORAGE_KEY, nextWorkspaceId);
    writeStorage(WORKSPACE_NAME_STORAGE_KEY, nextWorkspaceName ?? null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      apiKey,
      auth,
      isLoading,
      workspaceId,
      workspaceName,
      signInWithApiKey,
      signOut,
      setWorkspace,
    }),
    [apiKey, auth, isLoading, signInWithApiKey, signOut, workspaceId, workspaceName, setWorkspace],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
