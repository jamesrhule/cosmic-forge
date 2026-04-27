export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      api_rate_limit: {
        Row: {
          actor_id: string
          refilled_at: string
          scope: string
          tokens: number
        }
        Insert: {
          actor_id: string
          refilled_at?: string
          scope: string
          tokens?: number
        }
        Update: {
          actor_id?: string
          refilled_at?: string
          scope?: string
          tokens?: number
        }
        Relationships: []
      }
      audit_reports: {
        Row: {
          created_at: string
          fail_count: number | null
          pass_count: number | null
          run_id: string
          verdicts: Json
        }
        Insert: {
          created_at?: string
          fail_count?: number | null
          pass_count?: number | null
          run_id: string
          verdicts: Json
        }
        Update: {
          created_at?: string
          fail_count?: number | null
          pass_count?: number | null
          run_id?: string
          verdicts?: Json
        }
        Relationships: [
          {
            foreignKeyName: "audit_reports_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: true
            referencedRelation: "runs"
            referencedColumns: ["id"]
          },
        ]
      }
      jobs: {
        Row: {
          attempts: number
          compute_class: Database["public"]["Enums"]["compute_class"]
          created_at: string
          created_by: string | null
          error: string | null
          finished_at: string | null
          id: string
          kind: string
          locked_by: string | null
          locked_until: string | null
          max_attempts: number
          payload: Json
          priority: number
          result: Json | null
          run_id: string | null
          scheduled_at: string
          started_at: string | null
          status: Database["public"]["Enums"]["job_status"]
          tenant_id: string
          updated_at: string
        }
        Insert: {
          attempts?: number
          compute_class?: Database["public"]["Enums"]["compute_class"]
          created_at?: string
          created_by?: string | null
          error?: string | null
          finished_at?: string | null
          id?: string
          kind: string
          locked_by?: string | null
          locked_until?: string | null
          max_attempts?: number
          payload?: Json
          priority?: number
          result?: Json | null
          run_id?: string | null
          scheduled_at?: string
          started_at?: string | null
          status?: Database["public"]["Enums"]["job_status"]
          tenant_id: string
          updated_at?: string
        }
        Update: {
          attempts?: number
          compute_class?: Database["public"]["Enums"]["compute_class"]
          created_at?: string
          created_by?: string | null
          error?: string | null
          finished_at?: string | null
          id?: string
          kind?: string
          locked_by?: string | null
          locked_until?: string | null
          max_attempts?: number
          payload?: Json
          priority?: number
          result?: Json | null
          run_id?: string | null
          scheduled_at?: string
          started_at?: string | null
          status?: Database["public"]["Enums"]["job_status"]
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "jobs_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "jobs_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          affiliation: string | null
          avatar_url: string | null
          bio: string | null
          created_at: string
          display_name: string | null
          handle: string | null
          id: string
          updated_at: string
        }
        Insert: {
          affiliation?: string | null
          avatar_url?: string | null
          bio?: string | null
          created_at?: string
          display_name?: string | null
          handle?: string | null
          id: string
          updated_at?: string
        }
        Update: {
          affiliation?: string | null
          avatar_url?: string | null
          bio?: string | null
          created_at?: string
          display_name?: string | null
          handle?: string | null
          id?: string
          updated_at?: string
        }
        Relationships: []
      }
      run_results: {
        Row: {
          created_at: string
          payload: Json
          run_id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          payload: Json
          run_id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          payload?: Json
          run_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "run_results_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: true
            referencedRelation: "runs"
            referencedColumns: ["id"]
          },
        ]
      }
      runs: {
        Row: {
          author_user_id: string | null
          completed_at: string | null
          config: Json
          created_at: string
          id: string
          label: string | null
          notes: string | null
          potential_kind: string | null
          precision: string | null
          started_at: string | null
          status: Database["public"]["Enums"]["run_status"]
          tenant_id: string | null
          updated_at: string
          visibility: Database["public"]["Enums"]["run_visibility"]
        }
        Insert: {
          author_user_id?: string | null
          completed_at?: string | null
          config: Json
          created_at?: string
          id: string
          label?: string | null
          notes?: string | null
          potential_kind?: string | null
          precision?: string | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["run_status"]
          tenant_id?: string | null
          updated_at?: string
          visibility?: Database["public"]["Enums"]["run_visibility"]
        }
        Update: {
          author_user_id?: string | null
          completed_at?: string | null
          config?: Json
          created_at?: string
          id?: string
          label?: string | null
          notes?: string | null
          potential_kind?: string | null
          precision?: string | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["run_status"]
          tenant_id?: string | null
          updated_at?: string
          visibility?: Database["public"]["Enums"]["run_visibility"]
        }
        Relationships: [
          {
            foreignKeyName: "runs_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      system_incidents: {
        Row: {
          body: string | null
          created_at: string
          id: string
          resolved_at: string | null
          severity: string
          started_at: string
          status: string
          title: string
          updated_at: string
        }
        Insert: {
          body?: string | null
          created_at?: string
          id?: string
          resolved_at?: string | null
          severity?: string
          started_at?: string
          status?: string
          title: string
          updated_at?: string
        }
        Update: {
          body?: string | null
          created_at?: string
          id?: string
          resolved_at?: string | null
          severity?: string
          started_at?: string
          status?: string
          title?: string
          updated_at?: string
        }
        Relationships: []
      }
      tenant_members: {
        Row: {
          joined_at: string
          role: Database["public"]["Enums"]["tenant_role"]
          tenant_id: string
          user_id: string
        }
        Insert: {
          joined_at?: string
          role?: Database["public"]["Enums"]["tenant_role"]
          tenant_id: string
          user_id: string
        }
        Update: {
          joined_at?: string
          role?: Database["public"]["Enums"]["tenant_role"]
          tenant_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "tenant_members_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      tenants: {
        Row: {
          billing_email: string | null
          created_at: string
          created_by: string | null
          id: string
          name: string
          slug: string
          subscription_tier: Database["public"]["Enums"]["subscription_tier"]
          updated_at: string
        }
        Insert: {
          billing_email?: string | null
          created_at?: string
          created_by?: string | null
          id?: string
          name: string
          slug: string
          subscription_tier?: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string
        }
        Update: {
          billing_email?: string | null
          created_at?: string
          created_by?: string | null
          id?: string
          name?: string
          slug?: string
          subscription_tier?: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string
        }
        Relationships: []
      }
      tool_call_audit: {
        Row: {
          approval_token_id: string | null
          args_redacted: Json | null
          conversation_id: string | null
          created_at: string
          id: string
          latency_ms: number | null
          result_summary: string | null
          status: Database["public"]["Enums"]["tool_status"]
          tenant_id: string | null
          tier: Database["public"]["Enums"]["tool_tier"]
          tool_name: string
          user_id: string | null
        }
        Insert: {
          approval_token_id?: string | null
          args_redacted?: Json | null
          conversation_id?: string | null
          created_at?: string
          id?: string
          latency_ms?: number | null
          result_summary?: string | null
          status: Database["public"]["Enums"]["tool_status"]
          tenant_id?: string | null
          tier: Database["public"]["Enums"]["tool_tier"]
          tool_name: string
          user_id?: string | null
        }
        Update: {
          approval_token_id?: string | null
          args_redacted?: Json | null
          conversation_id?: string | null
          created_at?: string
          id?: string
          latency_ms?: number | null
          result_summary?: string | null
          status?: Database["public"]["Enums"]["tool_status"]
          tenant_id?: string | null
          tier?: Database["public"]["Enums"]["tool_tier"]
          tool_name?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "tool_call_audit_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          granted_at: string
          granted_by: string | null
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          granted_at?: string
          granted_by?: string | null
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          granted_at?: string
          granted_by?: string | null
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
      viz_timelines: {
        Row: {
          bytes_size: number | null
          created_at: string
          duration_seconds: number | null
          expires_at: string | null
          frame_count: number | null
          manifest: Json | null
          run_id: string
          storage_path: string
        }
        Insert: {
          bytes_size?: number | null
          created_at?: string
          duration_seconds?: number | null
          expires_at?: string | null
          frame_count?: number | null
          manifest?: Json | null
          run_id: string
          storage_path: string
        }
        Update: {
          bytes_size?: number | null
          created_at?: string
          duration_seconds?: number | null
          expires_at?: string | null
          frame_count?: number | null
          manifest?: Json | null
          run_id?: string
          storage_path?: string
        }
        Relationships: [
          {
            foreignKeyName: "viz_timelines_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: true
            referencedRelation: "runs"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      check_rate_limit: {
        Args: { _capacity: number; _refill_per_sec: number; _scope: string }
        Returns: boolean
      }
      claim_admin: { Args: { _email: string }; Returns: boolean }
      claim_next_job: {
        Args: {
          _classes: Database["public"]["Enums"]["compute_class"][]
          _lease_seconds?: number
          _worker_id: string
        }
        Returns: {
          attempts: number
          compute_class: Database["public"]["Enums"]["compute_class"]
          created_at: string
          created_by: string | null
          error: string | null
          finished_at: string | null
          id: string
          kind: string
          locked_by: string | null
          locked_until: string | null
          max_attempts: number
          payload: Json
          priority: number
          result: Json | null
          run_id: string | null
          scheduled_at: string
          started_at: string | null
          status: Database["public"]["Enums"]["job_status"]
          tenant_id: string
          updated_at: string
        }
        SetofOptions: {
          from: "*"
          to: "jobs"
          isOneToOne: true
          isSetofReturn: false
        }
      }
      complete_job: {
        Args: { _error?: string; _job_id: string; _result?: Json }
        Returns: undefined
      }
      ensure_personal_tenant: { Args: { _user: string }; Returns: string }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      is_tenant_member: {
        Args: { _tenant: string; _user: string }
        Returns: boolean
      }
      prune_old_audit_rows: { Args: never; Returns: number }
      tenant_role: {
        Args: { _tenant: string; _user: string }
        Returns: Database["public"]["Enums"]["tenant_role"]
      }
    }
    Enums: {
      app_role: "viewer" | "researcher" | "admin"
      compute_class: "cpu" | "gpu_small" | "gpu_large"
      job_status: "queued" | "running" | "succeeded" | "failed" | "cancelled"
      run_status: "queued" | "running" | "completed" | "failed" | "canceled"
      run_visibility: "public" | "unlisted" | "private"
      subscription_tier: "free" | "pro" | "team" | "enterprise"
      tenant_role: "owner" | "admin" | "member" | "viewer"
      tool_status: "ok" | "error" | "denied" | "pending_approval"
      tool_tier: "read" | "write" | "destructive"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["viewer", "researcher", "admin"],
      compute_class: ["cpu", "gpu_small", "gpu_large"],
      job_status: ["queued", "running", "succeeded", "failed", "cancelled"],
      run_status: ["queued", "running", "completed", "failed", "canceled"],
      run_visibility: ["public", "unlisted", "private"],
      subscription_tier: ["free", "pro", "team", "enterprise"],
      tenant_role: ["owner", "admin", "member", "viewer"],
      tool_status: ["ok", "error", "denied", "pending_approval"],
      tool_tier: ["read", "write", "destructive"],
    },
  },
} as const
