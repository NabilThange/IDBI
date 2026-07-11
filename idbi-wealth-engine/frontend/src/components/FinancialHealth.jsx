import { useState, useEffect } from 'react'
import { useSession } from '../context/SessionContext'
import apiClient from '@/lib/apiClient'
import { CheckCircle, WarningCircle as AlertCircle, ArrowClockwise as RefreshCw } from '@phosphor-icons/react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

export default function FinancialHealth() {
  const { sessionId } = useSession()
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchHealthData = async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)

    try {
      const response = await apiClient.get(`/api/financial-health?session_id=${sessionId}&refresh=${refresh}`)
      setHealthData(response.data)
    } catch (error) {
      console.error('Error fetching financial health:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHealthData()
    }, 0)
    return () => clearTimeout(timer)
  }, [sessionId])

  const getGradeColor = (grade) => {
    if (grade.startsWith('A')) return 'bg-green-500'
    if (grade.startsWith('B')) return 'bg-blue-500'
    if (grade.startsWith('C')) return 'bg-amber-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-muted-foreground">Loading health data...</div>
        </CardContent>
      </Card>
    )
  }

  if (!healthData) return null

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Financial Health</CardTitle>
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchHealthData(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className={`w-24 h-24 rounded-full ${getGradeColor(healthData.grade)} flex items-center justify-center`}>
            <span className="text-4xl font-bold text-white">{healthData.grade}</span>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Score</div>
            <div className="text-3xl font-bold">{healthData.score}/100</div>
          </div>
          <p className="text-sm text-muted-foreground">{healthData.summary}</p>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <h4 className="font-semibold">Strengths</h4>
            </div>
            <div className="space-y-2">
              {healthData.strengths.map((strength, index) => (
                <div key={index} className="bg-green-50 border-l-4 border-green-500 p-3 rounded text-sm">
                  {strength}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              <h4 className="font-semibold">Areas for Improvement</h4>
            </div>
            <div className="space-y-2">
              {healthData.concerns.map((concern, index) => (
                <div key={index} className="bg-amber-50 border-l-4 border-amber-500 p-3 rounded text-sm">
                  {concern}
                </div>
              ))}
            </div>
          </div>
        </div>

        {healthData.cached && (
          <Badge variant="secondary" className="w-full justify-center">
            Cached result
          </Badge>
        )}
      </CardContent>
    </Card>
  )
}
