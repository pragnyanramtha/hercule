import { useState } from 'react';
import { Icons } from './Icons';

interface SummaryProps {
  summary: string;
}

function Summary({ summary }: SummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const MAX_LENGTH = 500;

  const needsTruncation = summary.length > MAX_LENGTH;

  const displayText = needsTruncation && !isExpanded
    ? summary.substring(0, MAX_LENGTH) + '...'
    : summary;

  return (
    <div className="bg-slate-900/40 border border-slate-800/60 rounded-3xl p-6 backdrop-blur-sm group hover:bg-slate-900/60 transition-colors duration-300">
      <div className="flex items-center gap-2 mb-4">
        <Icons.Document className="w-4 h-4 text-indigo-400" />
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Summary</h2>
      </div>
      <p className="text-slate-300/90 text-sm leading-7 whitespace-pre-wrap font-normal">
        {displayText}
      </p>

      {needsTruncation && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-6 flex items-center gap-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-wider"
        >
          {isExpanded ? 'Show Less' : 'Read Full Analysis'}
          <Icons.ChevronDown className={`w-3 h-3 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      )}
    </div>
  );
}

export default Summary;
