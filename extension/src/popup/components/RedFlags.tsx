import { useState } from 'react';

interface RedFlagsProps {
  redFlags: string[];
}

function RedFlags({ redFlags }: RedFlagsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const MAX_VISIBLE = 5;

  // Check if we need to show "Show More" button
  const needsExpansion = redFlags.length > MAX_VISIBLE;

  // Get display flags based on expansion state
  const displayFlags = needsExpansion && !isExpanded
    ? redFlags.slice(0, MAX_VISIBLE)
    : redFlags;

  if (redFlags.length === 0) {
    return (
      <div className="bg-emerald-950/30 border border-emerald-500/20 rounded-xl p-5 shadow-lg">
        <h2 className="text-lg font-semibold mb-2 text-emerald-400 flex items-center gap-2">
          <span>🛡️</span> Safe and Sound
        </h2>
        <p className="text-emerald-200/80 text-sm font-light">
          No major privacy concerns were identified.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-rose-950/30 border border-rose-500/20 rounded-xl p-5 shadow-lg">
      <h2 className="text-lg font-semibold mb-3 text-rose-400 flex items-center gap-2">
        <span>⚠️</span> Red Flags
      </h2>
      <ul className="space-y-3">
        {displayFlags.map((flag, index) => (
          <li key={index} className="flex items-start gap-3 text-sm text-rose-100/90 font-light bg-rose-900/20 p-2 rounded border border-rose-500/10">
            <span className="text-rose-500 mt-0.5">•</span>
            <span className="leading-relaxed">{flag}</span>
          </li>
        ))}
      </ul>

      {needsExpansion && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-4 w-full py-2 bg-rose-900/50 hover:bg-rose-900/80 border border-rose-800 rounded text-rose-300 text-xs uppercase tracking-wider font-semibold transition-all"
        >
          {isExpanded ? `Show Less` : `Show ${redFlags.length - MAX_VISIBLE} More`}
        </button>
      )}
    </div>
  );
}

export default RedFlags;
