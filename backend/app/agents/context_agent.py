import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger("context_agent")
logger.setLevel(logging.INFO)

class ContextAgent:
    """
    Context Agent manages contextual information for AR experiences
    """
    def __init__(self):
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        logger.info("Context Agent initialized")
    
    async def start(self):
        """Start the context agent"""
        self.is_running = True
        logger.info("Context Agent started")
        
        # Start background task
        asyncio.create_task(self._background_task())
        
        return self
    
    async def _background_task(self):
        """Background task for context processing"""
        while self.is_running:
            try:
                # Process contexts
                await self._process_contexts()
                
                # Sleep for a bit
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in context agent background task: {str(e)}")
                await asyncio.sleep(10)  # Sleep longer on error
    
    async def _process_contexts(self):
        """Process all active contexts"""
        # This is a placeholder for actual context processing logic
        for context_id, context in list(self.contexts.items()):
            # Update last processed time
            context["last_processed"] = datetime.utcnow()
            
            # Check if context is expired
            if "expiry" in context and datetime.utcnow() > context["expiry"]:
                logger.info(f"Context {context_id} expired, removing")
                del self.contexts[context_id]
    
    async def create_context(self, user_id: str, ar_experience_id: str, data: Dict[str, Any]) -> str:
        """Create a new context"""
        context_id = f"{user_id}:{ar_experience_id}:{datetime.utcnow().timestamp()}"
        
        self.contexts[context_id] = {
            "user_id": user_id,
            "ar_experience_id": ar_experience_id,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
            "data": data
        }
        
        logger.info(f"Created context {context_id}")
        return context_id
    
    async def update_context(self, context_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing context"""
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found")
            return False
        
        # Update the context data
        self.contexts[context_id]["data"].update(data)
        self.contexts[context_id]["last_updated"] = datetime.utcnow()
        
        logger.info(f"Updated context {context_id}")
        return True
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get a context by ID"""
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found")
            return None
        
        return self.contexts[context_id]
    
    async def delete_context(self, context_id: str) -> bool:
        """Delete a context"""
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found")
            return False
        
        del self.contexts[context_id]
        logger.info(f"Deleted context {context_id}")
        return True
    
    async def stop(self):
        """Stop the context agent"""
        self.is_running = False
        logger.info("Context Agent stopped")

# Global instance
_context_agent: Optional[ContextAgent] = None

async def init_context_agent() -> ContextAgent:
    """Initialize and start the context agent"""
    global _context_agent
    if _context_agent is None:
        _context_agent = ContextAgent()
        await _context_agent.start()
    return _context_agent

async def get_context_agent() -> Optional[ContextAgent]:
    """Get the context agent instance"""
    global _context_agent
    return _context_agent

async def shutdown_context_agent():
    """Shutdown the context agent"""
    global _context_agent
    if _context_agent is not None:
        await _context_agent.stop()
        _context_agent = None
