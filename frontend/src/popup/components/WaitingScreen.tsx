import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Icons } from './Icons';

const PHASES = [
    {
        id: 'search',
        icon: Icons.Search,
        color: 'text-indigo-400',
        bg: 'bg-indigo-500/20',
        messages: [
            "Searching for privacy policy...",
            "Checking footer links...",
            "Waking up the servers... ☕",
            "Looking for legal documents...",
            "Please wait, this may take a moment...",
            "Swiping right on privacy policies... 💕",
            "Teaching robots to read legalese...",
            "Finding the fine print so you don't have to 🔍",
            "On a first date with their privacy page...",
            "Asking politely for their privacy terms..."
        ]
    },
    {
        id: 'analyze',
        icon: Icons.Scan,
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/20',
        messages: [
            "Found policy text!",
            "Analyzing legal jargon...",
            "High demand right now, hang tight! 🚀",
            "Checking for red flags...",
            "Our AI is reading the fine print...",
            "Translating lawyer-speak to human... 🤖",
            "Spotting the sneaky bits they hoped you'd miss...",
            "Reading 50 pages so you can read 5 lines ✨",
            "This policy is longer than my dating profile...",
            "Dissecting corporate promises like a pro 🔬",
            "Finding out if they really \"value your privacy\" 😏"
        ]
    },
    {
        id: 'summarize',
        icon: Icons.Sparkles,
        color: 'text-purple-400',
        bg: 'bg-purple-500/20',
        messages: [
            "Generating summary...",
            "Thanks for your patience! 🙏",
            "Finalizing report...",
            "Almost there, just a few more seconds...",
            "Making your privacy easier to understand...",
            "Wrapping up your privacy report with a bow 🎀",
            "You're worth the wait, and so is this report 💜",
            "Putting the finishing touches on your insights...",
            "Your privacy guardian is almost ready! 🛡️",
            "Preparing to blow your mind with clarity ✨",
            "One sec, making this look pretty for you..."
        ]
    }
];

export default function WaitingScreen() {
    const [progress, setProgress] = useState(0);
    const [phaseIndex, setPhaseIndex] = useState(0);
    const [messageIndex, setMessageIndex] = useState(0);

    useEffect(() => {
        const duration = 60000; // 60 seconds
        const interval = 100; // Update every 100ms
        const steps = duration / interval;
        const increment = 100 / steps;

        const timer = setInterval(() => {
            setProgress(prev => {
                if (prev >= 100) {
                    clearInterval(timer);
                    return 100;
                }
                return prev + increment;
            });
        }, interval);

        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        // Update phase based on progress
        if (progress < 33) setPhaseIndex(0);
        else if (progress < 66) setPhaseIndex(1);
        else setPhaseIndex(2);
    }, [progress]);

    useEffect(() => {
        // Rotate messages every 3 seconds
        const messageTimer = setInterval(() => {
            setMessageIndex(prev => (prev + 1) % PHASES[phaseIndex].messages.length);
        }, 3000);

        return () => clearInterval(messageTimer);
    }, [phaseIndex]);

    const currentPhase = PHASES[phaseIndex];
    const CurrentIcon = currentPhase.icon;

    return (
        <div className="flex flex-col items-center justify-center py-20 w-full">
            <div className="relative mb-12">
                {/* Background glow */}
                <motion.div
                    animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.3, 0.6, 0.3],
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                    className={`absolute inset-0 rounded-full blur-3xl ${currentPhase.bg}`}
                />

                {/* Icon container */}
                <div className="relative w-24 h-24 flex items-center justify-center">
                    <motion.div
                        key={currentPhase.id}
                        initial={{ scale: 0, rotate: -180 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0, rotate: 180 }}
                        transition={{ type: "spring", stiffness: 260, damping: 20 }}
                        className={`relative z-10 p-6 rounded-2xl bg-slate-900/80 border border-white/10 backdrop-blur-xl shadow-2xl ${currentPhase.color}`}
                    >
                        <CurrentIcon className="w-10 h-10" />
                    </motion.div>

                    {/* Orbiting particles */}
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                        className="absolute inset-[-10px] border border-dashed border-slate-700/50 rounded-full"
                    />
                    <motion.div
                        animate={{ rotate: -360 }}
                        transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
                        className="absolute inset-[-20px] border border-dashed border-slate-800/50 rounded-full opacity-50"
                    />
                </div>
            </div>

            {/* Text Content */}
            <div className="h-20 flex flex-col items-center justify-center text-center px-4">
                <AnimatePresence mode="wait">
                    <motion.p
                        key={currentPhase.messages[messageIndex]}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-slate-200 font-medium text-lg mb-2"
                    >
                        {currentPhase.messages[messageIndex]}
                    </motion.p>
                </AnimatePresence>

                <motion.p
                    key={currentPhase.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-slate-500 text-sm"
                >
                    {phaseIndex === 0 && "Phase 1: Discovery"}
                    {phaseIndex === 1 && "Phase 2: Analysis"}
                    {phaseIndex === 2 && "Phase 3: Synthesis"}
                </motion.p>
            </div>

            {/* Progress Bar */}
            <div className="w-64 mt-8">
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500"
                        style={{ width: `${progress}%` }}
                        transition={{ ease: "linear" }}
                    />
                </div>
                <div className="flex justify-between mt-2 text-[10px] uppercase tracking-wider font-bold text-slate-600">
                    <span className={progress > 0 ? "text-indigo-400" : ""}>Search</span>
                    <span className={progress > 33 ? "text-emerald-400" : ""}>Analyze</span>
                    <span className={progress > 66 ? "text-purple-400" : ""}>Report</span>
                </div>
            </div>
        </div>
    );
}
