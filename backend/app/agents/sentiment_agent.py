import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import httpx
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.mcp.agent_registry import AgentCapability
from app.utils.helpers import get_kafka_consumer, get_kafka_producer
from app.integrations.groq_ai_interface import generate_structured_output

# Constants
AGENT_NAME = "sentiment_agent"
AGENT_DESCRIPTION = "Analyzes user feedback and sentiment to adjust AR scene parameters or conversation tone"
TOPIC_SENTIMENT_ANALYSIS = "sentiment-analysis"
TOPIC_CONTEXT_UPDATE = "context-update"

# Models
class SentimentAnalysis(BaseModel):
    """Result of sentiment analysis"""
    sentiment: str  # positive, negative, neutral
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    emotions: Dict[str, float] = Field(default_factory=dict)  # emotion -> intensity
    topics: Dict[str, float] = Field(default_factory=dict)  # topic -> relevance
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EngagementMetrics(BaseModel):
    """User engagement metrics"""
    interest_level: float  # 0.0 to 1.0
    satisfaction: float  # 0.0 to 1.0
    confusion: float  # 0.0 to 1.0
    attention: float  # 0.0 to 1.0
    engagement_score: float  # 0.0 to 1.0
    frustration: float  # 0.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ARSceneAdjustment(BaseModel):
    """Adjustments to AR scene based on sentiment"""
    scene_id: str
    adjustments: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    sentiment_source: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConversationAdjustment(BaseModel):
    """Adjustments to conversation tone based on sentiment"""
    context_id: str
    tone_shift: str  # more_empathetic, more_informative, more_encouraging, etc.
    formality_level: Optional[float] = None  # 0.0 (casual) to 1.0 (formal)
    pace: Optional[str] = None  # slower, faster, unchanged
    complexity: Optional[str] = None  # simpler, more_detailed, unchanged
    rationale: str
    sentiment_source: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Sentiment analysis schema for structured output
SENTIMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral"],
            "description": "The overall sentiment of the text"
        },
        "score": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Sentiment score from -1.0 (very negative) to 1.0 (very positive)"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in the sentiment analysis"
        },
        "emotions": {
            "type": "object",
            "description": "Map of emotions detected and their intensity",
            "additionalProperties": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0
            }
        },
        "topics": {
            "type": "object",
            "description": "Map of topics detected and their relevance",
            "additionalProperties": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0
            }
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The entity text"
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of entity"
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"],
                        "description": "The sentiment specifically for this entity"
                    }
                },
                "required": ["text", "type"]
            },
            "description": "Entities mentioned in the text and their sentiment"
        }
    },
    "required": ["sentiment", "score", "confidence"]
}

# Engagement metrics schema for structured output
ENGAGEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "interest_level": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "User's level of interest in the content"
        },
        "satisfaction": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "User's satisfaction with the content or experience"
        },
        "confusion": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Level of confusion detected in user's response"
        },
        "attention": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "User's level of attention to the content"
        },
        "engagement_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Overall engagement score"
        },
        "frustration": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Level of frustration detected in user's response"
        }
    },
    "required": ["interest_level", "satisfaction", "confusion", "engagement_score"]
}

# Prompt templates
SENTIMENT_PROMPT_TEMPLATE = """
Analyze the sentiment, emotions, and topics in the following text:

TEXT: {text}

Provide a detailed sentiment analysis including:
1. Overall sentiment (positive, negative, or neutral)
2. A score from -1.0 (very negative) to 1.0 (very positive)
3. Key emotions detected and their intensity (0.0 to 1.0)
4. Main topics mentioned and their relevance
5. Named entities and their associated sentiment
6. Confidence in your analysis

Focus on AR experience specific feedback, user satisfaction, and usability issues.
"""

ENGAGEMENT_PROMPT_TEMPLATE = """
Analyze the user's engagement level in the following interaction:

TEXT: {text}

CONTEXT: {context}

Provide metrics on:
1. Interest level (0.0 to 1.0)
2. Satisfaction (0.0 to 1.0)
3. Confusion (0.0 to 1.0)
4. Attention (0.0 to 1.0)
5. Overall engagement score (0.0 to 1.0)
6. Frustration level (0.0 to 1.0)

Consider indicators like question frequency, depth of inquiries, enthusiasm markers, and signs of disengagement.
"""

SCENE_ADJUSTMENT_PROMPT_TEMPLATE = """
Based on the sentiment analysis and engagement metrics, suggest adjustments to the AR scene with ID {scene_id}.

SENTIMENT ANALYSIS: {sentiment_json}

ENGAGEMENT METRICS: {engagement_json}

CURRENT SCENE PARAMETERS: {scene_params_json}

Suggest specific adjustments to the scene parameters that would improve the user experience based on the detected sentiment and engagement. 
Include adjustments to lighting, colors, object positioning, effects, or other parameters that could enhance the emotional impact or address issues.

Provide a brief rationale for each adjustment.
"""

