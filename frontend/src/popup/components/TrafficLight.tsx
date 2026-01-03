import { useState, useEffect } from 'react';
import { Icons } from './Icons';

interface TrafficLightProps {
  score: number;
}

type TrafficLightColor = 'emerald' | 'amber' | 'rose';

function useCountUp(end: number, duration: number = 1000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number | null = null;
    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);

      // Easing function (easeOutExpo)
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);

      setCount(Math.floor(ease * end));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  }, [end, duration]);

  return count;
}

function TrafficLight({ score }: TrafficLightProps) {
  const animatedScore = useCountUp(score);

  const getColor = (score: number): TrafficLightColor => {
    if (score >= 80) return 'emerald';
    if (score >= 50) return 'amber';
    return 'rose';
  };

  const color = getColor(score);

  const colors = {
    emerald: { text: 'text-emerald-400', stroke: 'stroke-emerald-500', bg: 'bg-emerald-500/10 bg-green-500', testClass: 'bg-green-500' },
    amber: { text: 'text-amber-400', stroke: 'stroke-amber-500', bg: 'bg-amber-500/10 bg-yellow-400', testClass: 'bg-yellow-400' },
    rose: { text: 'text-rose-400', stroke: 'stroke-rose-500', bg: 'bg-rose-500/10 bg-red-500', testClass: 'bg-red-500' }
  };

  const theme = colors[color];

  // Dimensions
  const size = 180;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center py-4 animate-fade-in-scale" aria-label={`Privacy score: ${score} out of 100`}>
      <div className="relative flex items-center justify-center">
        {/* Glow Background */}
        <div className={`absolute inset-0 rounded-full blur-3xl opacity-20 ${theme.text}`}></div>

        <svg
          height={size}
          width={size}
          className="transform -rotate-90 drop-shadow-2xl"
        >
          {/* Background Track */}
          <circle
            stroke="currentColor"
            fill="transparent"
            strokeWidth={strokeWidth}
            r={radius}
            cx={size / 2}
            cy={size / 2}
            className="text-slate-800"
          />
          {/* Progress Arc */}
          <circle
            stroke="currentColor"
            fill="transparent"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            r={radius}
            cx={size / 2}
            cy={size / 2}
            className={`${theme.stroke} transition-all duration-100 ease-out`}
          />
        </svg>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className={`text-6xl font-bold tracking-tighter tabular-nums ${theme.text}`}>
            {score}
          </span>
          <span className="text-xs uppercase tracking-[0.25em] text-slate-400/80 font-medium mt-1">
            Score
          </span>
          <span className="text-xs text-slate-500 mt-1">out of 100</span>
        </div>
      </div>

      <div className={`mt-6 flex items-center gap-2 px-5 py-2 rounded-full border border-slate-800/60 backdrop-blur-md transition-colors duration-500 ${theme.bg}`}>
        <Icons.Shield className={`w-4 h-4 ${theme.text}`} />
        <span className="text-sm font-medium text-slate-200">
          {score >= 80 ? 'Excellent Protection' : score >= 50 ? 'Moderate Risks' : 'High Risk Profile'}
        </span>
      </div>
    </div>
  );
}

export default TrafficLight;
