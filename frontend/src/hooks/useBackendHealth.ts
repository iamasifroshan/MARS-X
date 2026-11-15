"use client";

import { useEffect, useState } from "react";
import { fetchHealth, fetchStatus } from "../lib/api";
import { HealthResponse, StatusResponse } from "../lib/types";

export interface BackendHealthState {
  isConnected: boolean;
  isLoading: boolean;
  health: HealthResponse | null;
  status: StatusResponse | null;
  lastChecked: Date | null;
  error: string | null;
}

export function useBackendHealth(normalIntervalMs = 15000): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>({
    isConnected: false,
    isLoading: true,
    health: null,
    status: null,
    lastChecked: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    let timerId: NodeJS.Timeout | null = null;

    async function checkHealth() {
      try {
        const [healthRes, statusRes] = await Promise.all([
          fetchHealth(),
          fetchStatus().catch(() => null),
        ]);

        if (isMounted) {
          setState({
            isConnected: true,
            isLoading: false,
            health: healthRes,
            status: statusRes,
            lastChecked: new Date(),
            error: null,
          });
        }
        // When connected, schedule next check at normalIntervalMs
        if (isMounted) {
          timerId = setTimeout(checkHealth, normalIntervalMs);
        }
      } catch (err) {
        if (isMounted) {
          setState({
            isConnected: false,
            isLoading: false,
            health: null,
            status: null,
            lastChecked: new Date(),
            error: err instanceof Error ? err.message : "Backend unreachable",
          });
        }
        // When disconnected, poll aggressively (every 3000ms with small jitter) for fast recovery
        if (isMounted) {
          const retryDelay = 2500 + Math.random() * 1000;
          timerId = setTimeout(checkHealth, retryDelay);
        }
      }
    }

    checkHealth();

    return () => {
      isMounted = false;
      if (timerId) {
        clearTimeout(timerId);
      }
    };
  }, [normalIntervalMs]);

  return state;
}

