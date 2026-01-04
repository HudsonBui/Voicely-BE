# Voicely-BE Diagrams - Complete Index

Welcome to the Voicely-BE Mermaid Diagrams documentation. This index will help you navigate all available diagrams and understand what each one shows.

---

## 📋 Quick Navigation

### 📖 Documentation Files
1. **[MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md)** ⭐ START HERE
   - Comprehensive guide with all 8 diagram groups
   - Complete mermaid code examples
   - Implementation instructions
   - Best practices and conventions

2. **[DIAGRAMS_QUICK_REFERENCE.md](DIAGRAMS_QUICK_REFERENCE.md)** 
   - Quick lookup table for all diagrams
   - When to update each diagram
   - Diagram type selection guide
   - Common patterns and templates

3. **[DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md)**
   - Template for creating new diagram groups
   - Copy-paste ready structure
   - Best practices included
   - Customization examples

4. **[DIAGRAMS_INDEX.md](DIAGRAMS_INDEX.md)** (This file)
   - Navigation guide
   - File organization
   - Quick search reference

---

## 🗂️ Diagram Files Organization

```
docs/
├── MERMAID_DIAGRAMS_GUIDE.md          (Main comprehensive guide)
├── DIAGRAMS_QUICK_REFERENCE.md        (Quick lookup)
├── DIAGRAM_FILE_TEMPLATE.md           (Template for new diagrams)
├── DIAGRAMS_INDEX.md                  (This navigation file)
└── diagrams/
    ├── 01_authentication_flows.md      (Auth flows)
    ├── 02_audio_management_flows.md    (Upload & processing)
    ├── 03_async_task_processing.md     (Background jobs)
    ├── 04_note_generation_flows.md     (Notes & search)
    ├── 05_chatbot_interaction_flows.md (Chatbot & RAG)
    ├── 06_folder_organization_flows.md (Folder management)
    ├── 07_notification_system_flows.md (Notifications)
    └── 08_database_relationships.md    (Database schema)
```

---

## 📚 Diagram Groups Summary

### Group 1: Authentication (01_authentication_flows.md)
**Focus**: User authentication and session management

| Flow | Type | Purpose |
|------|------|---------|
| User Registration | Flowchart | Email signup process |
| User Login | Flowchart | JWT token generation |
| Token Refresh | Flowchart | Session extension |
| Complete Auth Flow | Sequence | End-to-end authentication |

**When to update**: 
- ✅ Adding 2FA/OAuth
- ✅ Changing JWT token logic
- ✅ Email verification changes
- ✅ Password reset flow changes

**Related code**:
- `app/api/v1/endpoints/auth_enpoints.py`
- `app/services/auth_service.py`
- `app/models/user_model.py`

---

### Group 2: Audio Management (02_audio_management_flows.md)
**Focus**: Audio upload, processing, and metadata management

| Flow | Type | Purpose |
|------|------|---------|
| Audio Upload | Flowchart | File upload process |
| Processing Pipeline | Flowchart | Transcription & analysis |
| Audio Retrieval | Flowchart | Getting audio files |
| Complete Upload & Processing | Sequence | Full pipeline |

**When to update**:
- ✅ Upload size limits change
- ✅ New processing steps added
- ✅ Storage service changes
- ✅ Metadata extraction changes

**Related code**:
- `app/api/v1/endpoints/audio_endpoints.py`
- `app/services/audio_service.py`
- `app/models/audio_model.py`
- `app/worker.py`

---

### Group 3: Async Task Processing (03_async_task_processing.md)
**Focus**: Background job management and error handling

| Flow | Type | Purpose |
|------|------|---------|
| Task Job Lifecycle | Flowchart | Job states |
| Error Handling & Retry | Flowchart | Failure recovery |
| Task Processing | Sequence | Worker interaction |

**When to update**:
- ✅ Retry logic changes
- ✅ Task queue strategy changes
- ✅ Error handling improves
- ✅ New job types added

**Related code**:
- `app/models/task_job_model.py`
- `app/services/task_job_service.py`
- `app/worker.py`
- `app/config.py`

---

