import React from "react";
import { PlaceholderPanel } from "../ui/PlaceholderPanel";

export const MissionInfo: React.FC = () => {
  return (
    <PlaceholderPanel
      title="Mission & EVA Console"
      icon="🧑‍🚀"
      badge="Phase 2 Surface Ops"
      description="Plan and coordinate crewed surface Extravehicular Activities (EVAs) and robotic rover operations for human Mars landing campaigns."
      plannedCapabilities={[
        "Astronaut metabolic energy & O2 consumable margin tracking",
        "Hab-to-Rover line-of-sight & UHF communication relay windows",
        "Orbiter direct-to-Earth (DTE) pass schedules (MRO, Odyssey, TGO)",
        "Contingency walkback radius with 45-minute emergency buffer"
      ]}
      scientificConstraints="Life-support duration calculations require validated metabolic rate models under 0.38g Martian surface gravity."
    />
  );
};

