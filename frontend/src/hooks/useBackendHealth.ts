"use client";

import { useEffect, useState } from "react";
import { fetchHealth, fetchStatus, fetchSystemCapabilities } from "../lib/api";
import { HealthResponse, StatusResponse, SystemCapabilitiesResponse } from "../lib/types";

export interface BackendHealthState {
  isConnected: boolean;
  isLoading: boolean;
  health: HealthResponse | null;
  status: StatusResponse | null;
  capabilities: SystemCapabilitiesResponse | null;
  operatingMode: "cloud_demo" | "local_full_science" | "unknown";
  rasterAvailable: boolean;
  cloudDemoNotice: string | null;
  capabilityCheckFailed: boolean;
  lastChecked: Date | null;
  error: string | null;
}

export function useBackendHealth(normalIntervalMs = 15000): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>({
    isConnected: false,
    isLoading: true,
    health: null,
    status: null,
    capabilities: null,
    operatingMode: "unknown",
    rasterAvailable: false,
    cloudDemoNotice: null,
    capabilityCheckFailed: false,
    lastChecked: null,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    let timerId: NodeJS.Timeout | null = null;

    async function checkHealth() {
      try {
        const [healthRes, statusRes, capsRes] = await Promise.all([
          fetchHealth(),
          fetchStatus().catch(() => null),
          fetchSystemCapabilities().catch(() => null),
        ]);

        if (isMounted) {
          const isConnected = Boolean(healthRes);
          const caps = capsRes as SystemCapabilitiesResponse | null;
          setState({
            isConnected,
            isLoading: false,
            health: healthRes,
            status: statusRes,
            capabilities: caps,
            operatingMode: caps?.operating_mode || "unknown",
            rasterAvailable: Boolean(caps?.raster_processing_available),
            cloudDemoNotice: caps?.cloud_demo_notice || null,
            capabilityCheckFailed: isConnected && !caps,
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
            capabilities: null,
            operatingMode: "unknown",
            rasterAvailable: false,
            cloudDemoNotice: null,
            capabilityCheckFailed: true,
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
