from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from typing import Dict, List, Any
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize the same LLM as the main conversation agent
def create_llm():
    provider = os.getenv("LLM_PROVIDER", "google_genai")
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    return init_chat_model(
        model=model,
        model_provider=provider,
        temperature=temperature
    )

llm = create_llm()

class OptimizationAgent:
    """
    Content Optimization Agent with Human-in-the-Loop
    
    Analyzes generated content and provides:
    - Hashtag suggestions
    - CTA improvements  
    - Engagement optimization
    - Structure analysis
    """
    
    def __init__(self):
        self.system_prompt = """You are a content optimization expert specializing in human-in-the-loop feedback systems. 
        Your job is to analyze content posts and provide specific, actionable suggestions 
        to maximize engagement, reach, and professional impact.
        
        Focus on:
        - Hashtag strategy (trending, relevant, mix of popular/niche)
        - Call-to-action effectiveness 
        - Content structure and readability
        - Engagement triggers and hooks
        - Professional tone optimization
        """

    async def optimize_content(
        self, 
        content: str, 
        topic: str = "", 
        content_length: str = "medium",
        industry: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze content and return optimization suggestions
        """
        
        analysis_prompt = f"""
        Analyze this content post and provide optimization suggestions:

        CONTENT TO ANALYZE:
        {content}

        CONTEXT:
        - Topic: {topic}
        - Length: {content_length}
        - Industry: {industry}

        PROVIDE ANALYSIS IN THIS EXACT JSON FORMAT:
        {{
            "hashtags": {{
                "suggested": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"],
                "reasoning": "Brief explanation of hashtag strategy"
            }},
            "call_to_action": {{
                "current_cta": "Current CTA from the content or 'None found'",
                "improved_cta": "Specific improved CTA suggestion",
                "alternatives": ["Alternative CTA 1", "Alternative CTA 2", "Alternative CTA 3"]
            }},
            "structure_analysis": {{
                "readability_score": "Good/Average/Poor",
                "paragraph_count": 0,
                "hook_effectiveness": "Strong/Moderate/Weak",
                "suggestions": ["Specific structural improvement 1", "Improvement 2"]
            }},
            "engagement_optimization": {{
                "predicted_engagement": "High/Medium/Low",
                "engagement_triggers": ["Trigger 1", "Trigger 2", "Trigger 3"],
                "improvements": ["Specific engagement improvement 1", "Improvement 2"]
            }},
            "overall_score": 85,
            "key_recommendations": ["Top recommendation 1", "Top recommendation 2", "Top recommendation 3"]
        }}

        Be specific and actionable in all suggestions. Focus on content best practices for professional platforms.
        """

        try:
            response = llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=analysis_prompt)
            ])
            
            # Extract JSON from response
            content_text = response.content
            
            # Try to parse JSON from the response
            json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                optimization_data = json.loads(json_str)
            else:
                # Fallback if JSON parsing fails
                optimization_data = self._create_fallback_optimization(content, topic)
                
            return optimization_data
            
        except Exception as e:
            print(f"Error in optimization analysis: {e}")
            return self._create_fallback_optimization(content, topic)

    def _create_fallback_optimization(self, content: str, topic: str) -> Dict[str, Any]:
        """Create basic optimization suggestions if main analysis fails"""
        
        # Extract basic hashtags from topic
        words = topic.lower().split() if topic else ["content", "professional"]
        hashtags = [f"#{word.replace(' ', '').capitalize()}" for word in words[:3]]
        hashtags.extend(["#Content", "#ProfessionalGrowth"])
        
        return {
            "hashtags": {
                "suggested": hashtags[:5],
                "reasoning": "Basic hashtag suggestions based on content topic"
            },
            "call_to_action": {
                "current_cta": "None detected",
                "improved_cta": "What are your thoughts on this topic? Share your experience below!",
                "alternatives": [
                    "How has this impacted your professional journey?",
                    "What strategies have worked for you?",
                    "I'd love to hear your perspective in the comments!"
                ]
            },
            "structure_analysis": {
                "readability_score": "Good",
                "paragraph_count": len(content.split('\n\n')),
                "hook_effectiveness": "Moderate",
                "suggestions": [
                    "Consider starting with a compelling question or statistic",
                    "Use bullet points or numbered lists for better readability"
                ]
            },
            "engagement_optimization": {
                "predicted_engagement": "Medium",
                "engagement_triggers": ["Personal experience", "Industry insights", "Call to action"],
                "improvements": [
                    "Add a personal anecdote or example",
                    "Include a thought-provoking question"
                ]
            },
            "overall_score": 75,
            "key_recommendations": [
                "Enhance with relevant hashtags",
                "Strengthen the call-to-action",
                "Add personal examples for authenticity"
            ]
        }

    async def suggest_hashtags_only(self, content: str, topic: str = "", count: int = 8) -> List[str]:
        """Quick hashtag-only analysis for simpler use cases"""
        
        hashtag_prompt = f"""
        Content: {content}
        Topic: {topic}
        
        Suggest {count} highly relevant hashtags for this content.
        Mix popular hashtags (high reach) with niche ones (targeted audience).
        
        Return ONLY the hashtags in this format:
        #Hashtag1, #Hashtag2, #Hashtag3, etc.
        """
        
        try:
            response = llm.invoke([
                SystemMessage(content="You are a content hashtag expert."),
                HumanMessage(content=hashtag_prompt)
            ])
            
            # Extract hashtags from response
            hashtags = re.findall(r'#\w+', response.content)
            return hashtags[:count] if hashtags else ["#Content", "#Professional", "#Growth"]
            
        except Exception as e:
            print(f"Error in hashtag generation: {e}")
            return ["#Content", "#Professional", "#Growth", "#Success", "#Business"]

# Global instance
optimization_agent = OptimizationAgent()

# FastAPI Application
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import asyncio
import uuid
from datetime import datetime, timedelta
from conversation import app as conversation_app
from langgraph.types import Command

def cleanup_expired_sessions():
    """Remove sessions that have been inactive for too long"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in active_sessions.items():
        last_activity = session_data.get("last_activity", session_data.get("created_at"))
        if current_time - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        print(f"Cleaning up expired session: {session_id}")
        del active_sessions[session_id]
    
    return len(expired_sessions)

async def periodic_cleanup():
    """Background task to periodically clean up expired sessions"""
    while True:
        try:
            cleaned_count = cleanup_expired_sessions()
            if cleaned_count > 0:
                print(f"Cleaned up {cleaned_count} expired sessions")
        except Exception as e:
            print(f"Error during session cleanup: {e}")
        
        # Wait 10 minutes before next cleanup
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting ContentLoop AI...")
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    print("Shutting down ContentLoop AI...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

# Store active AI agent sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

# Session timeout in minutes
SESSION_TIMEOUT_MINUTES = 5

app = FastAPI(title="ContentLoop AI", version="1.0.0", lifespan=lifespan)

# Configure CORS to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class AIAgentStartRequest(BaseModel):
    topic: str
    content_length: str = "medium"
    writing_style: str = ""

class AIAgentFeedbackRequest(BaseModel):
    session_id: str
    feedback: str

class OptimizationRequest(BaseModel):
    content: str
    topic: str = ""
    content_length: str = "medium"
    industry: str = "general"

# Response models
class AIAgentResponse(BaseModel):
    session_id: str
    generated_post: str
    status: str  # "waiting_feedback", "completed"
    success: bool
    message: Optional[str] = None

class AIAgentFeedbackResponse(BaseModel):
    session_id: str
    generated_post: Optional[str] = None
    status: str  # "waiting_feedback", "completed"
    success: bool
    message: Optional[str] = None

class OptimizationResponse(BaseModel):
    optimization_data: Dict[str, Any]
    success: bool
    message: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ContentLoop AI is running", "status": "healthy"}

@app.post("/api/ai-agent/start", response_model=AIAgentResponse)
async def start_ai_agent_session(request: AIAgentStartRequest):
    """Start a new AI agent session for human-in-the-loop content generation"""
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create thread config for this session
        thread_config = {"configurable": {"thread_id": session_id}}
        
        # Initial state
        initial_state = {
            "topic": request.topic,
            "content_length": request.content_length,
            "writing_style": request.writing_style,
            "generated_post": [],
            "human_feedback": []
        }
        
        # Start the conversation app
        generated_post = ""
        
        for chunk in conversation_app.stream(initial_state, config=thread_config):
            for node_id, value in chunk.items():

                if node_id == "__interrupt__":
                    # Extract the generated post from the interrupt data
                    if "generated_post" in value and value["generated_post"]:
                        generated_post = value["generated_post"][-1].content if hasattr(value["generated_post"][-1], 'content') else str(value["generated_post"][-1])
                    break
                elif node_id == "model" and "generated_post" in value:
                    # Store the generated post
                    if value["generated_post"]:
                        generated_post = value["generated_post"][-1].content if hasattr(value["generated_post"][-1], 'content') else str(value["generated_post"][-1])
        
        # Store session data
        active_sessions[session_id] = {
            "thread_config": thread_config,
            "state": initial_state,
            "current_post": generated_post,
            "status": "waiting_feedback",
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        return AIAgentResponse(
            session_id=session_id,
            generated_post=generated_post,
            status="waiting_feedback",
            success=True,
            message="AI agent session started. Content generated, waiting for feedback."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting AI agent session: {str(e)}")

@app.post("/api/ai-agent/feedback", response_model=AIAgentFeedbackResponse)
async def provide_ai_agent_feedback(request: AIAgentFeedbackRequest):
    """Provide feedback to the AI agent and continue the conversation"""
    try:
        session_id = request.session_id
        feedback = request.feedback
        
        # Check if session exists
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = active_sessions[session_id]
        thread_config = session_data["thread_config"]
        
        # Check if user wants to finish
        if feedback.lower() == "done":
            # Mark session as completed
            active_sessions[session_id]["status"] = "completed"
            
            return AIAgentFeedbackResponse(
                session_id=session_id,
                generated_post=session_data["current_post"],
                status="completed",
                success=True,
                message="Content finalized successfully!"
            )
        
        # Resume the conversation app with feedback
        generated_post = ""
        
        # Resume with the user's feedback
        for chunk in conversation_app.stream(Command(resume=feedback), config=thread_config):
            for node_id, value in chunk.items():
                if node_id == "__interrupt__":
                    # Extract the newly generated post from the interrupt data
                    if "generated_post" in value and value["generated_post"]:
                        generated_post = value["generated_post"][-1].content if hasattr(value["generated_post"][-1], 'content') else str(value["generated_post"][-1])
                    break
                elif node_id == "model" and "generated_post" in value:
                    # Store the generated post
                    if value["generated_post"]:
                        generated_post = value["generated_post"][-1].content if hasattr(value["generated_post"][-1], 'content') else str(value["generated_post"][-1])
        
        # Update session data
        active_sessions[session_id]["current_post"] = generated_post
        active_sessions[session_id]["last_activity"] = datetime.now()
        
        return AIAgentFeedbackResponse(
            session_id=session_id,
            generated_post=generated_post,
            status="waiting_feedback",
            success=True,
            message="Feedback processed. New content generated, waiting for more feedback."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing feedback: {str(e)}")

@app.get("/api/ai-agent/session/{session_id}")
async def get_ai_agent_session(session_id: str):
    """Get the current state of an AI agent session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    
    return {
        "session_id": session_id,
        "generated_post": session_data["current_post"],
        "status": session_data["status"],
        "success": True
    }

@app.delete("/api/ai-agent/session/{session_id}")
async def delete_ai_agent_session(session_id: str):
    """Delete an AI agent session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del active_sessions[session_id]
    
    return {
        "success": True,
        "message": "Session deleted successfully"
    }

@app.get("/api/ai-agent/sessions/stats")
async def get_session_stats():
    """Get statistics about active sessions"""
    current_time = datetime.now()
    total_sessions = len(active_sessions)
    expired_sessions = 0
    
    for session_data in active_sessions.values():
        last_activity = session_data.get("last_activity", session_data.get("created_at"))
        if current_time - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            expired_sessions += 1
    
    return {
        "total_active_sessions": total_sessions,
        "expired_sessions": expired_sessions,
        "healthy_sessions": total_sessions - expired_sessions,
        "session_timeout_minutes": SESSION_TIMEOUT_MINUTES
    }

@app.post("/api/ai-agent/sessions/cleanup")
async def manual_cleanup_sessions():
    """Manually trigger cleanup of expired sessions"""
    cleaned_count = cleanup_expired_sessions()
    
    return {
        "success": True,
        "message": f"Cleanup completed. Removed {cleaned_count} expired sessions.",
        "cleaned_sessions": cleaned_count
    }

@app.post("/api/optimization/analyze", response_model=OptimizationResponse)
async def analyze_content_optimization(request: OptimizationRequest):
    """Analyze content and provide optimization suggestions"""
    
    try:
        optimization_data = await optimization_agent.optimize_content(
            content=request.content,
            topic=request.topic,
            content_length=request.content_length,
            industry=request.industry
        )
        
        return OptimizationResponse(
            optimization_data=optimization_data,
            success=True,
            message="Content analysis completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing content: {str(e)}")

@app.post("/api/optimization/hashtags")
async def suggest_hashtags_only(request: OptimizationRequest):
    """Get hashtag suggestions only (faster endpoint)"""
    try:
        hashtags = await optimization_agent.suggest_hashtags_only(
            content=request.content,
            topic=request.topic,
            count=8
        )
        
        return {
            "hashtags": hashtags,
            "success": True,
            "message": "Hashtag suggestions generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating hashtags: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)