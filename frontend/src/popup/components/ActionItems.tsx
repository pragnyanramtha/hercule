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
      <ul className="space-y-4">
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
              className={`flex flex-col gap-3 text-sm bg-slate-900/40 rounded-2xl p-4 border-l-4 ${borderClass} hover:bg-slate-800/40 transition-colors`}
            >
              {/* Header with priority badge and text */}
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-2">
                  <span className={`inline-block px-2.5 py-1 text-[10px] uppercase font-bold tracking-wider rounded-md border ${badgeClass}`}>
                    {item.priority}
                  </span>
                </div>
                <span className="text-slate-200 leading-relaxed block font-medium">{item.text}</span>
              </div>

              {/* Action Links */}
              <div className="flex flex-wrap gap-2 mt-1">
                {/* View in Policy link */}
                {item.reference_url && (
                  <a
                    href={item.reference_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 hover:border-indigo-500/30 transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    View in Policy
                  </a>
                )}

                {/* Contact Company link */}
                {item.mailto_link && (
                  <a
                    href={item.mailto_link}
                    onClick={(e) => {
                      e.preventDefault();
                      // Open mailto link in a new tab - this triggers the default email client
                      window.open(item.mailto_link, '_blank');
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-violet-500/10 text-violet-300 border border-violet-500/20 hover:bg-violet-500/20 hover:border-violet-500/30 transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Contact Company
                  </a>
                )}

                {/* Legacy URL support */}
                {item.url && !item.reference_url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-sky-500/10 text-sky-300 border border-sky-500/20 hover:bg-sky-500/20 hover:border-sky-500/30 transition-all"
                  >
                    <Icons.ArrowRight className="w-3 h-3" />
                    Learn More
                  </a>
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

