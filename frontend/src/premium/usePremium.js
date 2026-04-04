import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-toastify";
import { API_BASE } from "../config/api";
import { auth } from "../firebase";
import { hasFeature } from "./plans";

const ENTITLEMENT_KEY = "educator_entitlement";

const readStoredEntitlement = () => {
  try {
    const raw = localStorage.getItem(ENTITLEMENT_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
};

const writeStoredEntitlement = (value) => {
  try {
    localStorage.setItem(ENTITLEMENT_KEY, JSON.stringify(value || {}));
  } catch (_error) {}
};

function usePremium() {
  const [state, setState] = useState(() => {
    const saved = readStoredEntitlement();
    const plan = String(saved?.plan || "free").toLowerCase();
    return {
      plan,
      active: Boolean(saved?.active),
      expiresAtEpoch: Number(saved?.expiresAtEpoch || 0),
      loading: false,
      lastSyncEpoch: Number(saved?.lastSyncEpoch || 0),
    };
  });
  const lastSyncRef = useRef(state.lastSyncEpoch || 0);
  const loadingRef = useRef(false);

  const effectivePlan = useMemo(() => {
    const normalized = String(state.plan || "free").trim().toLowerCase();
    if (normalized === "free") return "free";
    if (!state.active) return "free";
    const nowSec = Math.floor(Date.now() / 1000);
    if (Number(state.expiresAtEpoch || 0) <= nowSec) return "free";
    return normalized;
  }, [state.active, state.expiresAtEpoch, state.plan]);

  useEffect(() => {
    lastSyncRef.current = state.lastSyncEpoch || 0;
    loadingRef.current = Boolean(state.loading);
  }, [state.lastSyncEpoch, state.loading]);

  const refresh = useCallback(async () => {
    const now = Date.now();
    if (loadingRef.current) {
      return { plan: state.plan, active: state.active, expiresAtEpoch: state.expiresAtEpoch };
    }
    if (now - (lastSyncRef.current || 0) < 5000) {
      return { plan: state.plan, active: state.active, expiresAtEpoch: state.expiresAtEpoch };
    }
    if (!auth.currentUser) {
      setState((prev) => ({ ...prev, plan: "free", active: false, expiresAtEpoch: 0 }));
      writeStoredEntitlement({ plan: "free", active: false, expiresAtEpoch: 0, lastSyncEpoch: Date.now() });
      return { plan: "free", active: false, expiresAtEpoch: 0 };
    }

    setState((prev) => ({ ...prev, loading: true }));
    try {
      const token = await auth.currentUser.getIdToken();
      const response = await fetch(`${API_BASE}/api/billing/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.error || "Failed to load subscription");
      }
      const next = {
        plan: String(data?.plan || "free").toLowerCase(),
        active: Boolean(data?.active),
        expiresAtEpoch: Number(data?.expiresAtEpoch || 0),
        lastSyncEpoch: Date.now(),
      };
      writeStoredEntitlement(next);
      setState((prev) => ({ ...prev, ...next, loading: false }));
      return next;
    } catch (error) {
      console.error(error);
      setState((prev) => ({ ...prev, loading: false }));
      return null;
    }
  }, [state.active, state.expiresAtEpoch, state.plan]);

  useEffect(() => {
    // Background refresh once per page-load.
    refresh().catch(() => {});
  }, [refresh]);

  const canUse = useCallback((featureKey) => hasFeature(effectivePlan, featureKey), [effectivePlan]);

  const requireFeature = useCallback(
    (featureKey, onAllowed) => {
      if (canUse(featureKey)) return onAllowed();
      toast.info("Upgrade your plan to unlock this feature.", { toastId: "premium-upgrade" });
      return undefined;
    },
    [canUse]
  );

  const value = useMemo(
    () => ({
      plan: effectivePlan,
      active: state.active,
      expiresAtEpoch: state.expiresAtEpoch,
      loading: state.loading,
      refresh,
      canUse,
      requireFeature,
    }),
    [effectivePlan, state.active, state.expiresAtEpoch, state.loading, refresh, canUse, requireFeature]
  );

  return value;
}

export default usePremium;
