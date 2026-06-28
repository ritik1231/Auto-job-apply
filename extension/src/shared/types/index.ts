export interface User {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
  gmail_token_expiry?: string | null;
}

export type ApplicationStatus = "draft" | "sent" | "failed";

export interface JobPost {
  id: string;
  company: string | null;
  recruiter_name: string | null;
  recruiter_email: string | null;
  job_title: string | null;
  skills: string[];
  experience_required: string | null;
  responsibilities: string[];
  location: string | null;
  employment_type: string | null;
  seniority: string | null;
  job_summary: string | null;
  source_platform: string;
  created_at: string;
  from_cache?: boolean;
}

export interface ApplicationDraft {
  id: string;
  job_post_id: string;
  resume_id: string;
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
  generated_subject: string;
  generated_email: string;
  status: string;
  created_at: string;
}

export interface ApplicationSendResult {
  application_id: string;
  sent_at: string;
  gmail_message_id: string;
}

export interface ApplicationHistoryItem {
  id: string;
  job_title: string | null;
  company: string | null;
  status: "draft" | "sent" | "failed";
  match_score: number | null;
  sent_at: string | null;
  created_at: string;
}

export interface Application {
  id: string;
  job_post_id: string;
  resume_id: string;
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
  generated_subject: string;
  generated_email: string;
  status: ApplicationStatus;
  sent_at: string | null;
  gmail_message_id: string | null;
  created_at: string;
}

export interface Resume {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  is_active: boolean;
  created_at: string;
}

export interface ResumeListResponse {
  resumes: Resume[];
  active_id: string | null;
}
