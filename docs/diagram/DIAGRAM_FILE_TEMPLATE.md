# Diagram File Template

Use this template as a starting point when creating new diagram groups. Copy this entire content and customize for your feature.

---

## Template: [Module Name] Diagrams

### File Name: `XX_[module_name]_flows.md`
Replace `XX` with sequential number and `[module_name]` with feature name (e.g., `09_payment_processing_flows.md`)

---

```markdown
# [Module/Feature Name] Diagrams

## Overview

### What This Module Does
[2-3 sentences describing the main functionality]

### Key Features
- Feature 1
- Feature 2
- Feature 3

### Main Participants
- FastAPI endpoints
- [Service classes]
- [Database tables]
- [External services]

---

## Flow Diagrams

### Flow X.1: [Specific Operation Name]

#### Description
[What this flow shows and when it happens]
- Trigger: [What causes this flow]
- Duration: [How long it typically takes]
- Key Outcome: [What is produced/changed]

#### Flow Diagram

\`\`\`mermaid
flowchart TD
    A["Step 1"] --> B["Step 2"]
    B --> C{Decision}
    C -->|Option 1| D["Action 1"]
    C -->|Option 2| E["Action 2"]
    D --> F["Result"]
    E --> F
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#c8e6c9
\`\`\`

#### Key Steps
1. **Step 1 (API)**: Description
2. **Step 2 (Database)**: Description
3. **Decision Point**: What determines the path
4. **Result**: What is returned to user

#### Error Handling
- Error 1 (XXX): What causes it, how it's handled
- Error 2 (XXX): What causes it, how it's handled

#### Performance Considerations
- Caching: [What can be cached]
- Indexing: [Important database indexes]
- Async: [Parts that should be async]

---

### Flow X.2: [Another Operation Name]

#### Description
[What this flow shows]
- Trigger: [What causes this]
- Duration: [Time estimate]
- Key Outcome: [What changes]

#### Flow Diagram

\`\`\`mermaid
flowchart TD
    A["Input"] --> B["Process"]
    B --> C["Output"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#c8e6c9
\`\`\`

#### Key Steps
1. **Step Name**: Description

#### Error Handling
- Error type: Handling strategy

---

## Sequence Diagrams

### Sequence X.3: [Complete End-to-End Process]

#### Description
[Complete process with all interactions]

#### Participants
- **Client**: Web/Mobile app or external client
- **FastAPI**: API server
- **Database**: PostgreSQL instance
- **[Service]**: [Description]
- **[External]**: [External service]

#### Interaction Flow

\`\`\`mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Service
    participant External
    
    Client->>API: 1. Send Request
    API->>API: 2. Validate & Process
    API->>DB: 3. Query/Update Data
    DB-->>API: 4. Response
    API->>Service: 5. Call Service
    Service->>External: 6. External Call
    External-->>Service: 7. External Response
    Service-->>API: 8. Service Response
    API-->>Client: 9. Final Response
\`\`\`

#### Sequence Breakdown

| Step | Component | Action | Result |
|------|-----------|--------|--------|
| 1 | Client → API | Send request with parameters | Request received |
| 2 | API | Validate input and extract data | Validation success |
| 3 | API → Database | Query/create/update records | Records affected |
| 4 | Database → API | Return data | Data retrieved |
| 5 | API → Service | Call business logic | Processing started |
| 6 | Service → External | Call external API | External request sent |
| 7 | External → Service | Return response | Response received |
| 8 | Service → API | Return result | Result available |
| 9 | API → Client | Send response | Response delivered |

#### Timeline
- T+0ms: Request arrives
- T+5ms: Validation complete
- T+10ms: Database query starts
- T+15ms: Database response received
- T+20ms: External service called
- T+100ms: External service responds
- T+105ms: Response sent to client

#### Possible Errors
- **400 Bad Request**: Invalid input parameters
- **401 Unauthorized**: User not authenticated
- **403 Forbidden**: User lacks permission
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource state conflict
- **500 Internal Error**: Unexpected server error
- **503 Service Unavailable**: External service down

---

## Related Components

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/[resource]/` | List resources |
| POST | `/[resource]/` | Create resource |
| GET | `/[resource]/{id}` | Get specific resource |
| PUT | `/[resource]/{id}` | Update resource |
| DELETE | `/[resource]/{id}` | Delete resource |

**Endpoint File**: `app/api/v1/endpoints/[module]_endpoints.py`

### Service Classes
| Service | Purpose | Methods |
|---------|---------|---------|
| [ServiceName] | [Description] | create(), read(), update(), delete() |

**Service File**: `app/services/[module]_service.py`

### Database Models
| Model | Table | Purpose |
|-------|-------|---------|
| [Model] | [table_name] | [Description] |

**Model File**: `app/models/[module]_model.py`

### Schemas
| Schema | Purpose |
|--------|---------|
| [SchemaName]Base | Base fields |
| [SchemaName]Create | Creation input |
| [SchemaName]Update | Update input |
| [SchemaName] | Response output |

**Schema File**: `app/schemas/[module].py`

---

## Data Models

### Request Schema Example

