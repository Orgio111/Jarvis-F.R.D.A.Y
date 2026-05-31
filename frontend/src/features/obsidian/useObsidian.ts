import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api/client';

export interface VaultStatus {
  enabled: boolean;
  vault: string | null;
  file_count: number;
  size_bytes: number;
}

export interface GraphNode {
  id: string;
  label: string;
  path: string;
  type: 'agent' | 'swarm' | 'memory' | 'task' | 'improvement' | 'note';
  size: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export function useObsidian() {
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [files, setFiles] = useState<string[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiClient.get<{ data: VaultStatus }>('/obsidian/status');
      setStatus((data as any).data ?? data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load vault status');
    }
  }, []);

  const fetchFiles = useCallback(async () => {
    try {
      const data = await apiClient.get<{ data: { files: string[] } }>('/obsidian/files');
      setFiles(((data as any).data ?? data).files ?? []);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to list files');
    }
  }, []);

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<{ data: GraphData }>('/obsidian/graph');
      setGraph((data as any).data ?? data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, []);

  const readFile = useCallback(async (path: string) => {
    try {
      setLoading(true);
      setSelectedFile(path);
      const data = await apiClient.get<{ data: { content: string } }>(
        `/obsidian/read?path=${encodeURIComponent(path)}`
      );
      setFileContent(((data as any).data ?? data).content ?? '');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to read file');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchFiles();
  }, []);

  return {
    status,
    files,
    graph,
    fileContent,
    selectedFile,
    loading,
    error,
    fetchStatus,
    fetchFiles,
    fetchGraph,
    readFile,
  };
}
