from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    resource_tag_links: Mapped[list["ResourceTag"]] = relationship("ResourceTag", back_populates="tag")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    resources: Mapped[list["Resource"]] = relationship("Resource", back_populates="source")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    is_repository: Mapped[bool] = mapped_column(Boolean, default=False)
    is_documentation: Mapped[bool] = mapped_column(Boolean, default=False)
    is_article: Mapped[bool] = mapped_column(Boolean, default=False)
    is_skill: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    source: Mapped["Source"] = relationship("Source", back_populates="resources")
    repository_row: Mapped[Optional["Repository"]] = relationship(
        "Repository", back_populates="resource", uselist=False, passive_deletes=True
    )
    article_row: Mapped[Optional["Article"]] = relationship(
        "Article", back_populates="resource", uselist=False, passive_deletes=True
    )
    skill_row: Mapped[Optional["Skill"]] = relationship(
        "Skill", back_populates="resource", uselist=False, passive_deletes=True
    )
    tag_links: Mapped[list["ResourceTag"]] = relationship(
        "ResourceTag", back_populates="resource", passive_deletes=True
    )
    doc_routes: Mapped[list["DocRoute"]] = relationship(
        "DocRoute", back_populates="resource", passive_deletes=True
    )


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="repository_row")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    year_published: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="article_row")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="skill_row")


class ResourceTag(Base):
    __tablename__ = "resources_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="tag_links")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="resource_tag_links")


class DocRoute(Base):
    __tablename__ = "doc_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    resource: Mapped["Resource"] = relationship("Resource", back_populates="doc_routes")
