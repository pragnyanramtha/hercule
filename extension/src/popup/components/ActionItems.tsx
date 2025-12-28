import { ActionItem } from '../../../../shared/types';

interface ActionItemsProps {
  actionItems: ActionItem[];
}

function ActionItems({ actionItems }: ActionItemsProps) {
  // If no action items, show positive message
  if (actionItems.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow">
        <h2 className="text-lg font-semibold mb-2 text-blue-700">Action Items</h2>
        <p className="text-blue-600 text-sm">
          ✓ Policy appears acceptable
        </p>
      </div>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow">
      <h2 className="text-lg font-semibold mb-3 text-blue-700">Action Items</h2>
      <ul className="space-y-2">
        {actionItems.map((item, index) => (
          <li key={index} className="flex items-start gap-2 text-sm text-gray-800">
            <span className="text-blue-500 flex-shrink-0 mt-0.5">→</span>
            {item.url ? (
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 hover:underline leading-relaxed"
              >
                {item.text}
              </a>
            ) : (
              <span className="leading-relaxed">{item.text}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ActionItems;
