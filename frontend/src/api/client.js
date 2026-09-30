async function request(path, options = {}) {
  let response
  try {
    response = await fetch(path, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    })
  } catch {
    throw new Error('Cannot reach the Pawlice desk. Check that the backend is running.')
  }
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Please try again.')
  return data
}

export const api = {
  me: () => request('/api/auth/me'),
  register: (credentials) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(credentials) }),
  login: (credentials) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  listPets: () => request('/api/pets'),
  getPet: (id) => request(`/api/pets/${id}`),
  createPet: (pet) => request('/api/pets', { method: 'POST', body: JSON.stringify(pet) }),
  deletePet: (id) => request(`/api/pets/${id}`, { method: 'DELETE' }),
  listIncidents: (petId) => request(`/api/pets/${petId}/incidents`),
  getStats: (petId) => request(`/api/pets/${petId}/stats`),
  createIncident: (petId, incident) => request(`/api/pets/${petId}/incidents`, { method: 'POST', body: JSON.stringify(incident) }),
  deleteIncident: (id) => request(`/api/incidents/${id}`, { method: 'DELETE' }),
}
