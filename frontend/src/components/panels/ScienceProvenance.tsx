import React from "react";

export const ScienceProvenance: React.FC = () => {
  return (
    <div className="bg-[#0f121e]/90 border border-[#232840] rounded-lg p-3.5 text-xs font-mono backdrop-blur-md shadow-2xl flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-[#232840] pb-2 mb-3">
        <div className="flex items-center space-x-2">
          <span>🔬</span>
          <span className="font-semibold text-gray-200 uppercase tracking-wider">
            Scientific Provenance & CRS Architecture
          </span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
          Zero Fabrication Policy
        </span>
      </div>

      <div className="space-y-3 overflow-y-auto pr-1">
        <div className="bg-[#0a0c16] p-2.5 rounded border border-[#1d2338]">
          <span className="font-bold text-orange-400 block mb-1 text-[11px]">
            1. Planetary Coordinate Reference System (CRS)
          </span>
          <p className="text-[11px] text-gray-300 leading-relaxed">
            Standard web mapping libraries (MapLibre, Mapbox, Leaflet) assume Earth Web Mercator (<span className="text-red-400">EPSG:3857</span>, R=6378.137km).
            Mars is an oblate ellipsoid (<span className="text-amber-300">R_eq=3396.19km, R_pol=3376.20km</span>) mapped under <span className="text-cyan-400">EPSG:104905</span> (Equidistant Cylindrical Mars) and <span className="text-cyan-400">IAU:49900</span> (Mars 2000 Sphere).
            Streaming NASA Mars Trek WMTS tiles directly into EPSG:3857 causes severe latitudinal distortion and distance errors of over 45%.
          </p>
        </div>

        <div className="bg-[#0a0c16] p-2.5 rounded border border-[#1d2338]">
          <span className="font-bold text-orange-400 block mb-1 text-[11px]">
            2. Shaded Relief vs. Numerical DTM Separation
          </span>
          <p className="text-[11px] text-gray-300 leading-relaxed">
            Visual shaded relief layers are rendered 8-bit RGB representations for human perception, with fixed illumination azimuths.
            MARS-X strictly isolates visual basemaps from raw, floating-point elevation DTMs (e.g. MOLA MEGDR, HRSC DTMs) required for calculating scientific slope, roughness, and traverse impedance.
          </p>
        </div>

        <div className="bg-[#0a0c16] p-2.5 rounded border border-[#1d2338]">
          <span className="font-bold text-orange-400 block mb-1 text-[11px]">
            3. Dataset Provenance Lifecycle
          </span>
          <div className="grid grid-cols-4 gap-1.5 mt-2 text-center text-[10px]">
            <div className="p-1.5 rounded bg-amber-950/30 border border-amber-800/40 text-amber-300">
              <span className="font-bold block">REGISTERED</span>
              Metadata linked
            </div>
            <div className="p-1.5 rounded bg-blue-950/30 border border-blue-800/40 text-blue-300">
              <span className="font-bold block">AVAILABLE</span>
              PDS verified
            </div>
            <div className="p-1.5 rounded bg-purple-950/30 border border-purple-800/40 text-purple-300">
              <span className="font-bold block">DOWNLOADED</span>
              Stored in cache
            </div>
            <div className="p-1.5 rounded bg-emerald-950/30 border border-emerald-800/40 text-emerald-300">
              <span className="font-bold block">VALIDATED</span>
              Checksum verified
            </div>
          </div>
        </div>

        <div className="bg-[#0a0c16] p-2.5 rounded border border-[#1d2338] text-[10px] text-gray-400">
          <span className="font-bold text-gray-200 block mb-0.5">Scientific Citation:</span>
          All 11 baseline datasets reference peer-reviewed NASA Planetary Data System (PDS) instruments and USGS Astrogeology Science Center repositories.
        </div>
      </div>
    </div>
  );
};

