import { useState, useEffect } from 'react';
import { AnalysisResult } from '../../../shared/types';
import TrafficLight from './components/TrafficLight';
import Summary from './components/Summary';
import RedFlags from './components/RedFlags';
import ActionItems from './components/ActionItems';

interface LoadingState {
  isLoading: boolean;
  message: string;
}

function App() {
  const [loading, setLoading] = useState<LoadingState>({ isLoading: true, message: 'Extracting policy text...' });
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // On mount, request policy text from content script
    analyzePolicyFromCurrentPage();
  }, []);

  const analyzePolicyFromCurrentPage = async () => {
    try {
      setLoading({ isLoading: true, message: 'Extracting policy text...' });
      setError(null);

      // Get the active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      if (!tab.id) {
        setError('Could not access current tab');
        setLoading({ isLoading: false, message: '' });
        return;
      }

      // Request policy text from content script
      const response = await chrome.tabs.sendMessage(tab.id, { 
        action: 'extractCurrentPage' 
      });

      if (!response.success) {
        setError(response.error || 'Failed to extract policy text');
        setLoading({ isLoading: false, message: '' });
        return;
      }

      // POST policy text to backend
      setLoading({ isLoading: true, message: 'Analyzing policy...' });
      await analyzePolicy(response.policyText, response.policyUrl || '');

    } catch (err) {
      console.error('Error in analyzePolicyFromCurrentPage:', err);
      setError('Could not analyze policy. Check backend is running.');
      setLoading({ isLoading: false, message: '' });
    }
  };

  const analyzePolicy = async (policyText: string, url: string) => {
    try {
      // POST to backend API
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          policy_text: policyText,
          url: url
        })
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      // Parse and store result
      const analysisResult: AnalysisResult = await response.json();
      setResult(analysisResult);
      setLoading({ isLoading: false, message: '' });

    } catch (err) {
      console.error('Error calling backend:', err);
      setError('Could not analyze policy. Check backend is running.');
      setLoading({ isLoading: false, message: '' });
    }
  };

  return (
    <div className="w-full h-full p-4 bg-gray-50">
      <h1 className="text-2xl font-bold text-blue-600 mb-4">
        Privacy Policy Analyzer
      </h1>

      {/* Loading State */}
      {loading.isLoading && (
        <div className="flex flex-col items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">{loading.message}</p>
        </div>
      )}

      {/* Error State */}
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

      {/* Success State - Display Result */}
      {result && !loading.isLoading && (
        <div className="space-y-4">
          {/* Traffic Light Score */}
          <div className="bg-white rounded-lg p-6 shadow">
            <TrafficLight score={result.score} />
          </div>

          {/* Summary Section */}
          <Summary summary={result.summary} />

          {/* Red Flags Section */}
          <RedFlags redFlags={result.red_flags} />

          {/* Action Items Section */}
          <ActionItems actionItems={result.user_action_items} />
        </div>
      )}
    </div>
  );
}

export default App;
