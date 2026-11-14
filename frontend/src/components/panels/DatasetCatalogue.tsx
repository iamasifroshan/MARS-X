"use client";

import React, { useEffect, useState } from "react";
import { DatasetMetadata } from "../../lib/types";
import { fetchDatasets } from "../../lib/api";

interface DatasetCatalogueProps {
  onSelectDataset?: (dataset: DatasetMetadata) => void;
}

export const DatasetCatalogue: React.FC<DatasetCatalogueProps> = ({ onSelectDataset }) => {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterMission, setFilterMission] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedItem, setSelectedItem] = useState<DatasetMetadata | null>(null);

  const loadData = async (mission?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDatasets(mission === "ALL" ? undefined : mission);
      setDatasets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load catalogue from API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(filterMission);
  }, [filterMission]);

  const missions = ["ALL", "MGS", "Mars Express", "USGS", "MRO", "Mars Odyssey", "MSL", "Mars 2020"];

  const filtered = datasets.filter((d) => {
    const q = searchQuery.toLowerCase();
    return (
      d.name.toLowerCase().includes(q) ||
      d.instrument.toLowerCase().includes(q) ||
      d.dataset_id.toLowerCase().includes(q)
    );
  });

  const isLocallyAvailable = (datasetId: string) => {
    return datasetId === "mola-megdr" || datasetId === "ctx-edr";
  };

  return (
    <div className="bg-[#101322]/90 border border-[#232840] rounded-lg p-5 text-xs font-mono backdrop-blur-md shadow-2xl flex flex-col h-full">
      <div className="flex flex-wrap items-center justify-between border-b border-[#232840] pb-3 mb-4 gap-2">
        <div className="flex items-center space-x-2.5">
          <span className="text-xl">📚</span>
          <div>
            <h2 className="font-bold text-sm text-gray-100 uppercase tracking-wider">
              NASA Planetary Data System (PDS) Catalogue
            </h2>
            <p className="text-[11px] text-gray-400">
              Authoritative Martian elevation, imagery, and environmental science sources.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] px-2.5 py-1 rounded bg-blue-950/80 text-blue-300 border border-blue-800/40 font-semibold">
            {datasets.length} Registered Sources
          </span>
          <span className="text-[10px] px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/40 font-semibold">
            2 Tiers Locally Validated
          </span>
        </div>
      </div>

      {/* Filter and search bar */}
      <div className="space-y-2.5 mb-4">
        <input
          type="text"
          placeholder="Filter datasets by instrument, id, mission, or description..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-[#0a0c16] border border-[#22283e] rounded-lg px-3 py-2 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-orange-500 text-xs shadow-inner"
        />

        <div className="flex items-center space-x-1 overflow-x-auto pb-1 text-[11px]">
          <span className="text-gray-500 mr-1.5 font-semibold">MISSION FILTER:</span>
          {missions.map((m) => (
            <button
              key={m}
              onClick={() => setFilterMission(m)}
              className={`px-2.5 py-1 rounded-md whitespace-nowrap transition-colors font-medium ${
                filterMission === m
                  ? "bg-orange-500 text-white font-bold shadow-md shadow-orange-950/50"
                  : "bg-[#141829] text-gray-400 hover:text-gray-200 hover:bg-[#1a2035]"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Catalogue List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 min-h-[350px]">
        {loading ? (
          <div className="text-center py-16 text-gray-400">
            <div className="inline-block animate-spin mr-2">⚙️</div>
            Querying backend NASA/PDS dataset registry...
          </div>
        ) : error ? (
          <div className="bg-red-950/30 border border-red-800/50 rounded-lg p-4 text-red-300">
            <div className="font-bold mb-1">Backend Connection Notice:</div>
            <p className="text-[11px] mb-3">{error}</p>
            <button
              onClick={() => loadData(filterMission)}
              className="px-3 py-1.5 bg-red-900/60 hover:bg-red-800/70 text-red-200 rounded font-semibold text-xs"
            >
              Retry Connection
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            No datasets matched query criteria.
          </div>
        ) : (
          filtered.map((dataset) => {
            const localReady = isLocallyAvailable(dataset.dataset_id);
            return (
              <div
                key={dataset.dataset_id}
                onClick={() => {
                  setSelectedItem(dataset);
                  if (onSelectDataset) onSelectDataset(dataset);
                }}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  selectedItem?.dataset_id === dataset.dataset_id
                    ? "bg-[#1a2038] border-orange-500 shadow-lg shadow-orange-950/30"
                    : "bg-[#0b0d18] border-[#1d2338] hover:border-gray-600 hover:bg-[#101322]"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-gray-100 text-xs">
                        {dataset.name}
                      </span>
                      {localReady && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded font-bold uppercase bg-emerald-950 text-emerald-400 border border-emerald-700/50">
                          LOCAL DATA READY
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-400">
                      {dataset.mission} • {dataset.instrument}
                    </span>
                  </div>
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${
                      localReady
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                        : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {localReady ? "ANALYSIS READY" : dataset.processing_status}
                  </span>
                </div>

                <div className="mt-2 text-[10px] text-gray-400 grid grid-cols-2 md:grid-cols-4 gap-2 bg-black/25 p-2 rounded border border-[#181d2e]">
                  <div>Type: <span className="text-gray-300 font-medium">{dataset.product_type}</span></div>
                  <div>Res: <span className="text-gray-300 font-medium">{dataset.spatial_resolution || "N/A"}</span></div>
                  <div>Format: <span className="text-gray-300 font-medium">{dataset.data_format}</span></div>
                  <div>CRS: <span className="text-amber-300 font-mono font-medium">{dataset.crs}</span></div>
                </div>

                <p className="mt-2 text-[11px] text-gray-300 line-clamp-2 leading-relaxed">
                  {dataset.description}
                </p>
              </div>
            );
          })
        )}
      </div>

      {/* Selected dataset detail modal/drawer */}
      {selectedItem && (
        <div className="mt-4 pt-3 border-t border-[#232840] bg-[#090b14] p-3.5 rounded-lg text-[11px]">
          <div className="flex items-center justify-between mb-2">
            <span className="font-bold text-orange-400">{selectedItem.name} — Full PDS Metadata</span>
            <button
              onClick={() => setSelectedItem(null)}
              className="text-gray-500 hover:text-white px-1 font-bold"
            >
              ✕
            </button>
          </div>
          <div className="text-gray-400 space-y-1.5">
            <div>Footprint: <span className="text-gray-200">{selectedItem.geographic_footprint || "Global"}</span></div>
            <div>Source Archive:{" "}
              <a
                href={selectedItem.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:underline break-all"
              >
                {selectedItem.source_url}
              </a>
            </div>
            {selectedItem.scientific_limitations && (
              <div className="text-red-300/90 pt-1">
                <span className="font-bold text-red-400">Scientific Limitations: </span>
                {selectedItem.scientific_limitations}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
