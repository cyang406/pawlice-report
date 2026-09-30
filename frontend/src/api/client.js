async function request(path, options = {}, responseType = 'json') {
  let response
  try {
    const isFormData = options.body instanceof FormData
    response = await fetch(path, {
      credentials: 'same-origin',
      ...options,
      headers: {
        ...(options.body && !isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    })
  } catch {
    throw new Error('Cannot reach the Pawlice desk. Check that the backend is running.')
  }

  if (response.status === 204) return null

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : 'Please check the form and try again.'
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  if (responseType === 'blob') return response.blob()
  return response.json()
}

function imageBody(file) {
  const body = new FormData()
  body.append('file', file)
  return body
}

export const api = {
  me: () => request('/api/auth/me'),
  register: (credentials) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(credentials) }),
  login: (credentials) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  listPets: () => request('/api/pets'),
  getPet: (id) => request(`/api/pets/${id}`),
  createPet: (pet) => request('/api/pets', { method: 'POST', body: JSON.stringify(pet) }),
  prepareMugshot: (file) => request('/api/images/prepare', { method: 'POST', body: imageBody(file) }, 'blob'),
  uploadPetImage: (id, file) => request(`/api/pets/${id}/image`, { method: 'POST', body: imageBody(file) }),
  deletePet: (id) => request(`/api/pets/${id}`, { method: 'DELETE' }),
  listIncidents: (petId) => request(`/api/pets/${petId}/incidents`),
  listEvents: (petId) => request(`/api/pets/${petId}/events`),
  getStats: (petId) => request(`/api/pets/${petId}/stats`),
  createIncident: (petId, incident) =>
    request(`/api/pets/${petId}/incidents`, { method: 'POST', body: JSON.stringify(incident) }),
  createEvent: (petId, event) =>
    request(`/api/pets/${petId}/events`, { method: 'POST', body: JSON.stringify(event) }),
  uploadIncidentImage: (id, file) => request(`/api/incidents/${id}/image`, { method: 'POST', body: imageBody(file) }),
  uploadEventImage: (id, file) => request(`/api/events/${id}/image`, { method: 'POST', body: imageBody(file) }),
  deleteIncident: (id) => request(`/api/incidents/${id}`, { method: 'DELETE' }),
  deleteEvent: (id) => request(`/api/events/${id}`, { method: 'DELETE' }),
}
