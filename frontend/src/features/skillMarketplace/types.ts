export interface Skill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  origin: string;
  version: number;
  enabled: boolean;
  published: boolean;
  publisher: string;
  repo_url?: string;
  hash_sha?: string;
  trust_score: number;
  quality_score: number;

  // Execution stats
  execution_count: number;   // raw from backend
  success_count: number;     // raw from backend
  latency_ms_avg: number;    // raw from backend
  user_rating: number;       // raw from backend (0–5)
  rating_count: number;

  // Derived / aliased (for new components)
  usage_count: number;       // = execution_count
  success_rate: number;      // = success_count / max(execution_count, 1)
  avg_latency_ms: number;    // = latency_ms_avg
  avg_rating: number;        // = user_rating

  // Extended fields
  code?: string;             // source code (not always returned)
  icon?: string;             // emoji or short string
  trigger_patterns?: string[];
  tags: string[];
  triggers: string[];
  dependencies: string[];
  previous_version_id?: string;
  installed_at?: number;
  created_at: number;
  updated_at: number;
}

export interface SkillStats {
  total_skills: number;
  enabled_skills: number;
  total_executions: number;
  avg_trust_score: number;
  categories: Record<string, number>;
}

export interface SkillsResponse {
  skills: Skill[];
  total: number;
}

export interface SearchResponse extends SkillsResponse {
  query: string;
  tags: string[];
}
