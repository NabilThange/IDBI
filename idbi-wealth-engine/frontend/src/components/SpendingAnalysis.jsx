import { useState, useEffect } from 'react'
import { useSession } from '../context/SessionContext'
import axios from 'axios'
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { ArrowClockwise as RefreshCw, Warning as AlertTriangle, ArrowsDownUp as ArrowUpDown, ShoppingBag, CreditCard } from '@phosphor-icons/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

const CATEGORY_COLORS = {
  rent: '#ef4444',          // Red
  food: '#f59e0b',          // Amber
  transportation: '#06b6d4', // Cyan
  utilities: '#6b7280',     // Gray
  entertainment: '#8b5cf6', // Purple
  shopping: '#ec4899',      // Pink
  investment: '#3b82f6',    // Blue
  income: '#10b981',        // Green
  other: '#9ca3af'          // Light Gray
}

export default function SpendingAnalysis() {
  const { sessionId } = useSession()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [sortField, setSortField] = useState('amount') // 'amount' or 'count'
  const [sortOrder, setSortOrder] = useState('desc')

  const fetchSpendingAnalysis = async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)
    setError(null)

    try {
      const response = await axios.get(`/api/spending-analysis?session_id=${sessionId}&refresh=${refresh}`)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching spending analysis:', err)
      setError('Failed to load spending analysis. Please make sure the backend is running.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSpendingAnalysis()
    }, 0)
    return () => clearTimeout(timer)
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
          <p className="text-muted-foreground text-sm">Analyzing transactions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/10">
        <CardContent className="pt-6 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-destructive mx-auto" />
          <p className="text-destructive font-medium">{error}</p>
          <Button onClick={() => fetchSpendingAnalysis()}>Retry</Button>
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  // Process data for Recharts Pie Chart
  const pieData = data.spending_by_category.map(item => ({
    name: item.category.charAt(0).toUpperCase() + item.category.slice(1),
    value: item.amount,
    percent: item.percent,
    color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other
  })).filter(item => item.value > 0)

  // Sort function for category table
  const sortedCategories = [...data.spending_by_category].sort((a, b) => {
    const valA = sortField === 'amount' ? a.amount : a.transaction_count
    const valB = sortField === 'amount' ? b.amount : b.transaction_count
    return sortOrder === 'desc' ? valB - valA : valA - valB
  })

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header and Summary */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">Spending Analysis</h2>
          <p className="text-muted-foreground mt-1">Detailed breakdown of your recent expenses</p>
        </div>
        <div className="flex items-center gap-3">
          {data.cached && (
            <Badge variant="secondary" className="bg-muted text-muted-foreground text-xs">
              Cached Analysis
            </Badge>
          )}
          <Button
            variant="outline"
            size="icon"
            onClick={() => fetchSpendingAnalysis(true)}
            disabled={refreshing}
            className="hover:rotate-180 transition-transform duration-500"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Overview stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20 dark:from-primary/10 dark:to-primary/20 dark:border-primary/30">
          <CardHeader className="pb-2">
            <CardDescription className="text-primary font-semibold">Total Expenses Analyzed</CardDescription>
            <CardTitle className="text-3xl font-bold">₹{data.total_spent.toLocaleString('en-IN')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Excludes investments, transfers, and loan EMI payments</p>
          </CardContent>
        </Card>

        <Card className="col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">AI Financial Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">{data.summary}</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Pie Chart Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Spending Category Breakdown</CardTitle>
            <CardDescription>Visual distribution of total recent debit transactions</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col justify-center items-center">
            {pieData.length > 0 ? (
              <>
                <div className="w-full h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(value) => [`₹${value.toLocaleString('en-IN')}`, 'Amount']}
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: 'var(--radius)',
                          color: 'hsl(var(--foreground))'
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 mt-4 text-xs font-medium">
                  {pieData.map((item, index) => (
                    <div key={index} className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span>{item.name} ({item.percent}%)</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-muted-foreground py-20">No spending data to display</div>
            )}
          </CardContent>
        </Card>

        {/* Categories Table Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Category Details</CardTitle>
            <CardDescription>Click column headers to sort by amount or transaction count</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b text-muted-foreground font-semibold">
                  <th className="py-3 pr-4">Category</th>
                  <th 
                    className="py-3 px-4 text-right cursor-pointer hover:text-foreground select-none"
                    onClick={() => toggleSort('amount')}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      Amount
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Percent</th>
                  <th 
                    className="py-3 pl-4 text-right cursor-pointer hover:text-foreground select-none"
                    onClick={() => toggleSort('count')}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      Count
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedCategories.map((cat, index) => {
                  const color = CATEGORY_COLORS[cat.category] || CATEGORY_COLORS.other
                  return (
                    <tr key={index} className="border-b last:border-0 hover:bg-muted/40 transition-colors">
                      <td className="py-3 pr-4 font-medium flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                        <span className="capitalize">{cat.category}</span>
                      </td>
                      <td className="py-3 px-4 text-right font-semibold">
                        ₹{cat.amount.toLocaleString('en-IN')}
                      </td>
                      <td className="py-3 px-4 text-right text-muted-foreground">
                        {cat.percent}%
                      </td>
                      <td className="py-3 pl-4 text-right font-medium">
                        {cat.transaction_count}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Grid: Top Merchants & Trends/Optimizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top Merchants Card */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-primary" />
              Top Merchants & Venues
            </CardTitle>
            <CardDescription>Places where you spend the most money</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <div className="space-y-4">
              {data.top_merchants.map((merchant, index) => {
                const color = CATEGORY_COLORS[merchant.category] || CATEGORY_COLORS.other
                return (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors border">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center font-bold text-primary text-sm">
                        #{index + 1}
                      </div>
                      <div>
                        <p className="font-semibold text-sm">{merchant.name}</p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                          <span className="text-xs text-muted-foreground capitalize">{merchant.category}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-sm">₹{merchant.amount.toLocaleString('en-IN')}</p>
                      <p className="text-xs text-muted-foreground">{merchant.transaction_count} transactions</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Spending Trends & AI Recommendations */}
        <div className="space-y-8 flex flex-col justify-between h-full">
          {/* Trends/Alerts */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Spending Trends & Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.trends && data.trends.length > 0 ? (
                data.trends.map((trend, index) => (
                  <div key={index} className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-lg text-sm flex gap-3 dark:bg-amber-950/20 dark:border-amber-900">
                    <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-amber-800 dark:text-amber-400 capitalize">High spend in {trend.category}</p>
                      <p className="text-amber-700 dark:text-amber-500/80 mt-1">
                        Current spending is ₹{trend.current_amount.toLocaleString('en-IN')}. This is significantly higher than your average for other categories.
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-muted-foreground py-6 text-sm border border-dashed rounded-lg">
                  No unusual spending patterns detected. Great job keeping budgets stable!
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Optimizations */}
          <Card className="flex-1">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-purple-600" />
                Optimization Advice
              </CardTitle>
              <CardDescription>AI-generated ways to free up investable surplus</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.recommendations.map((tip, index) => (
                  <div key={index} className="bg-purple-50 dark:bg-purple-950/10 border border-purple-100 dark:border-purple-900/30 p-3 rounded-lg text-sm text-purple-900 dark:text-purple-300">
                    {tip}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
