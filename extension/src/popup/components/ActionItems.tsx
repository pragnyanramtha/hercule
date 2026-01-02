import { ActionItem } from '../../../../shared/types';

interface ActionItemsProps {
  actionItems: ActionItem[];
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
      <div className="bg-sky-950/30 border border-sky-500/20 rounded-xl p-5 shadow-lg">
        <h2 className="text-lg font-semibold mb-2 text-sky-400 flex items-center gap-2">
          <span>👍</span> Action Items
        </h2>
        <p className="text-sky-200/80 text-sm font-light">Policy appears acceptable.</p>
      </div>
    );
  }

  const sortedItems = sortByPriority(actionItems);

  return (
    <div className="bg-sky-950/30 border border-sky-500/20 rounded-xl p-5 shadow-lg">
      <h2 className="text-lg font-semibold mb-4 text-sky-400 flex items-center gap-2">
        <span>⚡</span> Action Items
      </h2>
      <ul className="space-y-3">
        {sortedItems.map((item, index) => {
          // Badge styles for dark mode
          let badgeClass = "bg-slate-800 text-slate-300 border-slate-700";
          let borderClass = "border-l-slate-500";

          if (item.priority === 'high') {
            badgeClass = "bg-rose-950/50 text-rose-300 border-rose-800";
            borderClass = "border-l-rose-500";
          } else if (item.priority === 'medium') {
            badgeClass = "bg-amber-950/50 text-amber-300 border-amber-800";
            borderClass = "border-l-amber-500";
          } else {
            badgeClass = "bg-emerald-950/50 text-emerald-300 border-emerald-800";
            borderClass = "border-l-emerald-500";
          }

          return (
            <li
              key={index}
              className={`flex items-start gap-4 text-sm bg-slate-900/40 rounded-lg p-4 border-l-4 ${borderClass} shadow-sm backdrop-blur-sm`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-1">
                  <span className={`inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded border ${badgeClass}`}>
                    {item.priority}
                  </span>
                </div>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 hover:underline leading-relaxed block"
                  >
                    {item.text}
                  </a>
                ) : (
                  <span className="text-slate-300 leading-relaxed block font-light">{item.text}</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default ActionItems;
