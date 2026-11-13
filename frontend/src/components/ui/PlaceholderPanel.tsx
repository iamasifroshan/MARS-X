import React from "react";

interface PlaceholderPanelProps {
  title: string;
  badge?: string;
  icon?: string;
  description: string;
  plannedCapabilities: string[];
  scientificConstraints?: string;
}

export const PlaceholderPanel: React.FC<PlaceholderPanelProps> = ({
  title,
  badge = "Planned for Phase 2",
  icon = "🛰️",
  description,
  plannedCapabilities,
  scientificConstraints,
}) => {
  return (
    <div className="bg-[#121420]/80 border border-[#23273e] rounded-lg p-4 text-xs font-mono backdrop-blur-sm shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between border-b border-[#23273e] pb-2 mb-3">
          <div className="flex items-center space-x-2">
            <span className="text-base">{icon}</span>
            <span className="font-semibold text-gray-200 uppercase tracking-wider">{title}</span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
            {badge}
          </span>
        </div>

        <p className="text-gray-400 mb-3 leading-relaxed">{description}</p>

        <div className="mb-3">
          <span className="text-gray-500 uppercase text-[10px] tracking-wider block mb-1.5 font-bold">
            Planned Capabilities
          </span>
          <ul className="space-y-1">
            {plannedCapabilities.map((cap, idx) => (
              <li key={idx} className="flex items-start text-gray-300">
                <span className="text-orange-500 mr-1.5">▸</span>
                <span>{cap}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {scientificConstraints && (
        <div className="mt-3 pt-2 border-t border-[#23273e]/60 bg-red-950/20 rounded p-2 text-[10px] text-red-300 border-l-2 border-l-red-500">
          <span className="font-bold text-red-400 block mb-0.5">Scientific Constraint:</span>
          {scientificConstraints}
        </div>
      )}
    </div>
  );
};

