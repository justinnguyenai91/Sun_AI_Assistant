"""
Database models for conversation history and session management.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Conversation(Base):
    """Represents a conversation session between user and AI."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    factory_code = Column(String(20), nullable=True, index=True)
    locale = Column(String(10), default="vi")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    context = relationship("SessionContext", back_populates="conversation", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_updated", "session_id", "updated_at"),
    )


class Message(Base):
    """Individual messages within a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Query execution details (for assistant messages)
    query_type = Column(String(50), nullable=True)  # report, statistic, explain, ui
    entity = Column(String(50), nullable=True)  # production, defect, etc.
    execution_plan = Column(JSON, nullable=True)
    result_rows = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    token_count = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_conversation_created", "conversation_id", "created_at"),
    )


class SessionContext(Base):
    """Persistent context for a conversation session."""
    __tablename__ = "session_contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Factory context
    factory_code = Column(String(20), nullable=True)
    factory_codes = Column(JSON, nullable=True)  # Array of factory codes
    
    # Time context
    last_time_from = Column(String(20), nullable=True)
    last_time_to = Column(String(20), nullable=True)
    
    # Entity context
    last_entity = Column(String(50), nullable=True)
    last_metrics = Column(JSON, nullable=True)  # Array of metric IDs
    last_group_by = Column(JSON, nullable=True)  # Array of dimensions
    
    # MES-specific filters
    line_codes = Column(JSON, nullable=True)
    model_codes = Column(JSON, nullable=True)
    process_types = Column(JSON, nullable=True)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="context")

    __table_args__ = (
        Index("idx_context_factory", "factory_code"),
    )


class QueryCache(Base):
    """Cache for expensive query results."""
    __tablename__ = "query_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    result_data = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    hit_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index("idx_cache_expires", "expires_at"),
    )
