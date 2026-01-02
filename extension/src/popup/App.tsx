import { useState, useEffect } from 'react';
import { AnalysisResult } from '../../../shared/types';
import { config } from '../config';
import ErrorBoundary from './components/ErrorBoundary';
import TrafficLight from './components/TrafficLight';
import Summary from './components/Summary';
import RedFlags from './components/RedFlags';
import ActionItems from './components/ActionItems';
import { Icons } from './components/Icons';

interface LoadingState {
  isLoading: boolean;
  message: string;
}

interface ComponentLoadingState {
  extraction: boolean;
  analysis: boolean;
}

function AppContent() {
  const [loading, setLoading] = useState<LoadingState>({ isLoading: true, message: 'Extracting policy text...' });
  const [componentLoading, setComponentLoading] = useState<ComponentLoadingState>({ extraction: true, analysis: false });
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyzePolicyFromCurrentPage();
  }, []);

  const analyzePolicyFromCurrentPage = async () => {
    try {
      setLoading({ isLoading: true, message: 'Extracting policy text...' });
      setComponentLoading({ extraction: true, analysis: false });
      setError(null);

      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab.id) {
        setError('Could not access current tab');
        setLoading({ isLoading: false, message: '' });
        return;
      }

      // Check if this is a restricted page
      if (tab.url?.startsWith('chrome://') || tab.url?.startsWith('chrome-extension://') ||
        tab.url?.startsWith('about:') || tab.url?.startsWith('edge://')) {
        setError('Cannot analyze browser extension or internal pages. Please navigate to a standard website.');
        setLoading({ isLoading: false, message: '' });
        return;
      }

      let response;
      try {
        response = await chrome.tabs.sendMessage(tab.id, {
          action: 'extractCurrentPage'
        });
      } catch (connectionError) {
        // Content script not loaded - inject it programmatically
        console.log('Content script not found, injecting...');
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content/content.js']
          });
          await new Promise(resolve => setTimeout(resolve, 100));
          response = await chrome.tabs.sendMessage(tab.id, {
            action: 'extractCurrentPage'
          });
        } catch (injectError) {
          console.error('Failed to inject content script:', injectError);
          setError('Cannot access this page. Try refreshing the page.');
          setLoading({ isLoading: false, message: '' });
          return;
        }
      }

      setComponentLoading({ extraction: false, analysis: true });

      if (!response.success) {
        setError(response.error || 'Failed to extract policy text');
        setLoading({ isLoading: false, message: '' });
        return;
      }

      setLoading({ isLoading: true, message: 'Analyzing privacy risks (this may take a moment)...' });
      await analyzePolicy(response.policyText, response.policyUrl || '');

    } catch (err) {
      console.error('Error in analyzePolicyFromCurrentPage:', err);
      setError('Could not analyze policy. Connection failed.');
      setLoading({ isLoading: false, message: '' });
    }
  };

  const analyzePolicy = async (policyText: string, url: string, retryCount = 0) => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config.requestTimeout);

      const response = await fetch(`${config.apiUrl}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ policy_text: policyText, url }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Backend returned ${response.status}`);
      }

      const analysisResult: AnalysisResult = await response.json();
      setResult(analysisResult);
      setLoading({ isLoading: false, message: '' });
      setComponentLoading({ extraction: false, analysis: false });

    } catch (err) {
      console.error('Error calling backend:', err);

      if (retryCount < config.maxRetries && err instanceof Error && err.name !== 'AbortError') {
        console.log(`Retrying... attempt ${retryCount + 1}`);
        await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
        return analyzePolicy(policyText, url, retryCount + 1);
      }

      const errorMessage = err instanceof Error
        ? (err.name === 'AbortError' ? 'Analysis timed out' : err.message)
        : 'Unknown error';

      setError(errorMessage);
      setLoading({ isLoading: false, message: '' });
      setComponentLoading({ extraction: false, analysis: false });
    }
  };

  return (
    <div className="w-full min-h-screen bg-transparent selection:bg-indigo-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 glass-panel border-x-0 border-t-0 border-b border-slate-800/60 rounded-none px-6 py-4 flex items-center justify-between bg-slate-950/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="relative group">
            <div className="absolute inset-0 bg-indigo-500 blur-lg opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div className="relative w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 border border-white/10">
              <Icons.Shield className="w-5 h-5 text-white" />
            </div>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-white via-indigo-100 to-indigo-200 bg-clip-text text-transparent tracking-tight">
            PrivacyGuard
          </h1>
        </div>
        <div className="px-2 py-0.5 rounded-full bg-slate-800/50 border border-slate-700/50">
          <span className="text-[10px] font-mono text-slate-400 font-medium">v1.1</span>
        </div>
      </header>

      <main className="p-6">
        {loading.isLoading && (
          <div className="flex flex-col items-center justify-center py-20 animate-fade-in-scale">
            <div className="relative mb-10">
              <div className={`absolute inset-0 rounded-full blur-2xl transition-colors duration-1000 ${componentLoading.analysis ? 'bg-emerald-500/20' : 'bg-indigo-500/20'} animate-pulse`}></div>
              <div className="w-16 h-16 relative">
                <div className="absolute inset-0 border-4 border-slate-800/50 rounded-full"></div>
                <div className={`absolute inset-0 border-4 border-t-current border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin transition-colors duration-1000 ${componentLoading.analysis ? 'text-emerald-400' : 'text-indigo-500'}`}></div>
              </div>
            </div>

            <p key={loading.message} className="text-slate-200 font-medium text-base mb-2 animate-fade-in-scale h-6">
              {loading.message}
            </p>

            <div className="flex items-center gap-4 mt-8 w-full max-w-[200px]">
              <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                <div className={`h-full transition-all duration-1000 ease-out ${componentLoading.analysis ? 'bg-emerald-400 w-full' : 'bg-indigo-500 w-1/2'}`}></div>
              </div>
            </div>
            <div className="flex justify-between w-full max-w-[200px] mt-2 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
              <span className={`transition-colors duration-500 ${!componentLoading.analysis ? 'text-indigo-400' : 'text-slate-600'}`}>Extract</span>
              <span className={`transition-colors duration-500 ${componentLoading.analysis ? 'text-emerald-400' : 'text-slate-600'}`}>Analyze</span>
            </div>
          </div>
        )}

        {error && !loading.isLoading && (
          <div className="bg-rose-950/20 border border-rose-500/20 p-8 rounded-3xl text-center backdrop-blur-sm animate-slide-up">
            <div className="inline-flex p-4 rounded-full bg-rose-500/10 mb-6 ring-1 ring-rose-500/20">
              <Icons.Alert className="w-8 h-8 text-rose-500" />
            </div>
            <h3 className="text-rose-200 font-semibold text-lg mb-2">Analysis Failed</h3>
            <p className="text-rose-200/70 text-sm mb-8 max-w-xs mx-auto leading-relaxed">{error}</p>
            <button
              onClick={analyzePolicyFromCurrentPage}
              className="px-6 py-3 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white rounded-xl shadow-lg shadow-rose-900/40 transition-all active:scale-95 font-medium text-sm flex items-center justify-center gap-2 mx-auto w-full group"
            >
              <span className="text-lg group-hover:rotate-180 transition-transform duration-500">↻</span> Retry Analysis
            </button>
          </div>
        )}

        {result && !loading.isLoading && (
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
