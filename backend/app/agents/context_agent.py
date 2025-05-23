import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from loguru import logger
from app.utils.helpers import ContextManager

class ContextAgent:
    """
    Agent for managing context data for AR experiences
    """
    def __init__(self):
        self.contexts = {}
        self.running = False
        self.context_manager = ContextManager()
        self.logger = logger.bind(agent="context")
        
    async def start(self):
        """Start the context agent"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting Context Agent")
        
        # Start background task for context processing
        asyncio.create_task(self.process_contexts())
        
    async def stop(self):
        """Stop the context agent"""
        self.running = False
        self.logger.info("Stopping Context Agent")
        
    async def process_contexts(self):
        """Process contexts and handle expiration"""
        while self.running:
            try:
                # Check for expired contexts
                current_time = time.time()
                expired_contexts = []
                
                for context_id, context_data in self.contexts.items():
                    if context_data.get("expiry_time", 0) < current_time:
                        expired_contexts.append(context_id)
                
                # Remove expired contexts
                for context_id in expired_contexts:
                    self.logger.info(f"Context {context_id} expired, removing")
                    self.contexts.pop(context_id, None)
                    self.context_manager.delete_context(context_id)
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in context processing: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def create_context(self, context_id: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Create a new context
        
        Args:
            context_id: Unique identifier for the context
            data: Context data
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            bool: Success status
        """
        try:
            expiry_time = time.time() + ttl
            context_data = {
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "expiry_time": expiry_time
            }
            
            self.contexts[context_id] = context_data
            self.context_manager.save_context(context_id, context_data, ttl)
            self.logger.info(f"Created context {context_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating context {context_id}: {e}")
            return False
    
    async def update_context(self, context_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Update an existing context
        
        Args:
            context_id: Unique identifier for the context
            data: New or updated context data
            ttl: Optional new TTL in seconds
            
        Returns:
            bool: Success status
        """
        try:
            if context_id not in self.contexts:
                # Try to load from persistent storage
                stored_context = self.context_manager.get_context(context_id)
                if not stored_context:
                    self.logger.warning(f"Context {context_id} not found for update")
                    return False
                self.contexts[context_id] = stored_context
            
            context_data = self.contexts[context_id]
            
            # Update data
            context_data["data"].update(data)
            context_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Update expiry if specified
            if ttl is not None:
                context_data["expiry_time"] = time.time() + ttl
                self.context_manager.update_context(context_id, context_data, ttl)
            else:
                # Calculate remaining TTL
                remaining_ttl = max(1, int(context_data["expiry_time"] - time.time()))
                self.context_manager.update_context(context_id, context_data, remaining_ttl)
            
            self.logger.info(f"Updated context {context_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating context {context_id}: {e}")
            return False
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context data
        
        Args:
            context_id: Unique identifier for the context
            
        Returns:
            Optional[Dict[str, Any]]: Context data if found, None otherwise
        """
        try:
            if context_id in self.contexts:
                return self.contexts[context_id]["data"]
            
            # Try to load from persistent storage
            stored_context = self.context_manager.get_context(context_id)
            if stored_context:
                self.contexts[context_id] = stored_context
                return stored_context["data"]
                
            self.logger.warning(f"Context {context_id} not found")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving context {context_id}: {e}")
            return None
    
    async def delete_context(self, context_id: str) -> bool:
        """
        Delete a context
        
        Args:
            context_id: Unique identifier for the context
            
        Returns:
            bool: Success status
        """
        try:
            if context_id in self.contexts:
                self.contexts.pop(context_id)
                
            # Also remove from persistent storage
            self.context_manager.delete_context(context_id)
            
            self.logger.info(f"Deleted context {context_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting context {context_id}: {e}")
            return False

# Global instance
_context_agent = None

async def init_context_agent():
    """Initialize the context agent"""
    global _context_agent
    if _context_agent is None:
        _context_agent = ContextAgent()
        await _context_agent.start()
    return _context_agent

async def shutdown_context_agent():
    """Shutdown the context agent"""
    global _context_agent
    if _context_agent is not None:
        await _context_agent.stop()
        _context_agent = None
