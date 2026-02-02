"""Pipeline Templates Router.

This module provides REST API endpoints for managing reusable pipeline templates.
Users can save, load, and share pipeline configurations.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/templates", tags=["templates"])


# ========== Pydantic Models ==========


class TemplateCreate(BaseModel):
    """Request model for creating a template."""

    name: str = Field(..., description="Template name")
    description: str = Field("", description="Template description")
    definition: dict = Field(..., description="Pipeline definition JSON")
    tags: list[str] = Field(default_factory=list, description="Template tags")
    category: str | None = Field(None, description="Template category")
    is_public: bool = Field(False, description="Whether template is public")


class TemplateUpdate(BaseModel):
    """Request model for updating a template."""

    name: str | None = None
    description: str | None = None
    definition: dict | None = None
    tags: list[str] | None = None
    category: str | None = None
    is_public: bool | None = None


class TemplateResponse(BaseModel):
    """Response model for a template."""

    template_id: str
    name: str
    description: str
    definition: dict
    tags: list[str]
    author: str | None
    category: str | None
    is_public: bool
    created_at: str
    updated_at: str | None


class TemplateListResponse(BaseModel):
    """Response model for template list."""

    templates: list[TemplateResponse]
    total: int


class InstantiateRequest(BaseModel):
    """Request model for instantiating a template."""

    name: str = Field(..., description="Name for the new pipeline")
    overrides: dict = Field(default_factory=dict, description="Override values for template variables")


class InstantiateResponse(BaseModel):
    """Response model for template instantiation."""

    pipeline_name: str
    definition: dict
    message: str


# ========== Helper Functions ==========


def _get_store():
    """Get the SQLMetadataStore instance."""
    import os

    from flowyml.storage.sql import SQLMetadataStore

    db_url = os.getenv("FLOWYML_DATABASE_URL")
    return SQLMetadataStore(db_url=db_url)


def _get_current_user() -> str | None:
    """Get current user (placeholder for auth integration)."""
    # TODO: Integrate with actual auth system
    return None


# ========== API Endpoints ==========


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(template: TemplateCreate) -> TemplateResponse:
    """Create a new pipeline template.

    Example:
        POST /api/templates/
        {
            "name": "Training Pipeline",
            "description": "Standard ML training pipeline",
            "definition": {"steps": [...]},
            "tags": ["training", "ml"],
            "category": "training"
        }
    """
    store = _get_store()
    template_id = str(uuid.uuid4())
    author = _get_current_user()
    now = datetime.now().isoformat()

    store.save_pipeline_template(
        template_id=template_id,
        name=template.name,
        definition=template.definition,
        description=template.description,
        tags=template.tags,
        author=author,
        category=template.category,
        is_public=template.is_public,
    )

    return TemplateResponse(
        template_id=template_id,
        name=template.name,
        description=template.description,
        definition=template.definition,
        tags=template.tags,
        author=author,
        category=template.category,
        is_public=template.is_public,
        created_at=now,
        updated_at=None,
    )


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    include_public: bool = Query(True, description="Include public templates"),
    author: str | None = Query(None, description="Filter by author"),
) -> TemplateListResponse:
    """List all pipeline templates.

    Example:
        GET /api/templates/?category=training&include_public=true
    """
    store = _get_store()

    templates = store.list_pipeline_templates(
        category=category,
        include_public=include_public,
        author=author,
    )

    return TemplateListResponse(
        templates=[
            TemplateResponse(
                template_id=t["template_id"],
                name=t["name"],
                description=t["description"],
                definition=t["definition"],
                tags=t["tags"],
                author=t["author"],
                category=t["category"],
                is_public=t["is_public"],
                created_at=t["created_at"],
                updated_at=t["updated_at"],
            )
            for t in templates
        ],
        total=len(templates),
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str) -> TemplateResponse:
    """Get a specific pipeline template by ID.

    Example:
        GET /api/templates/abc123
    """
    store = _get_store()
    template = store.get_pipeline_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return TemplateResponse(
        template_id=template["template_id"],
        name=template["name"],
        description=template["description"],
        definition=template["definition"],
        tags=template["tags"],
        author=template["author"],
        category=template["category"],
        is_public=template["is_public"],
        created_at=template["created_at"],
        updated_at=template["updated_at"],
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: str, update: TemplateUpdate) -> TemplateResponse:
    """Update an existing pipeline template.

    Example:
        PUT /api/templates/abc123
        {"name": "Updated Name", "description": "Updated desc"}
    """
    store = _get_store()
    existing = store.get_pipeline_template(template_id)

    if not existing:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # Merge updates with existing values
    store.save_pipeline_template(
        template_id=template_id,
        name=update.name or existing["name"],
        definition=update.definition or existing["definition"],
        description=update.description if update.description is not None else existing["description"],
        tags=update.tags if update.tags is not None else existing["tags"],
        author=existing["author"],
        category=update.category if update.category is not None else existing["category"],
        is_public=update.is_public if update.is_public is not None else existing["is_public"],
    )

    # Fetch updated template
    updated = store.get_pipeline_template(template_id)

    return TemplateResponse(
        template_id=updated["template_id"],
        name=updated["name"],
        description=updated["description"],
        definition=updated["definition"],
        tags=updated["tags"],
        author=updated["author"],
        category=updated["category"],
        is_public=updated["is_public"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: str) -> None:
    """Delete a pipeline template.

    Example:
        DELETE /api/templates/abc123
    """
    store = _get_store()
    deleted = store.delete_pipeline_template(template_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")


@router.post("/{template_id}/instantiate", response_model=InstantiateResponse)
async def instantiate_template(template_id: str, request: InstantiateRequest) -> InstantiateResponse:
    """Create a new pipeline from a template.

    This endpoint takes a template and instantiates it with the provided
    name and any override values for template variables.

    Example:
        POST /api/templates/abc123/instantiate
        {
            "name": "my-training-run",
            "overrides": {"learning_rate": 0.001}
        }
    """
    store = _get_store()
    template = store.get_pipeline_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # Clone the definition
    definition = template["definition"].copy()

    # Apply overrides (simple key replacement for now)
    if request.overrides:
        _apply_overrides(definition, request.overrides)

    # Set the pipeline name
    definition["name"] = request.name

    return InstantiateResponse(
        pipeline_name=request.name,
        definition=definition,
        message=f"Pipeline '{request.name}' instantiated from template '{template['name']}'",
    )


def _apply_overrides(definition: dict, overrides: dict) -> None:
    """Apply override values to a pipeline definition.

    This recursively searches for matching keys and replaces their values.
    """
    for key, value in overrides.items():
        if key in definition:
            definition[key] = value
        # Check nested dicts
        for _, v in definition.items():
            if isinstance(v, dict):
                _apply_overrides(v, {key: value})
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _apply_overrides(item, {key: value})
