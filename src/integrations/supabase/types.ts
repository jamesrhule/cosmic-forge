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
          updated_at?: string
          visibility?: Database["public"]["Enums"]["run_visibility"]
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
          tier?: Database["public"]["Enums"]["tool_tier"]
          tool_name?: string
          user_id?: string | null
        }
        Relationships: []
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
      claim_admin: { Args: { _email: string }; Returns: boolean }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "viewer" | "researcher" | "admin"
      run_status: "queued" | "running" | "completed" | "failed" | "canceled"
      run_visibility: "public" | "unlisted" | "private"
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
      run_status: ["queued", "running", "completed", "failed", "canceled"],
      run_visibility: ["public", "unlisted", "private"],
      tool_status: ["ok", "error", "denied", "pending_approval"],
      tool_tier: ["read", "write", "destructive"],
    },
  },
} as const
