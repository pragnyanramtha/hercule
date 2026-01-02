import { ActionItem } from '../../../../shared/types';

interface ActionItemsProps {
  actionItems: ActionItem[];
}

/**
 * Get priority-based styling for action items
 */
function getPriorityStyles(priority: ActionItem['priority']) {
  switch (priority) {
    case 'high':
      return {
        badge: 'bg-red-100 text-red-700 border-red-200',
        icon: '⚠️',
        border: 'border-l-red-500',
      };
    case 'medium':
      return {
        badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
        icon: '→',
        border: 'border-l-yellow-500',
      };
    case 'low':
      return {
        badge: 'bg-green-100 text-green-700 border-green-200',
        icon: '○',
        border: 'border-l-green-500',
      };
    default:
      return {
        badge: 'bg-gray-100 text-gray-700 border-gray-200',
        icon: '→',
        border: 'border-l-gray-500',
      };
  }
}

/**
 * Sort action items by priority (high → medium → low)
 */
function sortByPriority(items: ActionItem[]): ActionItem[] {
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  return [...items].sort((a, b) => 
    (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3)
  );
}

function ActionItems({ actionItems }: ActionItemsProps) {
  if (actionItems.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow">
        <h2 className="text-lg font-semibold mb-2 text-blue-700">Action Items</h2>
        <p className="text-blue-600 text-sm">✓ Policy appears acceptable</p>
      </div>
    );
  }

  const sortedItems = sortByPriority(actionItems);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow">
      <h2 className="text-lg font-semibold mb-3 text-blue-700">Action Items</h2>
      <ul className="space-y-3">
        {sortedItems.map((item, index) => {
          const styles = getPriorityStyles(item.priority);
          return (
            <li 
              key={index} 
              className={`flex items-start gap-3 text-sm bg-white rounded-md p-3 border-l-4 ${styles.border} shadow-sm`}
            >
              <span className="flex-shrink-0 mt-0.5">{styles.icon}</span>
              <div className="flex-1 min-w-0">
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
                  <span className="text-gray-800 leading-relaxed">{item.text}</span>
                )}
                <span className={`inline-block ml-2 px-2 py-0.5 text-xs font-medium rounded border ${styles.badge}`}>
                  {item.priority}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default ActionItems;
