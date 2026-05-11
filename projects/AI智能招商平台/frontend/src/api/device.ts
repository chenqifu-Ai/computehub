import http from './request'
export const deviceApi = {
  list: (p?: any) => http.get('/admin/devices', { params: p }),
  detail: (id: number) => http.get(`/admin/devices/${id}`),
  forceUpdate: (id: string) => http.post(`/admin/devices/${id}/force-update`),
  dashboard: () => http.get('/admin/dashboard/stats'),
}
