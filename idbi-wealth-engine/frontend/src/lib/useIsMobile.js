import { useState, useEffect } from 'react'

// Detects whether the current viewport is at "mobile" width.
// Uses matchMedia (viewport based, as requested) and stays reactive when the
// user resizes or rotates the device. `maxWidth` is the breakpoint in px.
export function useIsMobile(maxWidth = 768) {
  const query = `(max-width: ${maxWidth}px)`

  const getMatch = () =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(query).matches
      : false

  const [isMobile, setIsMobile] = useState(getMatch)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mql = window.matchMedia(query)
    const onChange = (event) => setIsMobile(event.matches)
    setIsMobile(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [query])

  return isMobile
}