\`\`\`python
class [ResourceName]Create(BaseModel):
    """Schema for creating [resource]"""
    field1: str = Field(..., description="Description")
    field2: Optional[str] = Field(None, description="Optional field")
    field3: int = Field(default=0, description="Default value")
\`\`\`

### Response Schema Example

\`\`\`python
class [ResourceName](BaseModel):
    """Schema for [resource] response"""
    id: int
    field1: str
    field2: Optional[str]
    field3: int
    created_at: datetime
    
    class Config:
        from_attributes = True
\`\`\`

### Database Model Example

\`\`\`python
class [ResourceName](Base):
    __tablename__ = "[resource_name]s"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    field1 = Column(String(255), nullable=False)
    field2 = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="[resources]")
\`\`\`

---

## Authentication & Authorization

### Required Permissions
- Endpoint 1: User must own the resource
- Endpoint 2: User must be authenticated
- Endpoint 3: User must have admin role

### Authorization Pattern
\`\`\`python
# Verify resource ownership
resource = db.query([Model]).filter(
    [Model].id == resource_id,
    [Model].user_id == current_user.id
).first()

if not resource:
    return error_response("Not found", 404)
\`\`\`

---

## Caching Strategy

### What to Cache
- Resource lists with pagination
- User preferences
- Frequently accessed data

### Cache Keys
- `[module]:{user_id}:{resource_id}` - Single resource
- `[module]:list:{user_id}:{skip}:{limit}` - Resource list
- `[module]:count:{user_id}` - Count by user

### TTL (Time To Live)
- Static data: 24 hours
- User data: 1 hour
- List pages: 5 minutes

### Invalidation
- Create: Invalidate list cache
- Update: Invalidate resource cache
- Delete: Invalidate list and resource cache

---

## Validation Rules

### Input Validation
- Field 1: [Validation rule] (e.g., "Max 255 characters")
- Field 2: [Validation rule]
- Field 3: [Validation rule]

### Business Logic Validation
- Rule 1: [Description]
- Rule 2: [Description]

### Example Validation
\`\`\`python
class [ResourceName]Create(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v
\`\`\`

---

## Error Handling

### Common Errors
| HTTP Code | Error | Cause | Solution |
|-----------|-------|-------|----------|
| 400 | Validation Error | Invalid input | Check request format |
| 401 | Unauthorized | No auth token | Provide valid JWT token |
| 403 | Forbidden | No permission | Check resource ownership |
| 404 | Not Found | Resource missing | Verify resource exists |
| 409 | Conflict | Business logic violation | [Specific rule] |
| 500 | Server Error | Unexpected error | Check server logs |

### Error Response Format
\`\`\`json
{
    "success": false,
    "code": 400,
    "message": "Error description",
    "data": null
}
\`\`\`

---

## Testing Checklist

- [ ] Can create [resource]
- [ ] Can read [resource]
- [ ] Can update [resource]
- [ ] Can delete [resource]
- [ ] Validation errors return 400
- [ ] Auth errors return 401
- [ ] Permission errors return 403
- [ ] Not found returns 404
- [ ] Concurrent operations handled correctly
- [ ] Cannot access other user's resources
- [ ] Pagination works correctly
- [ ] Filtering works correctly
- [ ] Sorting works correctly

---

## Performance Metrics

### Expected Performance
- List endpoint: < 100ms (with pagination)
- Create endpoint: < 50ms
- Update endpoint: < 50ms
- Delete endpoint: < 50ms
- Search endpoint: < 200ms

### Database Queries
- Queries per request: [Number]
- Important indexes: [List]
- N+1 problem mitigation: [Strategy]

### Optimization Tips
1. Use pagination for list endpoints
2. Lazy load relationships
3. Cache frequently accessed data
4. Use database indexes on foreign keys
5. Batch operations where possible

---

## Integration with Other Modules

### Dependencies
- [Module 1]: Uses for [purpose]
- [Module 2]: Triggers [action]

### Dependent On
- [Module 1]: [Module Name] depends on this

### Event Triggers
- Creating [Resource]: Triggers [Event]
- Updating [Resource]: Triggers [Event]
- Deleting [Resource]: Triggers [Event]

---

## Future Enhancements

### Planned Features
- [ ] Feature 1: Description
- [ ] Feature 2: Description
- [ ] Feature 3: Description

### Scalability Considerations
- Current limit: [Limit]
- Scaling strategy: [Strategy]
- Optimization needed: [Where]

---

## References & Links

- **Code**: [File paths to implementation]
- **Documentation**: [Related docs]
- **Tests**: [Test file paths]
- **Issues**: [GitHub issues if any]

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-30 | [Name] | Initial diagram creation |

---

**Note**: This is a living document. Update whenever the feature changes or new information is discovered.
\`\`\`

---

## How to Use This Template

1. **Copy the entire markdown content** above
2. **Create new file** in `docs/diagrams/` with format `XX_feature_name_flows.md`
3. **Replace placeholders**:
   - `[Module/Feature Name]` → Your feature name
   - `[Service]` → Your service names
   - `[Resource]` → Your resource names
4. **Replace diagram examples** with your actual flows
5. **Update participants** in sequence diagrams
6. **Fill in all sections** (some can be removed if not applicable)
7. **Test Mermaid syntax** on https://mermaid.live/
8. **Get peer review** before merging

---

## Tips for Using This Template

### Keep It Organized
- One diagram per major flow
- Group related flows together
- Use consistent naming

### Make It Maintainable
- Update whenever code changes
- Keep descriptions current
- Include version numbers

### Make It Useful
- Include error cases
- Show external integrations
- Explain timing/performance
- Link to related code

### Make It Professional
- Use consistent colors
- Clear, readable node labels
- Proper formatting
- Meaningful descriptions

---

**Last Updated**: December 30, 2025
