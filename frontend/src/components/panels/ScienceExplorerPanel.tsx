"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  fetchDiscoveryCategories,
  fetchDiscoveries,
  fetchDiscoveryById,
  fetchScienceProfile,
  compareScienceLocations,
} from "../../lib/api";
import {
  DiscoveryCategory,
  ScienceDiscovery,
  ScienceProfile,
  ScienceComparisonResponse,
} from "../../lib/types";

interface ScienceExplorerPanelProps {
  onFlyToLocation?: (coords: { lat: number; lon: number; zoom?: number }) => void;
  onInspectCoordinates?: (coords: { lat: number; lon: number }) => void;
  initialDiscoveryId?: string | null;
}

export const ScienceExplorerPanel: React.FC<ScienceExplorerPanelProps> = ({
  onFlyToLocation,
  onInspectCoordinates,
  initialDiscoveryId,
}) => {
  const [categories, setCategories] = useState<DiscoveryCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [discoveries, setDiscoveries] = useState<ScienceDiscovery[]>([]);
  const [selectedDiscovery, setSelectedDiscovery] = useState<ScienceDiscovery | null>(null);
  const [liveProfile, setLiveProfile] = useState<ScienceProfile | null>(null);

  const [comparisonSites, setComparisonSites] = useState<ScienceDiscovery[]>([]);
  const [comparisonResult, setComparisonResult] = useState<ScienceComparisonResponse | null>(null);
  const [showComparisonModal, setShowComparisonModal] = useState<boolean>(false);

  const [loadingList, setLoadingList] = useState<boolean>(false);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [loadingComparison, setLoadingComparison] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load categories on mount
  useEffect(() => {
    fetchDiscoveryCategories()
      .then((cats) => setCategories(cats))
      .catch((err) => console.error("Failed to load discovery categories:", err));
  }, []);

  // Load discoveries list when category or search changes
  const loadDiscoveries = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const data = await fetchDiscoveries({
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        search: searchQuery.trim() || undefined,
      });
      setDiscoveries(data);

      // Auto-select first item or initial ID if nothing selected
      if (!selectedDiscovery && data.length > 0) {
        const target = initialDiscoveryId
          ? data.find((d) => d.id === initialDiscoveryId) || data[0]
          : data[0];
        handleSelectDiscovery(target);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load candidate discoveries");
    } finally {
      setLoadingList(false);
    }
  }, [selectedCategory, searchQuery, initialDiscoveryId, selectedDiscovery]);

  useEffect(() => {
    loadDiscoveries();
  }, [selectedCategory, searchQuery]);

  // Handle selecting a candidate discovery
  const handleSelectDiscovery = async (discovery: ScienceDiscovery) => {
    setSelectedDiscovery(discovery);
    setLoadingDetail(true);
    try {
      const [fullDisc, profile] = await Promise.all([
        fetchDiscoveryById(discovery.id).catch(() => discovery),
        fetchScienceProfile(discovery.latitude, discovery.longitude, 350.0).catch(() => null),
      ]);
      setSelectedDiscovery(fullDisc);
      setLiveProfile(profile);
    } catch (err) {
      console.error("Error loading discovery detail:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Toggle site in comparison list
  const toggleComparisonSite = (disc: ScienceDiscovery) => {
    if (comparisonSites.some((s) => s.id === disc.id)) {
      setComparisonSites((prev) => prev.filter((s) => s.id !== disc.id));
    } else {
      if (comparisonSites.length >= 5) {
        alert("Maximum 5 sites can be compared simultaneously.");
        return;
      }
      setComparisonSites((prev) => [...prev, disc]);
    }
  };

  // Run multi-site comparison
  const runComparison = async () => {
    if (comparisonSites.length < 2) return;
    setLoadingComparison(true);
    try {
      const payload = comparisonSites.map((s) => ({
        lat: s.latitude,
        lon: s.longitude,
        label: s.name,
      }));
      const res = await compareScienceLocations(payload);
      setComparisonResult(res);
      setShowComparisonModal(true);
    } catch (err) {
      console.error("Failed to compare locations:", err);
      alert("Comparison failed: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoadingComparison(false);
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case "high_res_terrain":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
      case "landing_site":
        return "bg-blue-500/20 text-blue-400 border-blue-500/40";
      case "geological_unit_contact":
        return "bg-amber-500/20 text-amber-400 border-amber-500/40";
      case "structural_feature":
        return "bg-purple-500/20 text-purple-400 border-purple-500/40";
      case "thermal_contrast":
        return "bg-cyan-500/20 text-cyan-400 border-cyan-500/40";
      case "multi_dataset_intersection":
        return "bg-rose-500/20 text-rose-400 border-rose-500/40";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/40";
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#080a14] text-gray-200 font-mono text-xs select-none">
      {/* Header Banner */}
      <div className="border-b border-[#1f253d] bg-[#0c0e1c] p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="text-xl">🔭</span>
            <h1 className="text-base font-bold text-gray-100 tracking-wider uppercase">
              Planetary Science Discovery System
            </h1>
            <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30 text-[10px] font-semibold">
              PHASE 8.7
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1 max-w-3xl leading-relaxed">
            Evidence-based exploration engine synthesizing authentic USGS SIM 3292 chronostratigraphy,
            MGS TES thermal inertia, THEMIS 256 ppd IR imagery, and high-resolution USGS CTX / HiRISE DTMs.
          </p>
        </div>

        {/* Comparison Actions */}
        <div className="flex items-center space-x-2 shrink-0">
          {comparisonSites.length > 0 && (
            <div className="flex items-center space-x-2 bg-[#12162a] border border-[#273050] px-3 py-1.5 rounded-lg">
              <span className="text-[11px] text-gray-300">
                Selected for comparison: <strong className="text-orange-400">{comparisonSites.length}</strong>
              </span>
              <button
                onClick={runComparison}
                disabled={comparisonSites.length < 2 || loadingComparison}
                className="px-2.5 py-1 rounded bg-orange-600 hover:bg-orange-500 text-white font-bold text-[11px] transition-colors disabled:opacity-50"
              >
                {loadingComparison ? "Comparing..." : "Compare Sites"}
              </button>
              <button
                onClick={() => setComparisonSites([])}
                className="text-gray-400 hover:text-white text-[10px] underline ml-1"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Category Pills & Search Bar */}
      <div className="border-b border-[#1b2034] bg-[#090b14] px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setSelectedCategory("all")}
            className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all border ${
              selectedCategory === "all"
                ? "bg-orange-500/20 text-orange-400 border-orange-500/50 shadow-md"
                : "bg-[#111422] text-gray-400 border-[#22283e] hover:text-gray-200"
            }`}
          >
            All Candidates ({discoveries.length})
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all border flex items-center space-x-1.5 ${
                selectedCategory === cat.id
                  ? `${getCategoryBadgeClass(cat.id)} font-bold shadow-md`
                  : "bg-[#111422] text-gray-400 border-[#22283e] hover:text-gray-200"
              }`}
            >
              <span>{cat.icon}</span>
              <span>{cat.title.split("(")[0].trim()}</span>
              <span className="text-[9px] opacity-75">({cat.discovery_count})</span>
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search candidate discoveries..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#111422] border border-[#22283e] rounded-md px-3 py-1 text-[11px] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-orange-500/60"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1 text-gray-500 hover:text-gray-300 text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Main Split Layout: Left List + Right Detail */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left List of Discoveries */}
        <div className="w-80 md:w-96 border-r border-[#1a1f33] bg-[#0a0c18] flex flex-col overflow-y-auto">
          {loadingList ? (
            <div className="p-8 text-center text-gray-500 space-y-2">
              <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p>Scanning Mars science targets...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-950/30 border border-red-800/40 rounded m-3 text-red-300 text-[11px] space-y-2">
              <p>{error}</p>
              <button
                type="button"
                onClick={() => loadDiscoveries()}
                className="px-2.5 py-1 bg-red-900/40 hover:bg-red-800/60 border border-red-700/60 rounded text-[10px] text-red-200 transition-colors"
              >
                Retry Scan
              </button>
            </div>
          ) : discoveries.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No discoveries match your current filter.
            </div>
          ) : (
            <div className="divide-y divide-[#15192a]">
              {discoveries.map((disc) => {
                const isSelected = selectedDiscovery?.id === disc.id;
                const isCompared = comparisonSites.some((s) => s.id === disc.id);
                return (
                  <div
                    key={disc.id}
                    onClick={() => handleSelectDiscovery(disc)}
                    className={`p-3.5 cursor-pointer transition-all ${
                      isSelected
                        ? "bg-[#181d33] border-l-4 border-orange-500"
                        : "hover:bg-[#101322] border-l-4 border-transparent"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className="font-bold text-gray-200 text-xs leading-snug">
                        {disc.name}
                      </span>
                      <button
                        title={isCompared ? "Remove from comparison" : "Add to comparison"}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleComparisonSite(disc);
                        }}
                        className={`px-1.5 py-0.5 rounded text-[10px] border transition-colors ${
                          isCompared
                            ? "bg-orange-500 text-white border-orange-400 font-bold"
                            : "bg-[#131627] text-gray-400 border-[#2b3350] hover:text-white"
                        }`}
                      >
                        {isCompared ? "✓ Compare" : "+ Compare"}
                      </button>
                    </div>

                    <div className="flex items-center space-x-2 mt-1.5">
                      <span
                        className={`px-1.5 py-0.2 rounded border text-[9px] uppercase font-semibold ${getCategoryBadgeClass(
                          disc.category
                        )}`}
                      >
                        {disc.category.replace(/_/g, " ")}
                      </span>
                      <span className="text-[10px] text-gray-400">
                        {disc.coordinate_display || `${disc.latitude.toFixed(2)}°, ${disc.longitude.toFixed(2)}°E`}
                      </span>
                      {disc.primary_source?.native_scale_or_spacing && (
                        <span className="text-[9px] text-cyan-400 border border-cyan-800/40 bg-cyan-950/20 px-1 rounded ml-auto">
                          {disc.primary_source.source_type === "cartographic_map" ? "1:20M Scale" : disc.primary_source.native_scale_or_spacing.split(" ")[0]}
                        </span>
                      )}
                    </div>

                    <p className="text-[10px] text-gray-400 mt-1.5 line-clamp-2 leading-relaxed">
                      {disc.scientific_significance}
                    </p>

                    <div className="flex flex-wrap gap-1 mt-2">
                      {(disc.supporting_datasets || []).slice(0, 3).map((ds) => (
                        <span
                          key={ds}
                          className="px-1 py-0.2 rounded bg-[#131726] border border-[#21273d] text-[9px] text-gray-400"
                        >
                          {ds}
                        </span>
                      ))}
                      {(disc.supporting_datasets || []).length > 3 && (
                        <span className="text-[9px] text-gray-500">
                          +{(disc.supporting_datasets || []).length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Detail & Live Science Profile */}
        <div className="flex-1 bg-[#070912] p-5 overflow-y-auto space-y-5">
          {selectedDiscovery ? (
            <>
              {/* Detail Header Banner */}
              <div className="bg-[#0f1224] border border-[#21273e] rounded-xl p-4 shadow-xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#1e2338] pb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${getCategoryBadgeClass(
                          selectedDiscovery.category
                        )}`}
                      >
                        {selectedDiscovery.category.replace(/_/g, " ")}
                      </span>
                      <span className="text-gray-400 text-[11px]">
                        ID: <strong className="text-gray-300">{selectedDiscovery.id}</strong>
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-gray-100 mt-1">
                      {selectedDiscovery.name}
                    </h2>
                    <p className="text-xs text-orange-400 font-semibold mt-0.5">
                      {selectedDiscovery.primary_feature}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-2">
                    {onFlyToLocation && (
                      <button
                        onClick={() =>
                          onFlyToLocation({
                            lat: selectedDiscovery.latitude,
                            lon: selectedDiscovery.longitude,
                            zoom: selectedDiscovery.category === "high_res_terrain" ? 9 : 6,
                          })
                        }
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center space-x-1.5 shadow-lg shadow-emerald-950/40 transition-colors"
                      >
                        <span>🚀</span>
                        <span>Fly to Location</span>
                      </button>
                    )}
                    {onInspectCoordinates && (
                      <button
                        onClick={() =>
                          onInspectCoordinates({
                            lat: selectedDiscovery.latitude,
                            lon: selectedDiscovery.longitude,
                          })
                        }
                        className="px-3 py-1.5 rounded-lg bg-[#1a2035] hover:bg-[#232b47] border border-[#2e3758] text-gray-200 text-[11px] font-semibold transition-colors"
                      >
                        <span>🔍</span>
                        <span>Inspect Coordinates</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Coordinate & Geodetic Parameters */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 pt-1 text-[11px]">
                  <div className="bg-[#14182e] p-2 rounded border border-[#232a45]">
                    <span className="text-gray-400 text-[10px] block">LATITUDE (IAU:49900)</span>
                    <span className="font-bold text-amber-300">
                      {selectedDiscovery.latitude.toFixed(5)}°
                    </span>
                  </div>
                  <div className="bg-[#14182e] p-2 rounded border border-[#232a45]">
                    <span className="text-gray-400 text-[10px] block">LONGITUDE (EAST 0-360°)</span>
                    <span className="font-bold text-amber-300">
                      {selectedDiscovery.longitude.toFixed(5)}°E
                    </span>
                  </div>
                  <div className="bg-[#14182e] p-2 rounded border border-[#232a45]">
                    <span className="text-gray-400 text-[10px] block">MOLA ELEVATION (AREOID)</span>
                    <span className="font-bold text-emerald-400">
                      {selectedDiscovery.terrain_context?.mola_elevation_m !== undefined
                        ? `${selectedDiscovery.terrain_context.mola_elevation_m.toFixed(1)} m`
                        : "Querying..."}
                    </span>
                  </div>
                  <div className="bg-[#14182e] p-2 rounded border border-[#232a45]">
                    <span className="text-gray-400 text-[10px] block">PRIMARY SOURCE SCALE / RES</span>
                    <span className="font-bold text-cyan-400">
                      {selectedDiscovery.primary_source?.native_scale_or_spacing ||
                        (selectedDiscovery.terrain_context?.highest_resolution_tier
                          ? `${selectedDiscovery.terrain_context.highest_resolution_tier.toUpperCase()} (${selectedDiscovery.terrain_context.finest_ground_spacing_m}m)`
                          : "Regional MOLA")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Scientific Significance Text */}
              <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span>📖</span>
                  <span>Scientific Significance &amp; Context</span>
                </h3>
                <p className="text-gray-300 leading-relaxed text-xs">
                  {selectedDiscovery.scientific_significance}
                </p>
              </div>

              {/* Evidence Classification (4 Distinct Classes) */}
              <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span>🔬</span>
                    <span>Evidence Classification Matrix</span>
                  </div>
                  <span className="text-[10px] text-gray-400 font-normal">
                    Epistemological rigor: observations vs inferences
                  </span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                  {/* Direct Sensor Observations */}
                  <div className="bg-[#12162a] border border-emerald-900/40 rounded-lg p-3">
                    <div className="flex items-center space-x-1.5 text-emerald-400 font-bold mb-1.5">
                      <span>🟢</span>
                      <span>Direct Sensor Observations</span>
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                      {(selectedDiscovery.evidence_classes?.direct_sensor_observations || selectedDiscovery.evidence_classes?.measured_observations)?.map((item, idx) => (
                        <li key={idx} className="leading-relaxed">{item}</li>
                      )) || <li>Raw telemetry in external NASA PDS archives</li>}
                    </ul>
                  </div>

                  {/* Derived Physical Measurements */}
                  <div className="bg-[#12162a] border border-blue-900/40 rounded-lg p-3">
                    <div className="flex items-center space-x-1.5 text-blue-400 font-bold mb-1.5">
                      <span>🔵</span>
                      <span>Derived Measurements</span>
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                      {selectedDiscovery.evidence_classes?.derived_measurements?.map((item, idx) => (
                        <li key={idx} className="leading-relaxed">{item}</li>
                      )) || <li>Interpolated terrain elevation and slope</li>}
                    </ul>
                  </div>

                  {/* Mapped Geological Interpretations */}
                  <div className="bg-[#12162a] border border-amber-900/40 rounded-lg p-3">
                    <div className="flex items-center space-x-1.5 text-amber-300 font-bold mb-1.5">
                      <span>🗺️</span>
                      <span>Mapped Geological Interpretations</span>
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                      {(selectedDiscovery.evidence_classes?.mapped_geological_interpretations || [
                        "USGS SIM 3292 1:20M cartographic unit boundaries & contacts",
                      ]).map((item, idx) => (
                        <li key={idx} className="leading-relaxed">{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Indicative Proxies */}
                  <div className="bg-[#12162a] border border-yellow-900/40 rounded-lg p-3">
                    <div className="flex items-center space-x-1.5 text-yellow-400 font-bold mb-1.5">
                      <span>🟡</span>
                      <span>Indicative Proxies</span>
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                      {selectedDiscovery.evidence_classes?.indicative_proxies?.map((item, idx) => (
                        <li key={idx} className="leading-relaxed">{item}</li>
                      )) || <li>Thermophysical grain size proxy (TES)</li>}
                    </ul>
                  </div>

                  {/* Potential Investigations */}
                  <div className="bg-[#12162a] border border-purple-900/40 rounded-lg p-3 md:col-span-2">
                    <div className="flex items-center space-x-1.5 text-purple-400 font-bold mb-1.5">
                      <span>🟣</span>
                      <span>Potential Investigations (Hypotheses)</span>
                    </div>
                    <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                      {selectedDiscovery.evidence_classes?.potential_investigations?.map((item, idx) => (
                        <li key={idx} className="leading-relaxed">{item}</li>
                      )) || <li>Candidate exploration hypothesis to verify</li>}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Multi-Dataset Context Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Geological Context (SIM 3292) */}
                <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                  <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                    <span>🌋</span>
                    <span>Geological Framework (USGS SIM 3292)</span>
                  </h3>
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">Unit Symbol:</span>
                      <span className="font-bold text-amber-300">
                        {selectedDiscovery.geological_context?.unit_symbol || liveProfile?.geological_analysis?.unit_code || "Unknown"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">Unit Name:</span>
                      <span className="text-gray-200 text-right max-w-xs">
                        {selectedDiscovery.geological_context?.unit_name || liveProfile?.geological_analysis?.unit_name || "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">Stratigraphic Age:</span>
                      <span className="text-orange-300 font-semibold">
                        {selectedDiscovery.geological_context?.stratigraphic_age || liveProfile?.geological_analysis?.stratigraphic_age || "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">Lithology / Interpretation:</span>
                      <span className="text-gray-300 text-right max-w-xs">
                        {selectedDiscovery.geological_context?.primary_lithology || liveProfile?.geological_analysis?.interpretation || "N/A"}
                      </span>
                    </div>

                    {liveProfile?.geological_analysis?.nearest_structure && (
                      <div className="bg-[#121527] p-2 rounded mt-2 border border-[#21273f]">
                        <span className="text-[10px] text-gray-400 block">NEAREST STRUCTURE (SIM 3292):</span>
                        <div className="flex justify-between items-center mt-0.5">
                          <span className="text-purple-300 font-bold">
                            {liveProfile.geological_analysis.nearest_structure.type}
                          </span>
                          <span className="text-gray-400">
                            {liveProfile.geological_analysis.nearest_structure.distance_km.toFixed(1)} km away
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Thermal & Thermophysical Context (MGS TES & THEMIS) */}
                <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                  <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                    <span>🌡️</span>
                    <span>Thermophysical Context (TES &amp; THEMIS)</span>
                  </h3>
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">TES Thermal Inertia:</span>
                      <span className="font-bold text-cyan-300">
                        {typeof selectedDiscovery.thermal_context?.tes_thermal_inertia_si === "number"
                          ? `${selectedDiscovery.thermal_context.tes_thermal_inertia_si.toFixed(1)} tiu`
                          : typeof liveProfile?.thermal_analysis?.tes_thermal_inertia_si === "number"
                          ? `${liveProfile.thermal_analysis.tes_thermal_inertia_si.toFixed(1)} tiu`
                          : "Pending"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">Thermophysical Unit:</span>
                      <span className="text-gray-300 text-right max-w-xs">
                        {selectedDiscovery.thermal_context?.thermophysical_unit || liveProfile?.thermal_analysis?.thermophysical_interpretation || "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-[#1b2034] pb-1">
                      <span className="text-gray-400">THEMIS IR Regional Coverage:</span>
                      <span className={selectedDiscovery.thermal_context?.themis_ir_covered ? "text-emerald-400 font-bold" : "text-gray-500"}>
                        {selectedDiscovery.thermal_context?.themis_ir_covered ? "Covered (256 ppd Band 9 Mosaic)" : "Outside Sinus Meridiani footprint"}
                      </span>
                    </div>
                    {selectedDiscovery.thermal_context?.themis_band_9_dn !== undefined && (
                      <div className="flex justify-between border-b border-[#1b2034] pb-1">
                        <span className="text-gray-400">THEMIS Band 9 Display DN:</span>
                        <span className="font-bold text-gray-200">
                          {selectedDiscovery.thermal_context.themis_band_9_dn.toFixed(1)} / 255
                        </span>
                      </div>
                    )}
                    <div className="p-2 bg-[#121527] rounded border border-[#21273f] text-[10px] text-gray-400 mt-2">
                      <strong className="text-cyan-400">Thermophysical Note:</strong> Thermal inertia (J m⁻² K⁻¹ s⁻¹/²) indicates physical state of surface particles (fine dust vs duricrust vs bedrock), NOT kinetic temperature.
                    </div>
                  </div>
                </div>
              </div>

              {/* Actionable Investigation Opportunities */}
              <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span>🎯</span>
                  <span>Suggested Exploration Investigations</span>
                </h3>
                <ul className="space-y-1.5 text-xs text-gray-300">
                  {(selectedDiscovery.suggested_investigations || []).map((inv, idx) => (
                    <li key={idx} className="flex items-start space-x-2">
                      <span className="text-orange-500 font-bold">▸</span>
                      <span className="leading-relaxed">{inv}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Scientific Limitations & Caveats */}
              <div className="bg-amber-950/20 border border-amber-600/30 rounded-xl p-4 text-xs">
                <h3 className="font-bold text-amber-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <span>⚠️</span>
                  <span>Scientific Limitations &amp; Caveats</span>
                </h3>
                <ul className="space-y-1 text-gray-300 text-[11px] list-disc list-inside">
                  {(selectedDiscovery.scientific_limitations || []).map((lim, idx) => (
                    <li key={idx} className="leading-relaxed">{lim}</li>
                  ))}
                  <li>Hypotheses require in-situ rover or crewed mission sampling to confirm.</li>
                </ul>
              </div>

              {/* Nearby Candidate Discoveries Corridor */}
              {liveProfile?.nearby_candidate_discoveries && liveProfile.nearby_candidate_discoveries.length > 0 && (
                <div className="bg-[#0e1122] border border-[#1f253d] rounded-xl p-4">
                  <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>🧭</span>
                    <span>Nearby Science Discovery Corridor (&lt; 350 km)</span>
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {liveProfile.nearby_candidate_discoveries.map((nb) => (
                      <div
                        key={nb.id}
                        onClick={() => handleSelectDiscovery(nb)}
                        className="p-2.5 bg-[#12162a] border border-[#21273f] rounded-lg hover:border-orange-500/50 cursor-pointer transition-colors"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-gray-200 text-[11px]">{nb.name}</span>
                          {nb.distance_km !== undefined && (
                            <span className="text-[10px] text-orange-400 font-mono">
                              {nb.distance_km.toFixed(1)} km
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">
                          {nb.primary_feature}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-12 text-center text-gray-500">
              Select a candidate discovery from the list to view its complete scientific profile.
            </div>
          )}
        </div>
      </div>

      {/* Multi-Site Comparison Modal */}
      {showComparisonModal && comparisonResult && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0c0f1e] border border-[#273050] rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
            {/* Modal Header */}
            <div className="p-4 border-b border-[#21273f] flex items-center justify-between bg-[#0e1224]">
              <div className="flex items-center space-x-2">
                <span className="text-lg">📊</span>
                <h2 className="text-sm font-bold text-gray-100 uppercase tracking-wider">
                  Multi-Site Science Discovery Comparison ({comparisonResult.summary.count} Sites)
                </h2>
              </div>
              <button
                onClick={() => setShowComparisonModal(false)}
                className="text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-[#1a2038]"
              >
                ✕ Close
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-5 overflow-y-auto space-y-4">
              {/* Summary Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-[#12162a] p-3 rounded-xl border border-[#222a45]">
                  <span className="text-[10px] text-gray-400 block">HIGHEST ELEVATION</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {comparisonResult.summary.highest_elevation_site.elevation_m.toFixed(1)} m
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    at ({comparisonResult.summary.highest_elevation_site.lat.toFixed(2)}°, {comparisonResult.summary.highest_elevation_site.lon.toFixed(2)}°E)
                  </span>
                </div>
                <div className="bg-[#12162a] p-3 rounded-xl border border-[#222a45]">
                  <span className="text-[10px] text-gray-400 block">LOWEST ELEVATION</span>
                  <span className="text-sm font-bold text-blue-400">
                    {comparisonResult.summary.lowest_elevation_site.elevation_m.toFixed(1)} m
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    at ({comparisonResult.summary.lowest_elevation_site.lat.toFixed(2)}°, {comparisonResult.summary.lowest_elevation_site.lon.toFixed(2)}°E)
                  </span>
                </div>
                <div className="bg-[#12162a] p-3 rounded-xl border border-[#222a45]">
                  <span className="text-[10px] text-gray-400 block">HIGHEST THERMAL INERTIA</span>
                  <span className="text-sm font-bold text-cyan-400">
                    {comparisonResult.summary.highest_thermal_inertia_site.ti.toFixed(1)} tiu
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    at ({comparisonResult.summary.highest_thermal_inertia_site.lat.toFixed(2)}°, {comparisonResult.summary.highest_thermal_inertia_site.lon.toFixed(2)}°E)
                  </span>
                </div>
              </div>

              {/* Comparison Table */}
              <div className="border border-[#222a45] rounded-xl overflow-x-auto">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="bg-[#141930] text-gray-300 border-b border-[#222a45]">
                      <th className="p-3">Site / Target</th>
                      <th className="p-3">Coordinates</th>
                      <th className="p-3">DTM Elevation</th>
                      <th className="p-3">Resolution Tier</th>
                      <th className="p-3">Geology Unit (SIM 3292)</th>
                      <th className="p-3">TES Thermal Inertia</th>
                      <th className="p-3">THEMIS IR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#181e36]">
                    {comparisonResult.sites.map((site, idx) => {
                      const matchedDisc = comparisonSites[idx];
                      return (
                        <tr key={idx} className="hover:bg-[#12162a]">
                          <td className="p-3 font-bold text-gray-200">
                            {matchedDisc?.name || `Site #${idx + 1}`}
                          </td>
                          <td className="p-3 text-amber-300">
                            {site.query_latitude.toFixed(3)}°, {site.query_longitude.toFixed(3)}°E
                          </td>
                          <td className="p-3 text-emerald-400 font-semibold">
                            {site.elevation_analysis.elevation_m !== null
                              ? `${site.elevation_analysis.elevation_m.toFixed(1)} m`
                              : "NoData"}
                          </td>
                          <td className="p-3 text-cyan-300">
                            {site.terrain_analysis.finest_tier.toUpperCase()} ({site.terrain_analysis.ground_spacing_m}m)
                          </td>
                          <td className="p-3 text-gray-300">
                            <span className="font-bold text-amber-300">
                              {site.geological_analysis.unit_code || "Unknown"}
                            </span>{" "}
                            - {site.geological_analysis.unit_name || "N/A"}
                          </td>
                          <td className="p-3 text-cyan-400 font-bold">
                            {site.thermal_analysis.tes_thermal_inertia_si !== null
                              ? `${site.thermal_analysis.tes_thermal_inertia_si.toFixed(1)} tiu`
                              : "N/A"}
                          </td>
                          <td className="p-3 text-gray-400">
                            {site.thermal_analysis.themis_day_ir.covered ? "Covered" : "No"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
