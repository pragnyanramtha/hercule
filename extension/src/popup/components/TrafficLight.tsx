interface TrafficLightProps {
  score: number;
}

type TrafficLightColor = 'green' | 'yellow' | 'red';

function TrafficLight({ score }: TrafficLightProps) {
  // Determine color based on score thresholds
  const getColor = (score: number): TrafficLightColor => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };

  const color = getColor(score);

  // Map color names to Tailwind classes
  const colorClasses: Record<TrafficLightColor, string> = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-400',
    red: 'bg-red-500'
  };

  const textColorClasses: Record<TrafficLightColor, string> = {
    green: 'text-green-700',
    yellow: 'text-yellow-700',
    red: 'text-red-700'
  };

  return (
    <div className="flex items-center gap-4">
      {/* Circular indicator */}
      <div 
        className={`w-16 h-16 rounded-full ${colorClasses[color]} shadow-lg flex items-center justify-center`}
        aria-label={`Privacy score: ${score} out of 100`}
      >
        <span className="text-white font-bold text-xl">{score}</span>
      </div>
      
      {/* Numerical score display */}
      <div className="flex flex-col">
        <span className={`text-3xl font-bold ${textColorClasses[color]}`}>
          {score}
        </span>
        <span className="text-sm text-gray-600">out of 100</span>
      </div>
    </div>
  );
}

export default TrafficLight;
