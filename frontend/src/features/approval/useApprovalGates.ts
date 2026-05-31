import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface ApprovalRequest {
  request_id: string;
  action: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  details: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected' | 'timed_out' | 'auto_approved';
  created_at: number;
  resolved_at: number | null;
  resolved_by: string | null;
  reject_reason: string;
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: ['approval', 'pending'],
    queryFn: async () => {
      const res = await apiClient.get<{ requests: ApprovalRequest[] }>('/approval/pending');
      return res.data.requests;
    },
    refetchInterval: 3_000,   // Poll every 3s — gates are time-sensitive
  });
}

export function useApprovalHistory(limit = 50) {
  return useQuery({
    queryKey: ['approval', 'history', limit],
    queryFn: async () => {
      const res = await apiClient.get<{ history: ApprovalRequest[] }>(`/approval/history?limit=${limit}`);
      return res.data.history;
    },
    refetchInterval: 15_000,
  });
}

export function useRespondApproval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, approved, reason }: { requestId: string; approved: boolean; reason?: string }) => {
      await apiClient.post(`/approval/${requestId}/respond`, { approved, reason: reason ?? '' });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approval'] });
    },
  });
}