### Group 4: Note Generation (04_note_generation_flows.md)
**Focus**: Automatic and manual note creation, semantic search

| Flow | Type | Purpose |
|------|------|---------|
| Auto Notes from Audio | Flowchart | Automatic generation |
| Manual Note Creation | Flowchart | User editing workflow |
| Note Search | Flowchart | Semantic search |
| Complete Note Lifecycle | Sequence | Full note journey |

**When to update**:
- ✅ Auto-generation logic changes
- ✅ Summarization improves
- ✅ Search algorithm changes
- ✅ Embedding model updates

**Related code**:
- `app/api/v1/endpoints/note_endpoints.py`
- `app/services/note_service.py`
- `app/services/embedding_service.py`
- `app/models/note_model.py`
- `app/models/note_chunk_model.py`

---

### Group 5: Chatbot Interactions (05_chatbot_interaction_flows.md)
**Focus**: Chatbot sessions, RAG responses, intent detection

| Flow | Type | Purpose |
|------|------|---------|
| Session Initialization | Flowchart | Chat setup |
| RAG Response Generation | Flowchart | Context-aware responses |
| Intent Detection | Flowchart | User intent routing |
| Complete Chatbot Flow | Sequence | End-to-end chat |

**When to update**:
- ✅ LLM provider changes
- ✅ RAG strategy changes
- ✅ Intent detection improves
- ✅ Context retrieval changes

**Related code**:
- `app/api/v1/endpoints/chatbot_endpoints.py`
- `app/services/chatbot_service.py`
- `app/services/rag_context_service.py`
- `app/services/intent_service.py`
- `app/models/chatbot_model.py`

---

### Group 6: Folder Organization (06_folder_organization_flows.md)
**Focus**: Folder CRUD operations and audio organization

| Flow | Type | Purpose |
|------|------|---------|
| Folder Creation & Management | Flowchart | CRUD operations |
| Moving Audio Between Folders | Flowchart | Audio organization |
| Folder Deletion Cascade | Flowchart | Cleanup process |
| Complete Management | Sequence | Full operations |

**When to update**:
- ✅ Adding folder sharing
- ✅ Nested folders support
- ✅ Default folder logic changes
- ✅ Organization features added

**Related code**:
- `app/api/v1/endpoints/folder_endpoints.py`
- `app/services/folder_service.py`
- `app/models/folder_model.py`

---

### Group 7: Notification System (07_notification_system_flows.md)
**Focus**: Event triggers, multi-channel delivery, preferences

| Flow | Type | Purpose |
|------|------|---------|
| Trigger & Queue | Flowchart | Event to queue |
| Multi-Channel Delivery | Flowchart | FCM, WebSocket, Email |
| Preferences Management | Flowchart | User settings |
| End-to-End Flow | Sequence | Complete notification |

**When to update**:
- ✅ New notification channels added
- ✅ Event trigger logic changes
- ✅ Delivery strategy changes
- ✅ Preferences structure changes

**Related code**:
- `app/api/v1/endpoints/notification_endpoints.py`
- `app/services/notification_service.py`
- `app/models/notification_model.py`
- `app/socket_manager.py`

---

### Group 8: Database Relationships (08_database_relationships.md)
**Focus**: Schema design and data model relationships

| Diagram | Type | Purpose |
|---------|------|---------|
| Entity Relationship | ER Diagram | Complete schema |
| Data Flow | Graph | Data pipeline |

**When to update**:
- ✅ New tables added
- ✅ Relationships change
- ✅ Schema redesign
- ✅ New features require new tables

**Related code**:
- `app/models/` (all model files)
- `alembic/versions/` (migrations)

---

## 🎯 Finding the Right Diagram

### By Use Case

**I need to understand how...**

