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

  return (
    <div className="bg-[#101322]/90 border border-[#232840] rounded-lg p-3.5 text-xs font-mono backdrop-blur-md shadow-2xl flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-[#232840] pb-2 mb-3">
        <div className="flex items-center space-x-2">
          <span>📚</span>
          <span className="font-semibold text-gray-200 uppercase tracking-wider">
            NASA Scientific Dataset Catalogue
          </span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/40">
          {datasets.length} Registered Sources
        </span>
      </div>

      {/* Filter and search bar */}
      <div className="space-y-2 mb-3">
        <input
          type="text"
          placeholder="Filter datasets by instrument, id, or name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-[#0a0c16] border border-[#22283e] rounded px-2.5 py-1.5 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-orange-500 text-xs"
        />

        <div className="flex items-center space-x-1 overflow-x-auto pb-1 text-[10px]">
          <span className="text-gray-500 mr-1">MISSION:</span>
          {missions.map((m) => (
            <button
              key={m}
              onClick={() => setFilterMission(m)}
              className={`px-2 py-0.5 rounded whitespace-nowrap transition-colors ${
                filterMission === m
                  ? "bg-orange-500 text-white font-bold"
                  : "bg-[#141829] text-gray-400 hover:text-gray-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Catalogue List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[380px]">
        {loading ? (
          <div className="text-center py-8 text-gray-400">
            <div className="inline-block animate-spin mr-2">⚙️</div>
            Querying backend dataset registry...
          </div>
        ) : error ? (
          <div className="bg-red-950/30 border border-red-800/50 rounded p-3 text-red-300">
            <div className="font-bold mb-1">Backend Connection Notice:</div>
            <p className="text-[11px] mb-2">{error}</p>
            <button
              onClick={() => loadData(filterMission)}
              className="px-2.5 py-1 bg-red-900/50 hover:bg-red-800/60 text-red-200 rounded text-[10px]"
            >
              Retry Connection
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No datasets matched query criteria.
          </div>
        ) : (
          filtered.map((dataset) => (
            <div
              key={dataset.dataset_id}
              onClick={() => {
                setSelectedItem(dataset);
                if (onSelectDataset) onSelectDataset(dataset);
              }}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                selectedItem?.dataset_id === dataset.dataset_id
                  ? "bg-[#1a2038] border-orange-500 shadow-md"
                  : "bg-[#0b0d18] border-[#1d2338] hover:border-gray-600"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-bold text-gray-100 text-[11px] block">
                    {dataset.name}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {dataset.mission} • {dataset.instrument}
                  </span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  {dataset.processing_status}
                </span>
              </div>

              <div className="mt-1.5 text-[10px] text-gray-400 grid grid-cols-2 gap-1 bg-black/20 p-1.5 rounded">
                <div>Type: <span className="text-gray-300">{dataset.product_type}</span></div>
                <div>Res: <span className="text-gray-300">{dataset.spatial_resolution || "N/A"}</span></div>
                <div>Format: <span className="text-gray-300">{dataset.data_format}</span></div>
                <div>CRS: <span className="text-amber-300 font-mono">{dataset.crs}</span></div>
              </div>

              <p className="mt-1.5 text-[10px] text-gray-400 line-clamp-2 leading-relaxed">
                {dataset.description}
              </p>
            </div>
          ))
        )}
      </div>

      {/* Selected dataset detail modal/drawer */}
      {selectedItem && (
        <div className="mt-3 pt-2.5 border-t border-[#232840] bg-[#090b14] p-2.5 rounded text-[10px]">
          <div className="flex items-center justify-between mb-1">
            <span className="font-bold text-orange-400">{selectedItem.name} Details</span>
            <button
              onClick={() => setSelectedItem(null)}
              className="text-gray-500 hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="text-gray-400 space-y-1">
            <div>Footprint: <span className="text-gray-200">{selectedItem.geographic_footprint || "Global"}</span></div>
            <div>Source URL:{" "}
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
                <span className="font-bold text-red-400">Limitations: </span>
                {selectedItem.scientific_limitations}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

