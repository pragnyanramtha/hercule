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
    <div className="w-full h-full p-4 bg-gray-50">
      <h1 className="text-2xl font-bold text-blue-600 mb-4">Privacy Policy Analyzer</h1>

      {loading.isLoading && (
        <div className="flex flex-col items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">{loading.message}</p>
          <div className="flex gap-2 mt-3 text-xs text-gray-400">
            <span className={componentLoading.extraction ? 'text-blue-500' : 'text-green-500'}>
              {componentLoading.extraction ? '○' : '✓'} Extract
            </span>
            <span className={componentLoading.analysis ? 'text-blue-500' : (result ? 'text-green-500' : 'text-gray-400')}>
              {componentLoading.analysis ? '○' : (result ? '✓' : '○')} Analyze
            </span>
          </div>
        </div>
      )}

      {error && !loading.isLoading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">Error</p>
          <p className="text-red-600 text-sm mt-1">{error}</p>
          <button
            onClick={analyzePolicyFromCurrentPage}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {result && !loading.isLoading && (
        <div className="space-y-4">
          <ErrorBoundary>
            <div className="bg-white rounded-lg p-6 shadow">
              <TrafficLight score={result.score} />
            </div>
          </ErrorBoundary>
          <ErrorBoundary><Summary summary={result.summary} /></ErrorBoundary>
          <ErrorBoundary><RedFlags redFlags={result.red_flags} /></ErrorBoundary>
          <ErrorBoundary><ActionItems actionItems={result.user_action_items} /></ErrorBoundary>
        </div>
      )}
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
