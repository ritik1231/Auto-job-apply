import { useEffect } from "react";
import { useAuthStore } from "@/popup/stores/auth-store";

export function useAuth() {
  const store = useAuthStore();

  useEffect(() => {
    void store.checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return store;
}
