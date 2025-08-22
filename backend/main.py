from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import asyncio
import uuid
from datetime import datetime, timedelta
from conversation import app as conversation_app
from optimization_agent import optimization_agent
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
            "human_feedback": [],
            "should_continue": True
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
                elif node_id == "content_generator" and "generated_post" in value:
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
                elif node_id == "content_generator" and "generated_post" in value:
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
