import { useState, useEffect } from 'react';
import { AnalysisResult } from '../../../shared/types';
import { config } from '../config';
import ErrorBoundary from './components/ErrorBoundary';
import TrafficLight from './components/TrafficLight';
import Summary from './components/Summary';
import RedFlags from './components/RedFlags';
import ActionItems from './components/ActionItems';

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
        setError('Cannot analyze browser internal pages. Please navigate to a website.');
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
          // Wait a moment for the script to initialize
          await new Promise(resolve => setTimeout(resolve, 100));
          // Retry the message
          response = await chrome.tabs.sendMessage(tab.id, {
            action: 'extractCurrentPage'
          });
        } catch (injectError) {
          console.error('Failed to inject content script:', injectError);
          setError('Cannot access this page. Try refreshing the page or check if the site allows extensions.');
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

      setLoading({ isLoading: true, message: 'Analyzing policy...' });
      await analyzePolicy(response.policyText, response.policyUrl || '');

    } catch (err) {
      console.error('Error in analyzePolicyFromCurrentPage:', err);
      setError('Could not analyze policy. Make sure you are on a valid page.');
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

      // Retry logic
      if (retryCount < config.maxRetries && err instanceof Error && err.name !== 'AbortError') {
        console.log(`Retrying... attempt ${retryCount + 1}`);
        await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
        return analyzePolicy(policyText, url, retryCount + 1);
      }

      const errorMessage = err instanceof Error
        ? (err.name === 'AbortError' ? 'Request timed out' : err.message)
        : 'Unknown error occurred';

      setError(`Could not analyze policy: ${errorMessage}`);
      setLoading({ isLoading: false, message: '' });
      setComponentLoading({ extraction: false, analysis: false });
    }
  };

  return (
    <div className="w-full min-h-screen bg-slate-950 text-slate-200 selection:bg-blue-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 glass-panel border-x-0 border-t-0 rounded-none px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            PrivacyGuard
          </h1>
        </div>
        <div className="text-xs font-mono text-slate-500">v1.0</div>
      </header>

      <main className="p-6">
        {loading.isLoading && (
          <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
            <div className="relative mb-8">
              <div className="absolute inset-0 rounded-full blur-xl bg-indigo-500/20 animate-pulse"></div>
              <div className="w-16 h-16 border-4 border-slate-800 border-t-indigo-500 rounded-full animate-spin"></div>
            </div>

            <p className="text-slate-300 font-medium text-lg mb-2">{loading.message}</p>

            <div className="flex items-center gap-6 mt-6">
              <div className={`flex items-center gap-2 transition-colors duration-300 ${componentLoading.extraction ? 'text-indigo-400' : 'text-emerald-400'}`}>
                <div className={`w-2 h-2 rounded-full ${componentLoading.extraction ? 'bg-indigo-400 animate-ping' : 'bg-emerald-400'}`}></div>
                <span className="text-xs font-medium uppercase tracking-wider">Extraction</span>
              </div>
              <div className="w-8 h-0.5 bg-slate-800 rounded-full"></div>
              <div className={`flex items-center gap-2 transition-colors duration-300 ${componentLoading.analysis ? 'text-indigo-400' : (result ? 'text-emerald-400' : 'text-slate-600')}`}>
                <div className={`w-2 h-2 rounded-full ${componentLoading.analysis ? 'bg-indigo-400 animate-ping' : (result ? 'bg-emerald-400' : 'bg-slate-600')}`}></div>
                <span className="text-xs font-medium uppercase tracking-wider">Analysis</span>
              </div>
            </div>
          </div>
        )}

        {error && !loading.isLoading && (
          <div className="glass-panel bg-rose-950/20 border-rose-500/20 p-6 rounded-xl text-center">
            <div className="inline-flex p-3 rounded-full bg-rose-500/10 mb-4">
              <span className="text-3xl">⚠️</span>
            </div>
            <p className="text-rose-200 font-medium text-lg mb-2">Analysis Failed</p>
            <p className="text-rose-200/60 text-sm mb-6 max-w-xs mx-auto">{error}</p>
            <button
              onClick={analyzePolicyFromCurrentPage}
              className="px-6 py-2.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg shadow-lg shadow-rose-900/20 transition-all active:scale-95 font-medium text-sm"
            >
              Try Again
            </button>
          </div>
        )}

        {result && !loading.isLoading && (
          <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-700">
            <ErrorBoundary>
              <div className="glass-panel p-8 rounded-2xl flex flex-col items-center">
                <TrafficLight score={result.score} />
              </div>
            </ErrorBoundary>

            <div className="grid gap-6">
              <ErrorBoundary><Summary summary={result.summary} /></ErrorBoundary>
              <ErrorBoundary><RedFlags redFlags={result.red_flags} /></ErrorBoundary>
              <ErrorBoundary><ActionItems actionItems={result.user_action_items} /></ErrorBoundary>
            </div>

            <footer className="text-center pt-8 pb-4 text-xs text-slate-600">
              <p>Powered by Gemini & Hercule Engine</p>
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
