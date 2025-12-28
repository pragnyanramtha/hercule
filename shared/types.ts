export interface ActionItem {
  text: string;
  url?: string;
  priority: 'high' | 'medium' | 'low';
}

export interface AnalysisResult {
  score: number;
  summary: string;
  red_flags: string[];
  user_action_items: ActionItem[];
  timestamp: string;
  url: string;
}
