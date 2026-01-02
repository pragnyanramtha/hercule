import { Icons } from './Icons';

interface TrafficLightProps {
  score: number;
}

type TrafficLightColor = 'emerald' | 'amber' | 'rose';

function TrafficLight({ score }: TrafficLightProps) {
  const getColor = (score: number): TrafficLightColor => {
    if (score >= 80) return 'emerald';
    if (score >= 50) return 'amber';
    return 'rose';
  };

  const color = getColor(score);

  const colors = {
    emerald: { text: 'text-emerald-400', stroke: 'stroke-emerald-500', glow: 'shadow-emerald-500/30' },
    amber: { text: 'text-amber-400', stroke: 'stroke-amber-500', glow: 'shadow-amber-500/30' },
    rose: { text: 'text-rose-400', stroke: 'stroke-rose-500', glow: 'shadow-rose-500/30' }
  };

  const theme = colors[color];
  const radius = 58;
  const stroke = 8;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={`flex flex-col items-center justify-center py-6`}>
      <div className="relative flex items-center justify-center">
        {/* Glow Container */}
        <div className={`absolute inset-0 rounded-full blur-3xl opacity-20 bg-current transition-colors duration-700 ${theme.text}`}></div>

        {/* SVG Gauge */}
        <svg
          height={radius * 2}
          width={radius * 2}
          className="transform -rotate-90 drop-shadow-xl"
        >
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="currentColor" className="text-slate-700" stopOpacity="0.2" />
              <stop offset="100%" stopColor="currentColor" className={theme.text} />
            </linearGradient>
          </defs>
          <circle
            stroke="currentColor"
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={circumference + ' ' + circumference}
            style={{ strokeDashoffset: 0 }}
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            className="text-slate-800/50"
          />
          <circle
            stroke="currentColor"
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={circumference + ' ' + circumference}
            style={{ strokeDashoffset }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={radius}
            cy={radius}
            className={`${theme.text} transition-all duration-1000 ease-out`}
          />
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-5xl font-bold tracking-tighter transition-colors duration-500 ${theme.text}`}>
            {score}
          </span>
          <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold mt-1">
            Score
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900/50 border border-slate-800 backdrop-blur-md">
        <Icons.Shield className={`w-3 h-3 ${theme.text}`} />
        <span className="text-xs font-medium text-slate-300">
          {score >= 80 ? 'Excellent Protection' : score >= 50 ? 'Moderate Risks' : 'High Risk Profile'}
        </span>
      </div>
    </div>
  );
}

export default TrafficLight;
