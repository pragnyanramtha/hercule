import { useState } from 'react';
import { Icons } from './Icons';

interface RedFlagsProps {
  redFlags: string[];
}

function RedFlags({ redFlags }: RedFlagsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const MAX_VISIBLE = 4;

  const needsExpansion = redFlags.length > MAX_VISIBLE;

  const displayFlags = needsExpansion && !isExpanded
    ? redFlags.slice(0, MAX_VISIBLE)
    : redFlags;

  if (redFlags.length === 0) {
    return (
      <div className="bg-emerald-950/20 border border-emerald-500/10 rounded-3xl p-6 backdrop-blur-sm">
        <h2 className="text-sm font-semibold mb-2 text-emerald-400 flex items-center gap-2 uppercase tracking-wide">
          <Icons.Shield className="w-4 h-4" /> Safe and Sound
        </h2>
        <p className="text-emerald-200/70 text-sm font-normal leading-relaxed">
          No major privacy concerns were identified.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-rose-950/20 border border-rose-500/10 rounded-3xl p-6 backdrop-blur-sm">
      <h2 className="text-sm font-semibold mb-4 text-rose-400 flex items-center gap-2 uppercase tracking-wide">
        <Icons.Alert className="w-4 h-4" /> Red Flags
      </h2>
      <ul className="space-y-3">
        {displayFlags.map((flag, index) => (
          <li key={index} className="flex items-start gap-3 group">
            <div className="mt-1 w-1.5 h-1.5 rounded-full bg-rose-500/50 group-hover:bg-rose-400 transition-colors flex-shrink-0" />
            <span className="text-sm text-rose-100/80 font-normal leading-relaxed group-hover:text-rose-100 transition-colors">
              {flag}
            </span>
          </li>
        ))}
      </ul>

      {needsExpansion && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-6 flex items-center gap-2 text-xs font-semibold text-rose-400 hover:text-rose-300 transition-colors uppercase tracking-wider"
        >
          {isExpanded ? 'Show Less' : `View ${redFlags.length - MAX_VISIBLE} More`}
          <Icons.ChevronDown className={`w-3 h-3 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      )}
    </div>
  );
}

export default RedFlags;
