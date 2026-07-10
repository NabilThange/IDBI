import { memo } from "react"

/**
 * Response – lightweight markdown renderer for streaming AI messages.
 * Falls back to react-markdown if streamdown is not installed.
 */
let Streamdown
try {
  Streamdown = (await import("streamdown")).Streamdown
} catch {
  // fallback: render as plain preformatted text
  Streamdown = ({ children, className, ...rest }) => (
    <div className={className} {...rest} style={{ whiteSpace: "pre-wrap" }}>
      {children}
    </div>
  )
}

function cn(...classes) {
  return classes.filter(Boolean).join(" ")
}

export const Response = memo(
  ({ className, children, ...props }) => (
    <Streamdown
      className={cn("ai-response size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0", className)}
      {...props}
    >
      {children}
    </Streamdown>
  ),
  (prev, next) => prev.children === next.children
)

Response.displayName = "Response"