| Question | Diagram |
|----------|---------|
| Users authenticate? | [Auth Flow](diagrams/01_authentication_flows.md#flow-14-complete-authentication-flow) |
| Audio is uploaded? | [Upload Flow](diagrams/02_audio_management_flows.md#flow-21-audio-upload-flow) |
| Background jobs work? | [Task Processing](diagrams/03_async_task_processing.md) |
| Notes are generated? | [Note Generation](diagrams/04_note_generation_flows.md) |
| Chatbot responds? | [Chatbot Flow](diagrams/05_chatbot_interaction_flows.md#sequence-54-complete-chatbot-interaction) |
| Folders are organized? | [Folder Management](diagrams/06_folder_organization_flows.md) |
| Notifications work? | [Notifications](diagrams/07_notification_system_flows.md) |
| Database is structured? | [ER Diagram](diagrams/08_database_relationships.md#diagram-81-complete-entity-relationship-diagram) |

### By Component

| Component | Relevant Diagrams |
|-----------|-------------------|
| FastAPI Server | All groups |
| PostgreSQL | Groups 4, 6, 8 |
| Redis | Groups 3, 7 |
| Storage (GCS) | Group 2 |
| Vector DB | Groups 4, 5 |
| Speech API | Group 2 |
| LLM API | Group 5 |
| FCM | Group 7 |
| Email Service | Groups 1, 7 |

### By Flow Type

| Type | Examples |
|------|----------|
| Flowchart | All creation, update, deletion flows |
| Sequence | Complete end-to-end processes |
| ER Diagram | Database schema |

---

## 🔄 Workflow: Creating New Diagrams

### Step 1: Plan
1. Identify the flow/feature
2. List all participants
3. Sketch on paper

### Step 2: Select Type
- Simple process → **Flowchart**
- Multi-actor interaction → **Sequence**
- Data model → **ER Diagram**

### Step 3: Draft
- Use [Mermaid Live Editor](https://mermaid.live/)
- Write mermaid code
- Test syntax

### Step 4: Document
- Use [DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md)
- Fill all sections
- Add error handling

### Step 5: Review
- Check for accuracy
- Validate against code
- Get peer review

### Step 6: Integrate
- Add to appropriate group file
- Update this index
- Commit to git

---

## 📊 Diagram Statistics

### Coverage by Group
- **Authentication**: 4 diagrams (100% coverage)
- **Audio Management**: 4 diagrams (100% coverage)
- **Task Processing**: 3 diagrams (100% coverage)
- **Note Generation**: 4 diagrams (100% coverage)
- **Chatbot**: 4 diagrams (100% coverage)
- **Folder Organization**: 4 diagrams (100% coverage)
- **Notifications**: 4 diagrams (100% coverage)
- **Database**: 2 diagrams (100% coverage)

**Total**: 33 diagrams across 8 groups

### Diagram Types
- Flowcharts: 24 (73%)
- Sequence Diagrams: 7 (21%)
- ER Diagrams: 2 (6%)

---

## 🛠️ Tools & Resources

### Essential Tools
- **Mermaid Live Editor**: https://mermaid.live/ (Test diagrams)
- **VS Code Extension**: Markdown Preview Mermaid Support
- **GitHub**: Auto-renders diagrams in markdown

### Documentation
- **Mermaid Docs**: https://mermaid.js.org/
- **Flowchart Guide**: https://mermaid.js.org/syntax/flowchart.html
- **Sequence Guide**: https://mermaid.js.org/syntax/sequenceDiagram.html

### Related Documentation
- [MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md) - Main guide
- [DIAGRAMS_QUICK_REFERENCE.md](DIAGRAMS_QUICK_REFERENCE.md) - Quick lookup
- [DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md) - Template

---

## 📝 Maintenance Schedule

### Monthly
- Review accuracy against code
- Check for outdated information
- Update example endpoints

### Per Feature Release
- Update affected diagrams
- Add new flows if needed
- Update this index

### Quarterly
- Comprehensive review
- Identify missing diagrams
- Plan improvements

---

## 🎓 Learning Path

**New to the project?** Follow this path:

1. ✅ Read this index (5 min)
2. ✅ Read [DIAGRAMS_QUICK_REFERENCE.md](DIAGRAMS_QUICK_REFERENCE.md) (10 min)
3. ✅ Browse [MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md) (30 min)
4. ✅ Study relevant diagrams for your feature (20 min)
5. ✅ Read actual code implementation (30 min)

**Want to add a diagram?** Follow this path:

1. ✅ Review [DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md)
2. ✅ Look at similar existing diagram
3. ✅ Draft on [Mermaid Live](https://mermaid.live/)
4. ✅ Copy template and customize
5. ✅ Get peer review
6. ✅ Commit to docs

---

## ❓ FAQ

**Q: Where should I start?**
A: Start with [MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md) for comprehensive overview.

**Q: How do I create a new diagram?**
A: Use [DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md) as your starting point.

**Q: My feature isn't shown?**
A: Check [MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md#useful-examples) for examples and create using the template.

**Q: How often should I update diagrams?**
A: Update whenever the flow changes significantly. See maintenance schedule above.

**Q: Can I use different diagram types?**
A: Yes! See [DIAGRAMS_QUICK_REFERENCE.md](DIAGRAMS_QUICK_REFERENCE.md#choosing-the-right-diagram-type) for guidance.

**Q: Should I include error handling?**
A: Yes, always show error paths and how they're handled.

---

## 📞 Support

### For Questions About...
- **Diagram Syntax**: See [Mermaid Documentation](https://mermaid.js.org/)
- **Architecture**: See [MERMAID_DIAGRAMS_GUIDE.md](MERMAID_DIAGRAMS_GUIDE.md)
- **Specific Feature**: See relevant diagram group
- **Creating Diagrams**: See [DIAGRAM_FILE_TEMPLATE.md](DIAGRAM_FILE_TEMPLATE.md)

### For Issues
- Diagram outdated? Update it and commit
- Diagram missing? Create using template
- Syntax error? Test on https://mermaid.live/

---

## 🔗 Quick Links

### Main Documentation
- [Comprehensive Guide](MERMAID_DIAGRAMS_GUIDE.md)
- [Quick Reference](DIAGRAMS_QUICK_REFERENCE.md)
- [Template for New Diagrams](DIAGRAM_FILE_TEMPLATE.md)

### Diagram Files
- [Authentication](diagrams/01_authentication_flows.md)
- [Audio Management](diagrams/02_audio_management_flows.md)
- [Async Processing](diagrams/03_async_task_processing.md)
- [Notes](diagrams/04_note_generation_flows.md)
- [Chatbot](diagrams/05_chatbot_interaction_flows.md)
- [Folders](diagrams/06_folder_organization_flows.md)
- [Notifications](diagrams/07_notification_system_flows.md)
- [Database](diagrams/08_database_relationships.md)

### External Tools
- [Mermaid Live Editor](https://mermaid.live/)
- [Mermaid Documentation](https://mermaid.js.org/)
- [Draw.io Alternative](https://draw.io/)

---

## 📈 Improvement Ideas

Planned enhancements:
- [ ] Add state machine diagrams for complex workflows
- [ ] Add deployment architecture diagrams
- [ ] Add performance benchmark diagrams
- [ ] Add testing strategy diagrams
- [ ] Add monitoring/alerting diagrams
- [ ] Interactive diagram viewer
- [ ] Diagram version history

---

## 📜 Document Information

**Document Type**: Navigation & Index  
**Version**: 1.0  
**Last Updated**: December 30, 2025  
**Maintained By**: Development Team  
**Status**: Active - Regularly Updated  

**Related Documents**:
- MERMAID_DIAGRAMS_GUIDE.md (Comprehensive guide)
- DIAGRAMS_QUICK_REFERENCE.md (Quick reference)
- DIAGRAM_FILE_TEMPLATE.md (Template)

---

## 🎉 You're Ready!

You now have everything you need to:
- ✅ Understand all system flows
- ✅ Find relevant diagrams quickly
- ✅ Create new diagrams
- ✅ Maintain and update diagrams

**Next Steps**:
1. Bookmark this page
2. Read the Comprehensive Guide
3. Explore specific diagrams for your feature
4. Reference these diagrams in your implementation

Happy diagramming! 🚀

---

**Quick Navigation**:
- [📖 Main Guide](MERMAID_DIAGRAMS_GUIDE.md)
- [⚡ Quick Reference](DIAGRAMS_QUICK_REFERENCE.md)
- [📋 Template](DIAGRAM_FILE_TEMPLATE.md)
