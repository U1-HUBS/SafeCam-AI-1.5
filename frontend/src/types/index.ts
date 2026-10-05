export interface Camera {
  id: number;
  name: string;
  location: string;
  stream_url: string;
  is_simulation: boolean;
  loop_simulation: boolean;
  enabled: boolean;
  ai_enabled: boolean;
  sampling_rate: number;
  sensitivity: number;
  pre_buffer_seconds: number;
  post_buffer_seconds: number;
  status: string;
  runtime_status?: string;
  last_seen_at?: string;
  latest_prediction?: {
    label: string;
    category: string;
    confidence: number;
    is_violent: boolean;
    timestamp: number;
    latency_ms: number;
  };
}

export interface IncidentReview {
  id: number;
  incident_id: number;
  reviewer: string;
  classification: "Confirmed Violence" | "False Positive / Not Violence" | "Needs Review";
  reason?: string;
  notes?: string;
  reviewed_at: string;
}

export interface IncidentEvent {
  id: number;
  incident_id: number;
  event_type: string;
  event_at: string;
  actor: string;
  metadata_json?: string;
}

export interface Incident {
  id: number;
  public_id: string;
  camera_id: number;
  camera_name?: string;
  camera_location?: string;
  category: string;
  raw_ai_label?: string;
  severity: "Critical" | "High" | "Medium" | "Low";
  peak_confidence: number;
  average_confidence: number;
  started_at: string;
  detected_at: string;
  ended_at?: string;
  status: "AWAITING_REVIEW" | "RESOLVED" | "ALERT_TRIGGERED";
  clip_status: "PENDING" | "PROCESSING" | "READY" | "FAILED";
  clip_url?: string;
  thumbnail_url?: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  latest_review?: IncidentReview;
  events?: IncidentEvent[];
  reviews?: IncidentReview[];
  created_at: string;
}

export interface SummaryReport {
  total_alerts: number;
  confirmed_violence: number;
  false_positives: number;
  needs_review: number;
  awaiting_review: number;
  false_positive_rate: number;
  by_camera: Record<string, number>;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
}
