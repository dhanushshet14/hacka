from typing import Dict, List, Any, Optional, Callable, Set, Awaitable
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from loguru import logger

class AgentCapability(BaseModel):
    """Model for an agent capability"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    example: Optional[Dict[str, Any]] = None

class RegisteredAgent(BaseModel):
    """Model for a registered agent"""
    agent_id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = Field(default_factory=list)
    status: str = "online"  # online, offline, busy
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentRegistry:
    """Registry for managing agent registrations and capabilities"""
    
    def __init__(self):
        self.agents: Dict[str, RegisteredAgent] = {}
        self.capability_map: Dict[str, Set[str]] = {}  # Map capability names to agent IDs
        
    def register_agent(self, 
                       name: str, 
                       description: str, 
                       capabilities: List[AgentCapability],
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new agent with the registry
        
        Args:
            name: Agent name
            description: Agent description
            capabilities: List of agent capabilities
            metadata: Additional agent metadata
            
        Returns:
            Agent ID
        """
        agent_id = str(uuid.uuid4())
        
        agent = RegisteredAgent(
            agent_id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities,
            metadata=metadata or {}
        )
        
        # Add to agents registry
        self.agents[agent_id] = agent
        
        # Update capability map
        for capability in capabilities:
            if capability.name not in self.capability_map:
                self.capability_map[capability.name] = set()
            self.capability_map[capability.name].add(agent_id)
            
        logger.info(f"Agent registered: {name} with ID {agent_id}")
        return agent_id
    
    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """
        Update an agent's status
        
        Args:
            agent_id: Agent ID
            status: New status (online, offline, busy)
            
        Returns:
            Success status
        """
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].status = status
        self.agents[agent_id].last_heartbeat = datetime.utcnow()
        return True
    
    def update_agent_heartbeat(self, agent_id: str) -> bool:
        """
        Update an agent's heartbeat timestamp
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Success status
        """
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].last_heartbeat = datetime.utcnow()
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Success status
        """
        if agent_id not in self.agents:
            return False
            
        # Remove from capability map
        for capability in self.agents[agent_id].capabilities:
            if capability.name in self.capability_map and agent_id in self.capability_map[capability.name]:
                self.capability_map[capability.name].remove(agent_id)
                
                # Clean up empty sets
                if not self.capability_map[capability.name]:
                    del self.capability_map[capability.name]
        
        # Remove from agents registry
        agent_name = self.agents[agent_id].name
        del self.agents[agent_id]
        
        logger.info(f"Agent unregistered: {agent_name} with ID {agent_id}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[RegisteredAgent]:
        """
        Get agent details by ID
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent details if found, None otherwise
        """
        return self.agents.get(agent_id)
    
    def get_agents_by_capability(self, capability_name: str) -> List[RegisteredAgent]:
        """
        Get all agents with a specific capability
        
        Args:
            capability_name: Capability name
            
        Returns:
            List of agents with the capability
        """
        if capability_name not in self.capability_map:
            return []
            
        return [self.agents[agent_id] for agent_id in self.capability_map[capability_name] 
                if agent_id in self.agents]
    
    def get_all_agents(self) -> List[RegisteredAgent]:
        """
        Get all registered agents
        
        Returns:
            List of all agents
        """
        return list(self.agents.values())
    
    def get_available_capabilities(self) -> List[str]:
        """
        Get all available capabilities across all agents
        
        Returns:
            List of capability names
        """
        return list(self.capability_map.keys())
    
    def find_agent_for_task(self, capability_name: str) -> Optional[str]:
        """
        Find an available agent with the required capability
        
        Args:
            capability_name: Required capability
            
        Returns:
            Agent ID if found, None otherwise
        """
        if capability_name not in self.capability_map:
            return None
            
        # Find online agents with capability
        available_agents = [
            agent_id for agent_id in self.capability_map[capability_name]
            if agent_id in self.agents and self.agents[agent_id].status == "online"
        ]
        
        if not available_agents:
            return None
            
        # Simple scheduling: return the first available agent
        # In a more sophisticated system, this could use load balancing
        return available_agents[0]

# Singleton instance
agent_registry = AgentRegistry() 