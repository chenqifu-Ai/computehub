import http from './request'
export function login(data: { username: string; password: string }) { return http.post('/auth/login', data) }
export function getUserInfo() { return http.get('/auth/me') }
