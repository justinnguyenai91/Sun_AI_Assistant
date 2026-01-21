"""
Context manager for maintaining conversation context across messages.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.models.database import get_db_session
from app.models.conversation import Conversation, Message, SessionContext
from app.cache.redis_cache import cache
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context and session state."""
    
    def __init__(self):
        self.use_db = True
        self.use_cache = True
    
    async def get_or_create_conversation(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        factory_code: Optional[str] = None,
        locale: str = "vi"
    ) -> Optional[int]:
        """Get or create conversation record."""
        try:
            async with get_db_session() as db:
                if db is None:
                    return None
                
                # Try to find existing conversation
                result = await db.execute(
                    select(Conversation).where(Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()
                
                if conversation:
                    # Update timestamp
                    conversation.updated_at = datetime.utcnow()
                    await db.commit()
                    return conversation.id
                
                # Create new conversation
                conversation = Conversation(
                    session_id=session_id,
                    user_id=user_id,
                    factory_code=factory_code,
                    locale=locale
                )
                db.add(conversation)
                await db.flush()
                
                # Create session context
                context = SessionContext(
                    conversation_id=conversation.id,
                    factory_code=factory_code
                )
                db.add(context)
                await db.commit()
                
                logger.info(f"Created new conversation: {conversation.id} for session: {session_id}")
                return conversation.id
                
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return None
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        query_type: Optional[str] = None,
        entity: Optional[str] = None,
        execution_plan: Optional[dict] = None,
        result_rows: Optional[int] = None,
        latency_ms: Optional[int] = None
    ):
        """Save message to database."""
        try:
            async with get_db_session() as db:
                if db is None:
                    return
                
                # Get conversation
                result = await db.execute(
                    select(Conversation).where(Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    logger.warning(f"Conversation not found for session: {session_id}")
                    return
                
                # Create message
                message = Message(
                    conversation_id=conversation.id,
                    role=role,
                    content=content,
                    query_type=query_type,
                    entity=entity,
                    execution_plan=execution_plan,
                    result_rows=result_rows,
                    latency_ms=latency_ms
                )
                db.add(message)
                await db.commit()
                
                logger.debug(f"Saved {role} message for session: {session_id}")
                
        except Exception as e:
            logger.error(f"Error saving message: {e}")
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context (from cache first, then DB)."""
        # Try cache first
        if self.use_cache:
            cached = await cache.get_session_context(session_id)
            if cached:
                logger.debug(f"Context cache HIT for session: {session_id}")
                return cached
        
        # Try database
        try:
            async with get_db_session() as db:
                if db is None:
                    return {}
                
                result = await db.execute(
                    select(Conversation).where(Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation or not conversation.context:
                    return {}
                
                ctx = conversation.context
                context_data = {
                    "factory_code": ctx.factory_code,
                    "factory_codes": ctx.factory_codes or [],
                    "last_time_from": ctx.last_time_from,
                    "last_time_to": ctx.last_time_to,
                    "last_entity": ctx.last_entity,
                    "last_metrics": ctx.last_metrics or [],
                    "last_group_by": ctx.last_group_by or [],
                    "line_codes": ctx.line_codes or [],
                    "model_codes": ctx.model_codes or [],
                    "process_types": ctx.process_types or [],
                }
                
                # Cache it
                if self.use_cache:
                    await cache.set_session_context(session_id, context_data)
                
                logger.debug(f"Context from DB for session: {session_id}")
                return context_data
                
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return {}
    
    async def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Update session context."""
        try:
            async with get_db_session() as db:
                if db is None:
                    return
                
                result = await db.execute(
                    select(Conversation).where(Conversation.session_id == session_id)
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation or not conversation.context:
                    logger.warning(f"Context not found for session: {session_id}")
                    return
                
                ctx = conversation.context
                
                # Update fields
                if "factory_code" in updates:
                    ctx.factory_code = updates["factory_code"]
                if "factory_codes" in updates:
                    ctx.factory_codes = updates["factory_codes"]
                if "last_time_from" in updates:
                    ctx.last_time_from = updates["last_time_from"]
                if "last_time_to" in updates:
                    ctx.last_time_to = updates["last_time_to"]
                if "last_entity" in updates:
                    ctx.last_entity = updates["last_entity"]
                if "last_metrics" in updates:
                    ctx.last_metrics = updates["last_metrics"]
                if "last_group_by" in updates:
                    ctx.last_group_by = updates["last_group_by"]
                if "line_codes" in updates:
                    ctx.line_codes = updates["line_codes"]
                if "model_codes" in updates:
                    ctx.model_codes = updates["model_codes"]
                if "process_types" in updates:
                    ctx.process_types = updates["process_types"]
                
                ctx.updated_at = datetime.utcnow()
                await db.commit()
                
                # Update cache
                if self.use_cache:
                    context_data = await self.get_context(session_id)
                    await cache.set_session_context(session_id, context_data)
                
                logger.debug(f"Updated context for session: {session_id}")
                
        except Exception as e:
            logger.error(f"Error updating context: {e}")
    
    async def merge_context_with_request(
        self, 
        session_id: str, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge saved context with current request."""
        context = await self.get_context(session_id)
        
        if not context:
            return request
        
        # Get request context
        req_context = request.get("context", {})
        
        # Apply defaults from saved context (don't override explicit request values)
        if not req_context.get("factoryCode") and context.get("factory_code"):
            req_context["factoryCode"] = context["factory_code"]
        
        if not req_context.get("factoryCodes") and context.get("factory_codes"):
            req_context["factoryCodes"] = context["factory_codes"]
        
        # Update request
        request["context"] = req_context
        
        # Store historical context for reference
        request["_saved_context"] = context
        
        logger.debug(f"Merged context for session: {session_id}")
        return request
    
    async def extract_and_save_context(
        self, 
        session_id: str, 
        semantic_plan: Dict[str, Any],
        execution_plan: Dict[str, Any]
    ):
        """Extract context from current query and save for future use."""
        updates = {}
        
        logger.info(f"Extracting context for session {session_id}")
        logger.debug(f"Semantic plan params: {semantic_plan.get('params')}")
        logger.debug(f"Execution plan filters: {execution_plan.get('filters')}")
        
        # Extract factory
        filters = execution_plan.get("filters", {})
        if filters.get("factoryCode"):
            updates["factory_code"] = filters["factoryCode"]
            logger.info(f"Extracted factoryCode: {filters['factoryCode']}")
        
        # Extract time range
        if execution_plan.get("from"):
            updates["last_time_from"] = execution_plan["from"]
        if execution_plan.get("to"):
            updates["last_time_to"] = execution_plan["to"]
        
        # Extract entity and metrics
        if execution_plan.get("entity"):
            updates["last_entity"] = execution_plan["entity"]
        if execution_plan.get("metrics"):
            updates["last_metrics"] = execution_plan["metrics"]
        if execution_plan.get("group_by"):
            gb = execution_plan["group_by"]
            if isinstance(gb, list):
                updates["last_group_by"] = gb
            elif isinstance(gb, str):
                updates["last_group_by"] = [gb]
        
        # Extract MES filters
        if filters.get("lineCodes"):
            updates["line_codes"] = filters["lineCodes"]
        if filters.get("modelCodes"):
            updates["model_codes"] = filters["modelCodes"]
        if filters.get("processTypes"):
            updates["process_types"] = filters["processTypes"]
        
        if updates:
            await self.update_context(session_id, updates)
            logger.info(f"Saved context updates: {list(updates.keys())}")
        else:
            logger.warning(f"No context updates extracted for session {session_id}")


# Global context manager
context_manager = ContextManager()
