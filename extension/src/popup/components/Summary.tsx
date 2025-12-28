import { useState } from 'react';

interface SummaryProps {
  summary: string;
}

function Summary({ summary }: SummaryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const MAX_LENGTH = 500;
  
  // Check if summary needs truncation
  const needsTruncation = summary.length > MAX_LENGTH;
  
  // Get display text based on expansion state
  const displayText = needsTruncation && !isExpanded 
    ? summary.substring(0, MAX_LENGTH) + '...'
    : summary;

  return (
    <div className="bg-white rounded-lg p-4 shadow">
      <h2 className="text-lg font-semibold mb-2 text-gray-800">Summary</h2>
      <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">
        {displayText}
      </p>
      
      {needsTruncation && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 text-blue-600 hover:text-blue-800 text-sm font-medium focus:outline-none focus:underline"
        >
          {isExpanded ? 'Show Less' : 'Read More'}
        </button>
      )}
    </div>
  );
}

export default Summary;
