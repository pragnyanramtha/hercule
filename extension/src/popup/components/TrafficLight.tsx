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
    emerald: { text: 'text-emerald-400', stroke: 'stroke-emerald-500', glow: 'shadow-emerald-500/20' },
    amber: { text: 'text-amber-400', stroke: 'stroke-amber-500', glow: 'shadow-amber-500/20' },
    rose: { text: 'text-rose-400', stroke: 'stroke-rose-500', glow: 'shadow-rose-500/20' }
  };

  const theme = colors[color];
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className={`flex flex-col items-center justify-center p-6 ${theme.text}`}>
      <div className="relative w-40 h-40 flex items-center justify-center">
        {/* Glow effect */}
        <div className={`absolute inset-0 rounded-full blur-xl opacity-20 bg-current`}></div>
        
        <svg className="w-full h-full transform -rotate-90 drop-shadow-lg" viewBox="0 0 120 120">
          {/* Background circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            className="stroke-slate-800"
            strokeWidth="8"
          />
          {/* Progress circle */}
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            className={`${theme.stroke} transition-all duration-1000 ease-out`}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-bold tracking-tighter text-white">
            {score}
          </span>
          <span className="text-xs uppercase tracking-widest text-slate-400 mt-1 font-medium">
            Score
          </span>
        </div>
      </div>
    </div>
  );
}

export default TrafficLight;
