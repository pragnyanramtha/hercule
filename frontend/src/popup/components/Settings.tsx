import { useState, useEffect } from 'react';
import { Icons } from './Icons';

interface SettingsProps {
    isOpen: boolean;
    onClose: () => void;
}

interface UserSettings {
    userName: string;
    groqApiKey: string;
}

const STORAGE_KEY = 'hercule_user_settings';

export function Settings({ isOpen, onClose }: SettingsProps) {
    const [userName, setUserName] = useState('');
    const [groqApiKey, setGroqApiKey] = useState('');
    const [showApiKey, setShowApiKey] = useState(false);
    const [saved, setSaved] = useState(false);

    // Load settings on mount
    useEffect(() => {
        chrome.storage.local.get([STORAGE_KEY], (result) => {
            if (result[STORAGE_KEY]) {
                const settings: UserSettings = result[STORAGE_KEY];
                setUserName(settings.userName || '');
                setGroqApiKey(settings.groqApiKey || '');
            }
        });
    }, []);

    const handleSave = () => {
        const settings: UserSettings = {
            userName: userName.trim(),
            groqApiKey: groqApiKey.trim(),
        };

        chrome.storage.local.set({ [STORAGE_KEY]: settings }, () => {
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        });
    };

    const handleClear = () => {
        setUserName('');
        setGroqApiKey('');
        chrome.storage.local.remove([STORAGE_KEY]);
        setSaved(false);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="bg-slate-900 border border-slate-700/60 rounded-3xl w-[340px] max-h-[90vh] overflow-hidden shadow-2xl animate-slide-up">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/60">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-indigo-500/20 border border-indigo-500/30">
                            <Icons.Settings className="w-5 h-5 text-indigo-400" />
                        </div>
                        <h2 className="text-lg font-semibold text-white">Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-xl hover:bg-slate-800 transition-colors text-slate-400 hover:text-white"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-5">
                    {/* User Name */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-slate-300">
                            Your Name
                        </label>
                        <input
                            type="text"
                            value={userName}
                            onChange={(e) => setUserName(e.target.value)}
                            placeholder="John Doe"
                            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
                        />
                        <p className="text-xs text-slate-500">
                            Used to personalize email templates when contacting companies.
                        </p>
                    </div>

                    {/* Groq API Key */}
                    <div className="space-y-2">
                        <label className="block text-sm font-medium text-slate-300">
                            Groq API Key <span className="text-slate-500">(Optional)</span>
                        </label>
                        <div className="relative">
                            <input
                                type={showApiKey ? 'text' : 'password'}
                                value={groqApiKey}
                                onChange={(e) => setGroqApiKey(e.target.value)}
                                placeholder="gsk_..."
                                className="w-full px-4 py-3 pr-12 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all font-mono text-sm"
                            />
                            <button
                                type="button"
                                onClick={() => setShowApiKey(!showApiKey)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition-colors"
                            >
                                {showApiKey ? (
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                )}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500">
                            Provide your own API key from{' '}
                            <a
                                href="https://console.groq.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-indigo-400 hover:text-indigo-300 underline"
                            >
                                console.groq.com
                            </a>
                            {' '}for faster analysis.
                        </p>
                    </div>

                    {/* Info Box */}
                    <div className="p-4 bg-slate-800/30 border border-slate-700/30 rounded-xl">
                        <div className="flex items-start gap-3">
                            <div className="p-1.5 rounded-lg bg-indigo-500/20">
                                <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <div className="text-xs text-slate-400 leading-relaxed">
                                <p className="font-medium text-slate-300 mb-1">Why provide an API key?</p>
                                <p>Using your own key ensures faster responses and helps avoid rate limits during peak usage.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center gap-3 px-6 py-4 border-t border-slate-800/60 bg-slate-900/50">
                    <button
                        onClick={handleClear}
                        className="flex-1 px-4 py-2.5 bg-slate-800/50 border border-slate-700/50 text-slate-300 rounded-xl hover:bg-slate-700/50 hover:text-white transition-all text-sm font-medium"
                    >
                        Clear
                    </button>
                    <button
                        onClick={handleSave}
                        className="flex-1 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white rounded-xl shadow-lg shadow-indigo-900/30 transition-all text-sm font-medium flex items-center justify-center gap-2"
                    >
                        {saved ? (
                            <>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Saved!
                            </>
                        ) : (
                            'Save Settings'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Helper hook to get settings from storage
export function useUserSettings(): UserSettings {
    const [settings, setSettings] = useState<UserSettings>({
        userName: '',
        groqApiKey: '',
    });

    useEffect(() => {
        chrome.storage.local.get([STORAGE_KEY], (result) => {
            if (result[STORAGE_KEY]) {
                setSettings(result[STORAGE_KEY]);
            }
        });

        // Listen for changes
        const listener = (changes: { [key: string]: chrome.storage.StorageChange }) => {
            if (changes[STORAGE_KEY]) {
                setSettings(changes[STORAGE_KEY].newValue || { userName: '', groqApiKey: '' });
            }
        };

        chrome.storage.onChanged.addListener(listener);
        return () => chrome.storage.onChanged.removeListener(listener);
    }, []);

    return settings;
}

export default Settings;
