import { useEffect, useState } from 'react'

export default function PetImage({ src, name, className = '' }) {
  const [failed, setFailed] = useState(false)

  useEffect(() => setFailed(false), [src])

  return (
    <div className={`pet-image ${className}`}>
      {src && !failed ? (
        <img src={src} alt={`${name} mugshot`} onError={() => setFailed(true)} />
      ) : (
        <div className="pet-image-fallback" role="img" aria-label={`No mugshot for ${name}`}>
          <span className="paw-print" aria-hidden="true">
            <i /><i /><i /><i /><b />
          </span>
          <span>NO MUGSHOT<br />ON FILE</span>
        </div>
      )}
    </div>
  )
}
