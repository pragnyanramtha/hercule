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

  // If no red flags, show positive message
  if (redFlags.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 shadow">
        <h2 className="text-lg font-semibold mb-2 text-green-700">Red Flags</h2>
        <p className="text-green-600 text-sm">
          ✓ No major concerns identified
        </p>
      </div>
    );
  }

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow">
      <h2 className="text-lg font-semibold mb-3 text-red-700">Red Flags</h2>
      <ul className="space-y-2">
        {displayFlags.map((flag, index) => (
          <li key={index} className="flex items-start gap-2 text-sm text-gray-800">
            <span className="text-orange-500 flex-shrink-0 mt-0.5">⚠️</span>
            <span className="leading-relaxed">{flag}</span>
          </li>
        ))}
      </ul>
      
      {needsExpansion && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 text-red-600 hover:text-red-800 text-sm font-medium focus:outline-none focus:underline"
        >
          {isExpanded ? `Show Less` : `Show More (${redFlags.length - MAX_VISIBLE} more)`}
        </button>
      )}
    </div>
  );
}

export default RedFlags;
