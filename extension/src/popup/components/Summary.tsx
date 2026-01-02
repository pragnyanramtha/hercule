import { useState } from 'react';

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
    <div className="glass-panel rounded-xl p-5 hover:border-slate-700 transition-colors">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">📝</span>
        <h2 className="text-lg font-semibold text-slate-200">Summary</h2>
      </div>
      <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-light">
        {displayText}
      </p>

      {needsTruncation && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center gap-1 transition-colors"
        >
          {isExpanded ? 'Show Less' : 'Read More'}
          <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>↓</span>
        </button>
      )}
    </div>
  );
}

export default Summary;
