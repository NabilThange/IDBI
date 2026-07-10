import * as React from "react"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { ExternalLink } from "@phosphor-icons/react"

// Simple inline citation component (simplified from ai-elements)
export function InlineCitation({ children }) {
  return <span className="inline-block">{children}</span>
}

export function InlineCitationCard({ children }) {
  return <HoverCard openDelay={200}>{children}</HoverCard>
}

export function InlineCitationCardTrigger({ sources = [], ...props }) {
  const hostname = sources[0] ? new URL(sources[0]).hostname.replace('www.', '') : ''
  const count = sources.length

  return (
    <HoverCardTrigger asChild>
      <button
        className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-primary/10 hover:bg-primary/20 text-primary rounded border border-primary/20 transition-colors cursor-pointer"
        {...props}
      >
        <span className="text-[10px]">{hostname}</span>
        {count > 1 && (
          <span className="flex items-center justify-center w-4 h-4 text-[9px] font-bold bg-primary/20 rounded-full">
            {count}
          </span>
        )}
      </button>
    </HoverCardTrigger>
  )
}

export function InlineCitationCardBody({ children }) {
  return (
    <HoverCardContent 
      className="w-80 p-0" 
      align="start"
      side="top"
    >
      {children}
    </HoverCardContent>
  )
}

export function InlineCitationSource({ title, url, description, ...props }) {
  const hostname = url ? new URL(url).hostname.replace('www.', '') : ''
  
  return (
    <div className="p-4 space-y-2" {...props}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold leading-tight line-clamp-2">
            {title}
          </h4>
          <p className="text-xs text-muted-foreground mt-1">{hostname}</p>
        </div>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground line-clamp-3">
          {description}
        </p>
      )}
    </div>
  )
}

export function InlineCitationQuote({ children, ...props }) {
  return (
    <blockquote 
      className="mt-2 pl-4 border-l-2 border-primary/30 text-xs italic text-muted-foreground"
      {...props}
    >
      {children}
    </blockquote>
  )
}
