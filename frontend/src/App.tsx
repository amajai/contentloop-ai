import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useTheme } from '@/components/ThemeProvider'
import { Toaster } from '@/components/ui/sonner'
import { toast } from 'sonner'
import { Feather, Sparkles, Wand2, Copy, X, Moon, Sun, Loader2, Check, RotateCcw, ChevronDown, ChevronRight, Palette, Target, TrendingUp, Hash, Zap } from 'lucide-react'

function App() {
  const [copyButtonText, setCopyButtonText] = useState('Copy')
  const [clearButtonText, setClearButtonText] = useState('Clear')
  
  // AI Agent states
  const [aiAgentTopic, setAiAgentTopic] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [aiGeneratedContent, setAiGeneratedContent] = useState('')
  const [sessionStatus, setSessionStatus] = useState('') // 'waiting_feedback', 'completed', ''
  const [feedbackInput, setFeedbackInput] = useState('')
  const [isAiGenerating, setIsAiGenerating] = useState(false)
  const [contentLength, setContentLength] = useState('medium')
  const [writingStyle, setWritingStyle] = useState('')
  const [isStyleDrawerOpen, setIsStyleDrawerOpen] = useState(false)
  const [optimizationData, setOptimizationData] = useState<any>(null)
  const [isOptimizationOpen, setIsOptimizationOpen] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  
  const { theme, setTheme } = useTheme()

  // Cookie functions
  const setCookie = (name: string, value: string, days: number = 30) => {
    const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString()
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`
  }

  const getCookie = (name: string): string => {
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop()?.split(';').shift() || '')
    }
    return ''
  }

  // Load writing style from cookie on component mount
  useEffect(() => {
    const savedStyle = getCookie('writingStyle')
    if (savedStyle) {
      setWritingStyle(savedStyle)
    }
  }, [])

  // Save writing style to cookie when it changes
  useEffect(() => {
    if (writingStyle !== undefined) {
      setCookie('writingStyle', writingStyle)
    }
  }, [writingStyle])


  const handleCopy = () => {
    navigator.clipboard.writeText(aiGeneratedContent)
    setCopyButtonText('Copied!')
    setTimeout(() => setCopyButtonText('Copy'), 2000)
  }

  const handleClear = () => {
    handleResetAiAgent()
    setClearButtonText('Cleared!')
    setTimeout(() => setClearButtonText('Clear'), 2000)
  }

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && feedbackInput.trim()) {
      e.preventDefault()
      handleProvideFeedback()
    }
  }

  // AI Agent handlers
  const handleStartAiAgent = async () => {
    if (!aiAgentTopic.trim()) {
      toast.error('Please provide your content ideas and details')
      return
    }

    setIsAiGenerating(true)
    
    try {
      const response = await fetch('http://localhost:8000/api/ai-agent/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: aiAgentTopic,
          content_length: contentLength,
          writing_style: writingStyle
        })
      })

      if (!response.ok) {
        if (response.status === 429) {
          const errorData = await response.json()
          toast.error(errorData.detail || 'Rate limit exceeded. Please try again later.')
          return
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setSessionId(data.session_id)
      setAiGeneratedContent(data.generated_post)
      setSessionStatus(data.status)
      toast.success('AI Agent started! Review the content and provide feedback.')
      
    } catch (error) {
      console.error('Error starting AI agent:', error)
      toast.error('Failed to start AI agent. Make sure the backend server is running.')
    } finally {
      setIsAiGenerating(false)
    }
  }

  const handleProvideFeedback = async () => {
    if (!sessionId || !feedbackInput.trim()) {
      toast.error('Please enter feedback')
      return
    }

    setIsAiGenerating(true)
    
    try {
      const response = await fetch('http://localhost:8000/api/ai-agent/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          feedback: feedbackInput
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.status === 'completed') {
        setSessionStatus('completed')
        toast.success(data.message)
      } else {
        setAiGeneratedContent(data.generated_post)
        setSessionStatus(data.status)
        toast.success('Feedback processed! Review the updated content.')
      }
      
      setFeedbackInput('')
      
    } catch (error) {
      console.error('Error providing feedback:', error)
      toast.error('Failed to provide feedback. Please try again.')
    } finally {
      setIsAiGenerating(false)
    }
  }

  const handleFinishSession = async () => {
    if (!sessionId) return

    try {
      const response = await fetch('http://localhost:8000/api/ai-agent/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          feedback: 'done'
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      await response.json()
      setSessionStatus('completed')
      toast.success('Session completed! Content finalized.')
      
    } catch (error) {
      console.error('Error finishing session:', error)
      toast.error('Failed to finish session.')
    }
  }

  const handleResetAiAgent = async () => {
    // If there's an active session, delete it on the backend
    if (sessionId) {
      try {
        await fetch(`http://localhost:8000/api/ai-agent/session/${sessionId}`, {
          method: 'DELETE'
        })
      } catch (error) {
        console.warn('Failed to delete session on backend:', error)
        // Continue with frontend reset even if backend deletion fails
      }
    }

    // Reset frontend state
    setSessionId('')
    setAiGeneratedContent('')
    setSessionStatus('')
    setFeedbackInput('')
    setAiAgentTopic('')
    setOptimizationData(null)
    setIsOptimizationOpen(false)
  }

  const handleOptimizeContent = async () => {
    if (!aiGeneratedContent.trim()) {
      toast.error('No content to optimize')
      return
    }

    setIsAnalyzing(true)
    
    try {
      const response = await fetch('http://localhost:8000/api/optimization/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: aiGeneratedContent,
          topic: aiAgentTopic,
          content_length: contentLength,
          industry: 'general'
        })
      })

      if (!response.ok) {
        if (response.status === 429) {
          const errorData = await response.json()
          toast.error(errorData.detail || 'Rate limit exceeded. Please try again later.')
          return
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setOptimizationData(data.optimization_data)
      setIsOptimizationOpen(true)
      toast.success('Content analysis completed!')
      
    } catch (error) {
      console.error('Error optimizing content:', error)
      toast.error('Failed to analyze content. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="min-h-screen bg-blue-50 dark:bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg border grid place-items-center bg-blue-100">
              <Feather className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">ContentLoop AI</h1>
              <p className="text-xs text-gray-500">Human-in-the-loop content creation</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleTheme}
            className="flex items-center gap-2 hover:bg-blue-50 hover:border-blue-300 transition-colors"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4 text-blue-600" /> : <Moon className="h-4 w-4 text-blue-600" />}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-6">
            {/* AI Agent Input Section */}
            <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Content Input</h3>
                  <p className="text-xs text-muted-foreground">Interactive content generation with human feedback</p>
                </div>
                {sessionId && (
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={handleFinishSession}
                      disabled={isAiGenerating || sessionStatus === 'completed'}
                      className="flex items-center gap-2 hover:bg-green-50 hover:border-green-300 transition-colors"
                    >
                      <Check className="h-3 w-3" />
                      Done
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={handleResetAiAgent}
                      className="flex items-center gap-2 hover:bg-gray-50 hover:border-gray-300 transition-colors"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Reset
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {!sessionId ? (
                // Start session form
                <div className="space-y-3">
                  <div className="space-y-1">
                    <Label htmlFor="content-length" className="text-sm">Content Length</Label>
                    <Select value={contentLength} onValueChange={setContentLength}>
                      <SelectTrigger id="content-length" className="w-full focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-0 focus-visible:border-blue-500 focus-visible:outline-none">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="short">Short</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="long">Long</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Writing Style Drawer */}
                  <div className="space-y-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setIsStyleDrawerOpen(!isStyleDrawerOpen)}
                      className="w-full justify-between h-auto p-3 hover:bg-accent hover:text-accent-foreground border border-border rounded-md"
                    >
                      <div className="flex items-center gap-2">
                        <Palette className="h-4 w-4 text-blue-600" />
                        <span className="text-sm font-medium">Writing Style</span>
                        {writingStyle && (
                          <div className="flex items-center gap-1">
                            <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
                            <span className="text-xs text-blue-600">Active</span>
                          </div>
                        )}
                      </div>
                      {isStyleDrawerOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </Button>
                    
                    {isStyleDrawerOpen && (
                      <div className="space-y-2 p-3 border border-border rounded-md bg-muted">
                        <Label htmlFor="writing-style" className="text-sm">Custom Writing Style (Optional)</Label>
                        <Textarea
                          id="writing-style"
                          placeholder="e.g., Write in a conversational tone with personal anecdotes, use emojis sparingly, include actionable insights..."
                          value={writingStyle}
                          onChange={(e) => setWritingStyle(e.target.value)}
                          className="min-h-[100px] bg-background text-foreground border-border focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-0 focus-visible:border-blue-500 focus-visible:outline-none"
                        />
                        <p className="text-xs text-muted-foreground">
                          Describe your preferred writing style, tone, and any specific requirements. This will be saved automatically.
                        </p>
                      </div>
                    )}
                  </div>
                  
                  <div className="space-y-1">
                    <Label htmlFor="ai-topic" className="text-sm">Content Ideas & Details</Label>
                    <Textarea
                      id="ai-topic"
                      placeholder="Share your content ideas, main points, experiences, or insights you'd like to cover. The AI will expand on your ideas to create engaging content."
                      value={aiAgentTopic}
                      onChange={(e) => setAiAgentTopic(e.target.value)}
                      rows={6}
                      className="resize-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-0 focus-visible:border-blue-500 focus-visible:outline-none"
                    />
                  </div>
                  <Button 
                    onClick={handleStartAiAgent}
                    disabled={isAiGenerating}
                    className="w-full flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    {isAiGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {isAiGenerating ? 'Starting Content Loop...' : 'Start Content Loop'}
                  </Button>
                </div>
              ) : (
                // Active session - Input controls
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label className="text-sm">Session Status:</Label>
                      <span className={`text-xs px-2 py-1 rounded ${
                        sessionStatus === 'waiting_feedback' 
                          ? 'bg-yellow-100 text-yellow-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {sessionStatus === 'waiting_feedback' ? 'Waiting for Feedback' : 'Completed'}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Session ID: {sessionId.slice(0, 8)}...
                    </div>
                  </div>

                  {/* Feedback input */}
                  {sessionStatus === 'waiting_feedback' && (
                    <div className="space-y-2">
                      <Label htmlFor="feedback" className="text-sm">Your Feedback</Label>
                      <Textarea
                        id="feedback"
                        placeholder="Provide feedback to improve the content, or type 'done' to finish... (Press Enter to send, Shift+Enter for new line)"
                        value={feedbackInput}
                        onChange={(e) => setFeedbackInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="min-h-[200px] focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-0 focus-visible:border-blue-500 focus-visible:outline-none"
                      />
                      <Button 
                        onClick={handleProvideFeedback}
                        disabled={isAiGenerating}
                        className="w-full flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white"
                      >
                        {isAiGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                        {isAiGenerating ? 'Processing...' : 'Send Feedback'}
                      </Button>
                    </div>
                  )}

                  {sessionStatus === 'completed' && (
                    <div className="p-3 rounded-md bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                      <div className="text-sm text-green-800 dark:text-green-200">
                        ✅ Session completed! Content has been finalized.
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
            </Card>

            {/* AI Agent Output Section */}
            <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Generated Content</h3>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleOptimizeContent}
                    disabled={!aiGeneratedContent || isAnalyzing}
                    className="flex items-center gap-2 hover:bg-green-50 hover:border-green-300 transition-colors cursor-pointer"
                  >
                    {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4 text-green-600" />}
                    {isAnalyzing ? 'Analyzing...' : 'Optimize'}
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleCopy}
                    disabled={!aiGeneratedContent}
                    className="flex items-center gap-2 hover:bg-blue-50 hover:border-blue-300 transition-colors cursor-pointer"
                  >
                    <Copy className="h-4 w-4 text-blue-600" />
                    {copyButtonText}
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleClear}
                    disabled={!aiGeneratedContent}
                    className="flex items-center gap-2 hover:bg-red-50 hover:border-red-300 transition-colors cursor-pointer"
                  >
                    <X className="h-4 w-4 text-red-600" />
                    {clearButtonText}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 rounded-md border bg-card h-[400px] overflow-hidden">
                <Textarea
                  value={aiGeneratedContent}
                  placeholder="Generated content will appear here..."
                  readOnly
                  className="border-none shadow-none p-0 text-sm leading-6 resize-none w-full h-full overflow-y-auto focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-0 focus-visible:border-blue-500 focus-visible:outline-none"
                />
              </div>

              {/* Optimization Suggestions Panel */}
              {optimizationData && (
                <div className="space-y-3">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setIsOptimizationOpen(!isOptimizationOpen)}
                    className="w-full justify-between h-auto p-3 hover:bg-accent hover:text-accent-foreground border border-border rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-medium">Optimization Suggestions</span>
                      <div className="flex items-center gap-1">
                        <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                        <span className="text-xs text-green-600">Score: {optimizationData.overall_score}/100</span>
                      </div>
                    </div>
                    {isOptimizationOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </Button>
                  
                  {isOptimizationOpen && (
                    <div className="space-y-4 p-4 border border-border rounded-md bg-muted">
                      {/* Hashtag Suggestions */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Hash className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-medium">Suggested Hashtags</span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {optimizationData.hashtags?.suggested?.map((hashtag: string, index: number) => (
                            <span key={index} className="text-xs bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                              {hashtag}
                            </span>
                          ))}
                        </div>
                        <p className="text-xs text-muted-foreground">{optimizationData.hashtags?.reasoning}</p>
                      </div>

                      {/* Call-to-Action Improvements */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4 text-orange-600" />
                          <span className="text-sm font-medium">Call-to-Action</span>
                        </div>
                        <div className="p-2 bg-background rounded border">
                          <p className="text-xs font-medium text-muted-foreground mb-1">Improved CTA:</p>
                          <p className="text-sm">{optimizationData.call_to_action?.improved_cta}</p>
                        </div>
                        {optimizationData.call_to_action?.alternatives && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-muted-foreground">Alternatives:</p>
                            {optimizationData.call_to_action.alternatives.map((alt: string, index: number) => (
                              <p key={index} className="text-xs text-muted-foreground">• {alt}</p>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Key Recommendations */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Target className="h-4 w-4 text-green-600" />
                          <span className="text-sm font-medium">Top Recommendations</span>
                        </div>
                        <div className="space-y-1">
                          {optimizationData.key_recommendations?.map((rec: string, index: number) => (
                            <div key={index} className="flex items-start gap-2">
                              <span className="text-xs text-green-600 mt-1">•</span>
                              <p className="text-xs text-muted-foreground">{rec}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Engagement Score */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Engagement Prediction</span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            optimizationData.engagement_optimization?.predicted_engagement === 'High' 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300'
                              : optimizationData.engagement_optimization?.predicted_engagement === 'Medium'
                              ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
                              : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
                          }`}>
                            {optimizationData.engagement_optimization?.predicted_engagement}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
            </Card>
          </div>
        </div>
      </main>
      <Toaster />
    </div>
  )
}

export default App
