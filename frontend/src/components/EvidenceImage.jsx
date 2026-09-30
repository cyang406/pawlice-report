import { useEffect, useState } from 'react'

export default function EvidenceImage({ src, label = 'Event photo' }) {
  const [failed, setFailed] = useState(false)

  useEffect(() => setFailed(false), [src])

  if (!src) return null

  return (
    <div className="evidence-image">
      {failed ? (
        <span>Photo unavailable</span>
      ) : (
        <img src={src} alt={label} loading="lazy" onError={() => setFailed(true)} />
      )}
    </div>
  )
}
