import { useState, useEffect } from 'react'
import { useSession } from '../context/SessionContext'
import axios from 'axios'
import { ArrowClockwise as RefreshCw, BookOpen, WarningCircle as AlertCircle, Compass, CheckCircle as CheckCircle2, CaretRight as ChevronRight } from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

const PRODUCT_TYPE_COLORS = {
  FD: 'bg-secondary text-secondary-foreground border-border',
  SIP: 'bg-primary/10 text-primary border-primary/20',
  Gold: 'bg-muted text-foreground border-border',
  ETF: 'bg-secondary text-secondary-foreground border-border',
  Insurance: 'bg-destructive/10 text-destructive border-destructive/20',
  default: 'bg-muted text-muted-foreground border-border'
}

export default function Recommendations() {
  const { sessionId } = useSession()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [activeProductInfo, setActiveProductInfo] = useState(null)

  const fetchRecommendations = async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    setError(null)

    try {
      const response = await axios.get(`/api/recommendations?session_id=${sessionId}&refresh=${refresh}`)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching recommendations:', err)
      if (err.response?.status === 503) {
        setError('RAG knowledge base is not initialized. Please ensure the BM25 index has been built in the backend.')
      } else {
        setError('Failed to load recommendations. Please verify the backend is running.')
      }
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRecommendations()
    }, 0)
    return () => clearTimeout(timer)
  }, [sessionId])

  const getProductBadgeColor = (type) => {
    return PRODUCT_TYPE_COLORS[type] || PRODUCT_TYPE_COLORS.default
  }

  const formatSourceLabel = (source) => {
    return source.replace('.md', '').split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground text-sm">Consulting RAG Advisor & Retrieving Products...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/10">
        <CardContent className="pt-6 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
          <p className="text-destructive font-medium">{error}</p>
          <Button onClick={() => fetchRecommendations()}>Retry</Button>
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header and Invalidation */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Product Recommendations</h2>
          <p className="text-muted-foreground mt-1">RAG-powered advisory mapping official IDBI offerings to your profile</p>
        </div>
        <div className="flex items-center gap-3">
          {data.cached && (
            <Badge variant="secondary" className="bg-muted text-muted-foreground text-xs">
              Cached Advisory
            </Badge>
          )}
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchRecommendations(true)}
            disabled={refreshing}
            className="hover:rotate-180 transition-transform duration-500"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Main summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-secondary border-border">
          <CardHeader className="pb-2">
            <CardDescription className="text-secondary-foreground font-semibold">Available Monthly Surplus</CardDescription>
            <CardTitle className="text-3xl font-bold">₹{data.total_investable.toLocaleString('en-IN')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Calculated after subtracting your current active SIP commitments</p>
          </CardContent>
        </Card>

        <Card className="col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Compass className="w-5 h-5 text-primary" />
              Strategic Investment Approach
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">{data.summary}</p>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {data.recommendations.map((rec, index) => (
          <Card key={index} className="flex flex-col hover:shadow-lg transition-all border border-border">
            <CardHeader className="pb-4">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <Badge className={`${getProductBadgeColor(rec.product_type)} border py-0.5 px-2 text-[10px] font-bold tracking-wider uppercase`}>
                    {rec.product_type}
                  </Badge>
                  <CardTitle className="text-xl font-bold mt-2">{rec.product_name}</CardTitle>
                </div>
                <div className="text-right">
                  <span className="text-xs text-muted-foreground block">Allocation</span>
                  <span className="text-lg font-bold text-primary">₹{rec.recommended_amount.toLocaleString('en-IN')}/mo</span>
                </div>
              </div>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col justify-between space-y-6">
              {/* Rationale */}
              <div className="space-y-1.5">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Advisor Rationale</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {rec.rationale}
                </p>
              </div>

              {/* Key Features */}
              <div className="space-y-2.5 pt-2">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Key Product Terms & Rates</h4>
                <div className="grid grid-cols-1 gap-2">
                  {rec.key_features.map((feature, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <CheckCircle2 className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action */}
              <div className="pt-4 border-t flex justify-between items-center mt-auto">
                <Button 
                  variant="outline" 
                  size="sm"
                  className="w-full flex justify-between items-center gap-1 group"
                  onClick={() => setActiveProductInfo(rec.product_name === activeProductInfo ? null : rec.product_name)}
                >
                  <span>Learn details & apply</span>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>

              {/* Mock info panel */}
              {activeProductInfo === rec.product_name && (
                <div className="mt-3 bg-muted border border-border p-3 rounded-lg text-xs space-y-2 animate-in slide-in-from-top-2 duration-300">
                  <p className="font-semibold text-foreground">How to apply:</p>
                  <p className="text-muted-foreground leading-relaxed">
                    You can purchase or set up this product by instructing our virtual agent. Try launching the **AI Assistant** and typing: 
                    <span className="block font-mono bg-card p-1.5 mt-1 border border-border rounded text-primary">
                      "I want to apply for {rec.product_name}"
                    </span>
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* RAG Knowledge Attribution Card */}
      <Card className="border border-dashed bg-muted/30">
        <CardContent className="py-4 flex flex-col md:flex-row justify-between items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4.5 h-4.5 text-primary" />
            <span className="font-semibold text-muted-foreground">Information sourced from:</span>
          </div>
          <div className="flex flex-wrap gap-2 justify-center">
            {data.knowledge_sources && data.knowledge_sources.length > 0 ? (
              data.knowledge_sources.map((src, index) => (
                <Badge key={index} variant="outline" className="bg-card text-[11px] font-medium border-border">
                  {formatSourceLabel(src)}
                </Badge>
              ))
            ) : (
              <span className="text-muted-foreground">IDBI Bank Product Guidelines</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
