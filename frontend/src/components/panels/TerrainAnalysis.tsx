import React from "react";
import { PlaceholderPanel } from "../ui/PlaceholderPanel";

export const TerrainAnalysis: React.FC = () => {
  return (
    <PlaceholderPanel
      title="Terrain DTM Intelligence"
      icon="⛰️"
      badge="Phase 2 Geospatial"
      description="Planetary terrain characterisation engine performing slope, aspect, rugosity, and viewshed analysis on Martian elevation models."
      plannedCapabilities={[
        "MOLA MEGDR global topographic base (463m/px elevation model)",
        "HRSC regional stereophotogrammetric DTMs (50m - 100m/px)",
        "HiRISE ultra-high-resolution DTMs (1m - 2m/px) for landing site hazards",
        "Geodetic slope angle extraction and boulder distribution metrics"
      ]}
      scientificConstraints="Separates visual shaded-relief imagery from numerical elevation arrays. No slope calculation will run on lossy 8-bit visual tiles."
    />
  );
};

