import { ActionItem } from '../../../../shared/types';
import { Icons } from './Icons';

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
      <div className="bg-sky-950/20 border border-sky-500/10 rounded-3xl p-6 backdrop-blur-sm">
        <h2 className="text-sm font-semibold mb-2 text-sky-400 flex items-center gap-2 uppercase tracking-wide">
          <Icons.Check className="w-4 h-4" /> Action Items
        </h2>
        <p className="text-sky-200/70 text-sm font-normal leading-relaxed">Policy appears acceptable.</p>
      </div>
    );
  }

  const sortedItems = sortByPriority(actionItems);

  return (
    <div className="bg-sky-950/20 border border-sky-500/10 rounded-3xl p-6 backdrop-blur-sm">
      <h2 className="text-sm font-semibold mb-4 text-sky-400 flex items-center gap-2 uppercase tracking-wide">
        <Icons.Bolt className="w-4 h-4" /> Action Items
      </h2>
      <ul className="space-y-3">
        {sortedItems.map((item, index) => {
          // Badge styles for dark mode
          let badgeClass = "bg-slate-800 text-slate-300 border-slate-700";
          let borderClass = "border-l-slate-500";

          if (item.priority === 'high') {
            badgeClass = "bg-rose-500/10 text-rose-300 border-rose-500/20";
            borderClass = "border-l-rose-500";
          } else if (item.priority === 'medium') {
            badgeClass = "bg-amber-500/10 text-amber-300 border-amber-500/20";
            borderClass = "border-l-amber-500";
          } else {
            badgeClass = "bg-emerald-500/10 text-emerald-300 border-emerald-500/20";
            borderClass = "border-l-emerald-500";
          }

          return (
            <li
              key={index}
              className={`flex items-start gap-4 text-sm bg-slate-900/40 rounded-2xl p-4 border-l-4 ${borderClass} hover:bg-slate-800/40 transition-colors`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-2">
                  <span className={`inline-block px-2.5 py-1 text-[10px] uppercase font-bold tracking-wider rounded-md border ${badgeClass}`}>
                    {item.priority}
                  </span>
                </div>
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-400 hover:text-sky-300 hover:underline leading-relaxed block font-medium flex items-center gap-1"
                  >
                    {item.text}
                    <Icons.ArrowRight className="w-3 h-3" />
                  </a>
                ) : (
                  <span className="text-slate-300 leading-relaxed block font-normal">{item.text}</span>
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