CONVERSATION_ADJUSTMENT_PROMPT_TEMPLATE = """
Based on the sentiment analysis and engagement metrics, suggest adjustments to the conversation tone.

SENTIMENT ANALYSIS: {sentiment_json}

ENGAGEMENT METRICS: {engagement_json}

CONVERSATION HISTORY: {conversation_history}

Suggest specific adjustments to the conversation approach that would improve the user experience based on the detected sentiment and engagement.
Specify tone shifts, formality level, pace, and complexity adjustments that would better engage the user and address any issues.

Provide a brief rationale for each adjustment.
"""

class SentimentAgent:
    """Agent that analyzes user feedback and adjusts AR scene parameters or conversation tone"""
    
    def __init__(self):
        self.agent_id = None
        self.kafka_producer = get_kafka_producer()
        self.kafka_consumer = None
        self.consumer_task = None
        self.is_running = False
        
        # Define capabilities
        self.capabilities = [
            AgentCapability(
                name="sentiment_analysis",
                description="Analyzes user feedback for sentiment and emotions",
                parameters={
                    "text": "The text to analyze",
                    "context_id": "Optional context ID for multi-turn conversations",
                    "user_id": "The user ID"
                },
                example={
                    "text": "I really like how the AR objects interact with my environment",
                    "context_id": "ctx_12345",
                    "user_id": "user_12345"
                }
            ),
            AgentCapability(
                name="scene_adjustment",
                description="Suggests AR scene adjustments based on sentiment",
                parameters={
                    "sentiment": "Sentiment analysis results",
                    "scene_id": "The scene ID to adjust",
                    "scene_params": "Current scene parameters"
                },
                example={
                    "sentiment": {"sentiment": "positive", "score": 0.8},
                    "scene_id": "scene_12345",
                    "scene_params": {"lighting": "bright", "colors": ["blue", "green"]}
                }
            ),
            AgentCapability(
                name="conversation_adjustment",
                description="Suggests conversation tone adjustments based on sentiment",
                parameters={
                    "sentiment": "Sentiment analysis results",
                    "context_id": "Context ID for the conversation",
                    "conversation_history": "Recent conversation history"
                },
                example={
                    "sentiment": {"sentiment": "negative", "score": -0.5},
                    "context_id": "ctx_12345",
                    "conversation_history": ["User: How do I move objects?", "System: Tap and drag."]
                }
            )
        ]
    
    async def start(self):
        """Start the agent, register with MCP, and begin consuming messages"""
        # Register with MCP server
        await self.register_with_mcp()
        
        # Start Kafka consumer
        self.is_running = True
        self.consumer_task = asyncio.create_task(self.consume_messages())
        
        logger.info(f"{AGENT_NAME} started with agent_id: {self.agent_id}")
    
    async def stop(self):
        """Stop the agent and clean up resources"""
        self.is_running = False
        
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.kafka_consumer:
            self.kafka_consumer.close()
        
        # Unregister from MCP
        await self.unregister_from_mcp()
        
        logger.info(f"{AGENT_NAME} stopped")
    
    async def register_with_mcp(self):
        """Register the agent with the MCP server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/agent/register",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={
                        "name": AGENT_NAME,
                        "description": AGENT_DESCRIPTION,
                        "capabilities": [capability.dict() for capability in self.capabilities],
                        "metadata": {
                            "version": "1.0.0",
                            "supported_emotions": ["joy", "anger", "sadness", "fear", "surprise"]
                        }
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.agent_id = data.get("agent_id")
                    logger.info(f"Registered with MCP server, agent_id: {self.agent_id}")
                else:
                    logger.error(f"Failed to register with MCP server: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error registering with MCP server: {e}")
    
    async def unregister_from_mcp(self):
        """Unregister the agent from the MCP server"""
        if not self.agent_id:
            return
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/agent/unregister",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={"agent_id": self.agent_id},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Unregistered from MCP server, agent_id: {self.agent_id}")
                else:
                    logger.error(f"Failed to unregister from MCP server: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error unregistering from MCP server: {e}")
    
    async def consume_messages(self):
        """Consume messages from Kafka topic"""
        self.kafka_consumer = get_kafka_consumer([TOPIC_SENTIMENT_ANALYSIS])
        
        try:
            while self.is_running:
                msg = self.kafka_consumer.poll(1.0)
                
                if msg is None:
                    await asyncio.sleep(0.1)
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    # Process the message
                    value = msg.value().decode("utf-8")
                    message = json.loads(value)
                    logger.info(f"Received message: {message.get('request_id')}")
                    
                    # Process in a separate task to not block the consumer
                    asyncio.create_task(self.process_message(message))
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        finally:
            self.kafka_consumer.close()
    
    async def process_message(self, message: Dict[str, Any]):
        """Process a sentiment analysis message"""
        request_id = message.get("request_id")
        user_id = message.get("user_id")
        context_id = message.get("context_id", user_id)
        text = message.get("text", "")
        
        if not text:
            logger.warning(f"Received empty text for request {request_id}")
            await self.send_result(request_id, user_id, {
                "error": "No text provided for sentiment analysis"
            })
            return
        
        try:
            # Get conversation context
            context = await self.get_conversation_context(context_id)
            
            # Analyze sentiment and engagement
            sentiment, engagement = await self.analyze_sentiment_and_engagement(text, context)
            
            # Get current AR scene if available
            current_scene_id = context.get("current_scene_id")
            scene_params = {}
            if current_scene_id:
                scene_params = await self.get_scene_parameters(current_scene_id)
            
            # Generate adjustments based on analysis
            scene_adjustment = None
            conversation_adjustment = None
            
            if current_scene_id and scene_params:
                scene_adjustment = await self.generate_scene_adjustment(
                    sentiment, 
                    engagement, 
                    current_scene_id, 
                    scene_params
                )
            
            if context.get("conversation_history"):
                conversation_adjustment = await self.generate_conversation_adjustment(
                    sentiment, 
                    engagement, 
                    context_id, 
                    context.get("conversation_history", [])
                )
            
            # Update context with sentiment information
            await self.update_context_with_sentiment(
                context_id, 
                sentiment, 
                engagement,
                scene_adjustment,
                conversation_adjustment
            )
            
            # Send the result
            await self.send_result(request_id, user_id, {
                "sentiment": sentiment.dict(),
                "engagement_metrics": engagement.dict(),
                "scene_adjustment": scene_adjustment.dict() if scene_adjustment else None,
                "conversation_adjustment": conversation_adjustment.dict() if conversation_adjustment else None
            })
            
            logger.info(f"Processed sentiment analysis for request {request_id}")
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            await self.send_result(request_id, user_id, {
                "error": f"Error in sentiment analysis: {str(e)}"
            })
    
    async def analyze_sentiment_and_engagement(self, text: str, context: Dict[str, Any]) -> Tuple[SentimentAnalysis, EngagementMetrics]:
        """Analyze sentiment and engagement from text and context"""
        # First, analyze sentiment
        sentiment_prompt = SENTIMENT_PROMPT_TEMPLATE.format(text=text)
        sentiment_result = await generate_structured_output(
            prompt=sentiment_prompt,
            system_prompt="You are an expert at sentiment analysis in augmented reality contexts.",
            output_schema=SENTIMENT_SCHEMA,
            temperature=0.1
        )
        
        # Create sentiment analysis object
        sentiment = SentimentAnalysis(
            sentiment=sentiment_result.get("sentiment", "neutral"),
            score=sentiment_result.get("score", 0.0),
            confidence=sentiment_result.get("confidence", 0.5),
            emotions=sentiment_result.get("emotions", {}),
            topics=sentiment_result.get("topics", {}),
            entities=sentiment_result.get("entities", []),
            language=sentiment_result.get("language", "en")
        )
        
        # Then, analyze engagement
        context_str = json.dumps({
            "recent_interactions": context.get("conversation_history", [])[-5:] if context.get("conversation_history") else [],
            "current_scene": context.get("current_scene_name", "Unknown")
        })
        
        engagement_prompt = ENGAGEMENT_PROMPT_TEMPLATE.format(text=text, context=context_str)
        engagement_result = await generate_structured_output(
            prompt=engagement_prompt,
            system_prompt="You are an expert at analyzing user engagement in augmented reality experiences.",
            output_schema=ENGAGEMENT_SCHEMA,
            temperature=0.1
        )
        
        # Create engagement metrics object
        engagement = EngagementMetrics(
            interest_level=engagement_result.get("interest_level", 0.5),
            satisfaction=engagement_result.get("satisfaction", 0.5),
            confusion=engagement_result.get("confusion", 0.0),
            attention=engagement_result.get("attention", 0.5),
            engagement_score=engagement_result.get("engagement_score", 0.5),
            frustration=engagement_result.get("frustration", 0.0)
        )
        
        return sentiment, engagement
    
    async def generate_scene_adjustment(
        self, 
        sentiment: SentimentAnalysis, 
        engagement: EngagementMetrics, 
        scene_id: str, 
        scene_params: Dict[str, Any]
    ) -> Optional[ARSceneAdjustment]:
        """Generate AR scene adjustments based on sentiment and engagement"""
        if not scene_params:
            return None
        
        # Prepare prompt with JSON formatted inputs
        prompt = SCENE_ADJUSTMENT_PROMPT_TEMPLATE.format(
            scene_id=scene_id,
            sentiment_json=json.dumps(sentiment.dict()),
            engagement_json=json.dumps(engagement.dict()),
            scene_params_json=json.dumps(scene_params)
        )
        
        # Define schema for adjustments
        adjustment_schema = {
            "type": "object",
            "properties": {
                "adjustments": {
                    "type": "object",
                    "description": "Specific adjustments to scene parameters",
                    "additionalProperties": True
                },
                "rationale": {
                    "type": "string",
                    "description": "Explanation for the suggested adjustments"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence in the suggested adjustments"
                }
            },
            "required": ["adjustments", "rationale", "confidence"]
        }
        
        # Generate adjustments
        adjustment_result = await generate_structured_output(
            prompt=prompt,
            system_prompt="You are an expert at adjusting AR experiences based on user sentiment.",
            output_schema=adjustment_schema,
            temperature=0.2
        )
        
        # Create adjustment object
        scene_adjustment = ARSceneAdjustment(
            scene_id=scene_id,
            adjustments=adjustment_result.get("adjustments", {}),
            rationale=adjustment_result.get("rationale", "No rationale provided"),
            sentiment_source={
                "sentiment": sentiment.sentiment,
                "score": sentiment.score,
                "top_emotions": {k: v for k, v in sorted(sentiment.emotions.items(), key=lambda item: item[1], reverse=True)[:3]}
            },
            confidence=adjustment_result.get("confidence", 0.5)
        )
        
        return scene_adjustment
    
    async def generate_conversation_adjustment(
        self, 
        sentiment: SentimentAnalysis, 
        engagement: EngagementMetrics, 
        context_id: str, 
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[ConversationAdjustment]:
        """Generate conversation tone adjustments based on sentiment and engagement"""
        if not conversation_history:
            return None
        
        # Format conversation history
        history_str = ""
        for i, entry in enumerate(conversation_history[-5:]):  # Last 5 entries
            if isinstance(entry, dict):
                role = entry.get("role", "unknown")
                text = entry.get("text", "")
                history_str += f"{i+1}. {role.upper()}: {text}\n"
            elif isinstance(entry, str):
                history_str += f"{i+1}. {entry}\n"
        
        # Prepare prompt with JSON formatted inputs
        prompt = CONVERSATION_ADJUSTMENT_PROMPT_TEMPLATE.format(
            sentiment_json=json.dumps(sentiment.dict()),
            engagement_json=json.dumps(engagement.dict()),
            conversation_history=history_str
        )
        
        # Define schema for adjustments
        adjustment_schema = {
            "type": "object",
            "properties": {
                "tone_shift": {
                    "type": "string",
                    "description": "How the conversation tone should shift"
                },
                "formality_level": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Target formality level from casual (0.0) to formal (1.0)"
                },
                "pace": {
                    "type": "string",
                    "enum": ["slower", "faster", "unchanged"],
                    "description": "How to adjust the conversation pace"
                },
                "complexity": {
                    "type": "string",
                    "enum": ["simpler", "more_detailed", "unchanged"],
                    "description": "How to adjust the complexity of responses"
                },
                "rationale": {
                    "type": "string",
                    "description": "Explanation for the suggested adjustments"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Confidence in the suggested adjustments"
                }
            },
            "required": ["tone_shift", "rationale", "confidence"]
        }
        
        # Generate adjustments
        adjustment_result = await generate_structured_output(
            prompt=prompt,
            system_prompt="You are an expert at adjusting conversation tone based on user sentiment.",
            output_schema=adjustment_schema,
            temperature=0.2
        )
        
        # Create adjustment object
        conversation_adjustment = ConversationAdjustment(
            context_id=context_id,
            tone_shift=adjustment_result.get("tone_shift", "unchanged"),
            formality_level=adjustment_result.get("formality_level"),
            pace=adjustment_result.get("pace"),
            complexity=adjustment_result.get("complexity"),
            rationale=adjustment_result.get("rationale", "No rationale provided"),
            sentiment_source={
                "sentiment": sentiment.sentiment,
                "score": sentiment.score,
                "confusion": engagement.confusion,
                "frustration": engagement.frustration
            },
            confidence=adjustment_result.get("confidence", 0.5)
        )
        
        return conversation_adjustment
    
    async def get_conversation_context(self, context_id: str) -> Dict[str, Any]:
        """Get conversation context from the Context Agent"""
        # In a real implementation, this would call the Context Agent's API
        # For simplicity, we'll simulate a context response
        
        try:
            # Make a request to the MCP server
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/context/get",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={
                        "context_id": context_id,
                        "request_id": str(uuid.uuid4())
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("context", {})
                else:
                    logger.error(f"Failed to get context: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return {}
    
    async def get_scene_parameters(self, scene_id: str) -> Dict[str, Any]:
        """Get scene parameters for a scene ID"""
        # In a real implementation, this would call an API to get scene parameters
        # For simplicity, we'll simulate a scene parameters response
        
        try:
            # Make a request to the MCP server
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/api/v1/scene/get",
                    headers={"X-MCP-API-Key": settings.MCP_SECRET},
                    json={
                        "scene_id": scene_id,
                        "request_id": str(uuid.uuid4())
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("scene_params", {})
                else:
                    logger.error(f"Failed to get scene parameters: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting scene parameters: {e}")
            return {}
    
    async def update_context_with_sentiment(
        self, 
        context_id: str, 
        sentiment: SentimentAnalysis, 
        engagement: EngagementMetrics,
        scene_adjustment: Optional[ARSceneAdjustment] = None,
        conversation_adjustment: Optional[ConversationAdjustment] = None
    ):
        """Update context with sentiment analysis results"""
        # Prepare context update
        context_update = {
            "last_sentiment": {
                "sentiment": sentiment.sentiment,
                "score": sentiment.score,
                "timestamp": sentiment.timestamp.isoformat(),
                "top_emotions": {k: v for k, v in sorted(sentiment.emotions.items(), key=lambda item: item[1], reverse=True)[:3]},
                "top_topics": {k: v for k, v in sorted(sentiment.topics.items(), key=lambda item: item[1], reverse=True)[:3]}
            },
            "engagement_metrics": {
                "engagement_score": engagement.engagement_score,
                "interest_level": engagement.interest_level,
                "satisfaction": engagement.satisfaction,
                "confusion": engagement.confusion,
                "timestamp": engagement.timestamp.isoformat()
            }
        }
        
        # Add adjustment information if available
        if scene_adjustment:
            context_update["scene_adjustment_recommendation"] = {
                "scene_id": scene_adjustment.scene_id,
                "adjustments": scene_adjustment.adjustments,
                "rationale": scene_adjustment.rationale,
                "timestamp": scene_adjustment.timestamp.isoformat()
            }
        
        if conversation_adjustment:
            context_update["conversation_adjustment_recommendation"] = {
                "tone_shift": conversation_adjustment.tone_shift,
                "formality_level": conversation_adjustment.formality_level,
                "pace": conversation_adjustment.pace,
                "complexity": conversation_adjustment.complexity,
                "rationale": conversation_adjustment.rationale,
                "timestamp": conversation_adjustment.timestamp.isoformat()
            }
        
        # Send context update to Kafka
        message = {
            "request_id": str(uuid.uuid4()),
            "user_id": context_id,  # Usually context_id is user_id
            "context_id": context_id,
            "context_data": context_update,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.kafka_producer.produce(
            f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_CONTEXT_UPDATE}",
            json.dumps(message).encode("utf-8")
        )
        self.kafka_producer.flush()
        
        logger.debug(f"Updated context {context_id} with sentiment information")
    
    async def send_result(self, request_id: str, user_id: str, result: Dict[str, Any]):
        """Send the sentiment analysis result back through Kafka"""
        # Prepare result message
        message = {
            "request_id": request_id,
            "user_id": user_id,
            "result_type": "sentiment_analysis",
            "timestamp": datetime.utcnow().isoformat(),
            **result
        }
        
        # Send to Kafka
        self.kafka_producer.produce(
            f"{settings.KAFKA_TOPIC_PREFIX}{TOPIC_SENTIMENT_ANALYSIS}-results",
            json.dumps(message).encode("utf-8")
        )
        self.kafka_producer.flush()
        
        logger.debug(f"Sent sentiment analysis result for request {request_id}")

# Create singleton instance
sentiment_agent = SentimentAgent()

# Function to start the agent
async def start_agent():
    await sentiment_agent.start()

# Function to stop the agent
async def stop_agent():
    await sentiment_agent.stop()

# For direct script execution
if __name__ == "__main__":
    import uvloop
    uvloop.install()
    
    async def main():
        await start_agent()
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await stop_agent()
    
    asyncio.run(main())
