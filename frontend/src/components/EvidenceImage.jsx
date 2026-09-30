import { useEffect, useState } from 'react'

export default function EvidenceImage({ src }) {
  const [failed, setFailed] = useState(false)

  useEffect(() => setFailed(false), [src])

  if (!src) return null

  return (
    <div className="evidence-image">
      {failed ? (
        <span>Evidence image unavailable</span>
      ) : (
        <img src={src} alt="Incident evidence" loading="lazy" onError={() => setFailed(true)} />
      )}
    </div>
  )
}
