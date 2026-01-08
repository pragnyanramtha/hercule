import { useState, useEffect } from 'react';
import { AnalysisResult } from '../../../shared/types';
import { config } from '../config';
import ErrorBoundary from './components/ErrorBoundary';
import TrafficLight from './components/TrafficLight';
import Summary from './components/Summary';
import RedFlags from './components/RedFlags';
import ActionItems from './components/ActionItems';
import { Icons } from './components/Icons';
import Settings, { useUserSettings } from './components/Settings';
import WaitingScreen from './components/WaitingScreen';

type LoadingPhase = 'idle' | 'discovering' | 'analyzing' | 'done' | 'error';

interface LoadingState {
  phase: LoadingPhase;
  message: string;
}

function AppContent() {
  const [loading, setLoading] = useState<LoadingState>({ phase: 'discovering', message: 'Finding privacy policy...' });
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Get user settings from storage
  const userSettings = useUserSettings();

  useEffect(() => {
    analyzeCurrentSite();
  }, []);

  const analyzeCurrentSite = async () => {
    try {
      setLoading({ phase: 'discovering', message: 'Finding privacy policy...' });
      setError(null);
      setResult(null);

      // Get current tab URL
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.url) {
        setError('Could not access current tab');
        setLoading({ phase: 'error', message: '' });
        return;
      }

      // Check for restricted pages
      if (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://') ||
        tab.url.startsWith('about:') || tab.url.startsWith('edge://')) {
        setError('Cannot analyze browser internal pages. Navigate to a website first.');
        setLoading({ phase: 'error', message: '' });
        return;
      }

      // Send URL to backend - it handles everything (discovery + analysis)
      setLoading({ phase: 'discovering', message: 'Searching for privacy policy...' });

      try {
        const response = await fetch(`${config.apiUrl}/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
          },
          body: JSON.stringify({
            policy_text: '',
            url: tab.url,
            user_name: userSettings.userName || '',
            user_groq_api_key: userSettings.groqApiKey || '',
          }),
          cache: 'no-store',
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Analysis failed (${response.status})`);
        }

        const analysisResult: AnalysisResult = await response.json();
        setResult(analysisResult);
        setLoading({ phase: 'done', message: '' });

      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Unknown error occurred');
        }
        setLoading({ phase: 'error', message: '' });
      }

    } catch (err) {
      console.error('Error:', err);
      setError('Could not analyze this site.');
      setLoading({ phase: 'error', message: '' });
    }
  };



  return (
    <div className="w-full min-h-screen bg-transparent selection:bg-indigo-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 glass-panel border-x-0 border-t-0 border-b border-slate-800/60 rounded-none px-6 py-4 flex items-center justify-between bg-slate-950/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="relative group">
            <div className="absolute inset-0 bg-indigo-500 blur-lg opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div className="relative w-8 h-8 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 border border-white/10 overflow-hidden bg-slate-900">
              <img src="/icons/logo.png" alt="Hercule Logo" className="w-full h-full object-cover" />
            </div>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-white via-indigo-100 to-indigo-200 bg-clip-text text-transparent tracking-tight">
            Hercule
          </h1>
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 hover:border-slate-600/50 transition-all text-slate-400 hover:text-indigo-400 group"
          title="Settings"
        >
          <Icons.Settings className="w-5 h-5 group-hover:rotate-90 transition-transform duration-500" />
        </button>
      </header>

      {/* Settings Modal */}
      <Settings isOpen={showSettings} onClose={() => setShowSettings(false)} />

      <main className="p-6">
        {/* Loading State */}
        {(loading.phase === 'discovering' || loading.phase === 'analyzing') && (
          <WaitingScreen />
        )}

        {/* Error State */}
        {error && loading.phase === 'error' && (
          <div className="bg-rose-950/20 border border-rose-500/20 p-8 rounded-3xl text-center backdrop-blur-sm animate-slide-up">
            <div className="inline-flex p-4 rounded-full bg-rose-500/10 mb-6 ring-1 ring-rose-500/20">
              <Icons.Alert className="w-8 h-8 text-rose-500" />
            </div>
            <h3 className="text-rose-200 font-semibold text-lg mb-2">Could Not Find Policy</h3>
            <p className="text-rose-200/70 text-sm mb-8 max-w-xs mx-auto leading-relaxed">{error}</p>
            <button
              onClick={analyzeCurrentSite}
              className="px-6 py-3 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white rounded-xl shadow-lg shadow-rose-900/40 transition-all active:scale-95 font-medium text-sm flex items-center justify-center gap-2 mx-auto w-full group"
            >
              <span className="text-lg group-hover:rotate-180 transition-transform duration-500">↻</span> Try Again
            </button>
          </div>
        )}

        {/* Results */}
        {result && loading.phase === 'done' && (
          <div className="space-y-6">
            <ErrorBoundary>
              <div className="bg-slate-900/40 border border-slate-800/60 rounded-[32px] p-8 flex flex-col items-center backdrop-blur-sm shadow-2xl shadow-indigo-500/5 animate-slide-up">
                <TrafficLight score={result.score} />
              </div>
            </ErrorBoundary>

            <div className="grid gap-5">
              <ErrorBoundary>
                <div className="animate-slide-up delay-150">
                  <Summary summary={result.summary} />
                </div>
              </ErrorBoundary>
              <ErrorBoundary>
                <div className="animate-slide-up delay-300">
                  <RedFlags redFlags={result.red_flags} />
                </div>
              </ErrorBoundary>
              <ErrorBoundary>
                <div className="animate-slide-up delay-500">
                  <ActionItems actionItems={result.user_action_items} />
                </div>
              </ErrorBoundary>
            </div>

            <footer className="flex items-center justify-center gap-2 pt-8 pb-4 opacity-0 animate-slide-up delay-500" style={{ animationFillMode: 'forwards' }}>
              <div className="w-1 h-1 rounded-full bg-slate-500"></div>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Protected by Hercule Engine</p>
            </footer>
          </div>
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
