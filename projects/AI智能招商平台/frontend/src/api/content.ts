import http from './request'
export const brandApi = {
  list: () => http.get('/project/brands'),
  detail: (id: number) => http.get(`/project/brands/${id}`),
  create: (data: any) => http.post('/project/brands', data),
  update: (id: number, data: any) => http.put(`/project/brands/${id}`, data),
  delete: (id: number) => http.delete(`/project/brands/${id}`),
}
export const qaApi = {
  list: (c?: string) => http.get('/project/qa', { params: { category: c } }),
  create: (data: any) => http.post('/project/qa', data),
  update: (id: number, data: any) => http.put(`/project/qa/${id}`, data),
  delete: (id: number) => http.delete(`/project/qa/${id}`),
}
