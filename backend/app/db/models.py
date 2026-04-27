"""Database models."""
import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Project(Base):
    """A research project — typically one client or one engagement."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), index=True)  # Clerk user ID
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list["ResearchRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ResearchRun(Base):
    """One execution of a research workflow."""
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    workflow_type: Mapped[str] = mapped_column(String(50))  # 'annual_report', 'competitive_landscape', etc.
    target: Mapped[str] = mapped_column(String(500))  # company name or URL
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|failed
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"step": "scraping", "pct": 30}
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    documents: Mapped[list["Document"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Company(Base):
    """Cached company metadata. Avoids re-scraping the same company."""
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    annual_report_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    last_scraped: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """A document fetched and parsed (annual report PDF, press release, etc.)."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"))
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    doc_type: Mapped[str] = mapped_column(String(50))  # 'annual_report'|'press_release'|'webpage'
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["ResearchRun"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Chunked text with embedding for RAG retrieval."""
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024))  # Voyage dimensionality

    document: Mapped["Document"] = relationship(back_populates="chunks")
