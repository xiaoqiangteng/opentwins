export type Tank = {
  tank_id: string;
  thing_id: string;
  name: string;
  wine_type: string;
  stage: string;
  risk_level: string;
  metrics: Record<string, { value: number | string | null; unit?: string }>;
  alarms: any[];
  recommendation: string;
  updated_at?: string | null;
};

// 使用相对路径，由 Vite dev server proxy 转发到后端
// 这样无论从本机、局域网还是 SSH 端口转发访问，都能正确路由
const API_BASE = '';

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const json = await response.json();
  return (json.data ?? json) as T;
}

async function post<T>(path: string, body: any): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  const json = await response.json();
  return (json.data ?? json) as T;
}

export const wineApi = {
  base: API_BASE,
  overview: () => get<any>('/api/wine/overview'),
  tanks: () => get<Tank[]>('/api/wine/tanks'),
  tank: (id: string) => get<Tank>(`/api/wine/tanks/${id}`),
  history: (id: string, metric: string) => get<any>(`/api/wine/tanks/${id}/history?metric=${metric}&hours=72`),
  alarms: (id: string) => get<any>(`/api/wine/tanks/${id}/alarms`),
  prediction: (id: string) => get<any>(`/api/wine/tanks/${id}/prediction`),
  simulate: (id: string, body: any) => post<any>(`/api/wine/tanks/${id}/simulate`, body),
};
