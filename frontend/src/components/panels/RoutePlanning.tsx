import React from "react";
import { PlaceholderPanel } from "../ui/PlaceholderPanel";

export const RoutePlanning: React.FC = () => {
  return (
    <PlaceholderPanel
      title="Traverse & Route Engine"
      icon="🥾"
      badge="Phase 2 Pathfinding"
      description="Multicriteria anisotropic route optimization computing safe traverse paths for pressurized rovers and uncrewed robotic exploration."
      plannedCapabilities={[
        "Anisotropic slope impedance modeling using Minetti energy formulations",
        "Soil trafficability & sand dune slip-hazard avoidance",
        "Autonomous obstacle avoidance using HiRISE 25cm/px DTMs",
        "Solar shadow & thermal exposure budget along route waypoints"
      ]}
      scientificConstraints="Route costs cannot be reliably calculated from shaded relief rasters; strict ingestion of floating-point numerical DTMs is required."
    />
  );
};

