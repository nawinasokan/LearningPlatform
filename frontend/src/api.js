const API = import.meta.env.VITE_API_URL || '/api/v1'
export async function request(path, options = {}) {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  })
  if (response.status === 401) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.dispatchEvent(new Event('auth-expired'))
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `Request failed (${response.status})`)
  }
  return response.status === 204 ? null : response.json()
}
