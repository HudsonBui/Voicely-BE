# Voicely-BE Mermaid Diagrams Guide

## Overview
This guide provides comprehensive instructions for drawing flow diagrams and sequence diagrams for the Voicely Backend application. The diagrams are organized by functional groups and each group has its own dedicated mermaid file.

**Project Architecture:** FastAPI Backend with PostgreSQL, Redis, Firebase, and WebSocket support.

---

## Diagram Groups

### 1. [Authentication Flows](#1-authentication-flows)
### 2. [Audio Management Flows](#2-audio-management-flows)
### 3. [Async Task Processing](#3-async-task-processing)
### 4. [Note Generation Flows](#4-note-generation-flows)
### 5. [Chatbot Interaction Flows](#5-chatbot-interaction-flows)
### 6. [Folder Organization Flows](#6-folder-organization-flows)
### 7. [Notification System Flows](#7-notification-system-flows)
### 8. [Database Relationships](#8-database-relationships)

---

## 1. Authentication Flows

### File: `diagrams/01_authentication_flows.md`

#### Flow 1.1: User Registration Flow
Shows the complete process of user registration with email verification.

```mermaid
flowchart TD
    A["User Access App"] --> B["Request Registration"]
    B --> C["FastAPI: /auth/register"]
    C --> D["Validate Email & Password"]
    D --> E{Email Valid?}
    E -->|No| F["Return Error 400"]
    E -->|Yes| G["Check Email Exists"]
    G --> H{Email Exists?}
    H -->|Yes| I["Return Error 409"]
    H -->|No| J["Hash Password"]
    J --> K["Create User in Database"]
    K --> L["Generate Email Token"]
    L --> M["Send Verification Email"]
    M --> N["Return 201 Created"]
    N --> O["User Confirms Email"]
    O --> P["Update user.is_active = True"]
    P --> Q["Registration Complete"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style Q fill:#c8e6c9
```

#### Flow 1.2: User Login Flow
Shows the authentication process with JWT token generation.

```mermaid
flowchart TD
    A["User Submits Credentials"] --> B["FastAPI: /auth/login"]
    B --> C["Get Email & Password"]
    C --> D["Query User from Database"]
    D --> E{User Exists?}
    E -->|No| F["Return 401 Unauthorized"]
    E -->|Yes| G["Verify Password Hash"]
    G --> H{Password Valid?}
    H -->|No| I["Return 401 Unauthorized"]
    H -->|Yes| J["Check user.is_active"]
    J --> K{Account Active?}
    K -->|No| L["Return 403 Forbidden"]
    K -->|Yes| M["Generate JWT Token"]
    M --> N["Generate Refresh Token"]
    N --> O["Save Refresh Token in Redis"]
    O --> P["Return Token & User Info"]
    P --> Q["Client Stores Token"]
    Q --> R["Authentication Success"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style R fill:#c8e6c9
    style F fill:#ffcdd2
```

#### Flow 1.3: Token Refresh Flow
Shows the process of refreshing expired access tokens.

```mermaid
flowchart TD
    A["Client Has Expired Token"] --> B["Request Token Refresh"]
    B --> C["FastAPI: /auth/refresh"]
    C --> D["Extract Refresh Token"]
    D --> E["Query Redis for Token"]
    E --> F{Token Exists?}
    F -->|No| G["Return 401 Unauthorized"]
    F -->|Yes| H["Decode Refresh Token"]
    H --> I{Token Valid?}
    I -->|No| J["Return 401 Unauthorized"]
    I -->|Yes| K["Generate New Access Token"]
    K --> L["Return New Access Token"]
    L --> M["Client Updates Header"]
    M --> N["Continue Request"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style N fill:#c8e6c9
```

#### Sequence 1.4: Complete Authentication Flow
Shows the interaction between Client, API, Database, and Redis.

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Database as PostgreSQL
    participant Redis
    participant Email as Email Service

    Client->>FastAPI: POST /auth/register
    FastAPI->>FastAPI: Validate Input
    FastAPI->>Database: Check Email Exists
    Database-->>FastAPI: Email Not Found
    FastAPI->>FastAPI: Hash Password
    FastAPI->>Database: Create User
    Database-->>FastAPI: User Created
    FastAPI->>Email: Send Verification Email
    Email-->>Client: Email Sent
    Note over Client: User Clicks Email Link
    Client->>FastAPI: POST /auth/verify-email
    FastAPI->>Database: Update is_active=True
    Database-->>FastAPI: Updated
    FastAPI-->>Client: 200 OK

    Client->>FastAPI: POST /auth/login
    FastAPI->>Database: Query User by Email
    Database-->>FastAPI: User Found
    FastAPI->>FastAPI: Verify Password
    FastAPI->>FastAPI: Generate JWT Token
    FastAPI->>Redis: Save Refresh Token
    Redis-->>FastAPI: Stored
    FastAPI-->>Client: Return Access & Refresh Token
    
    Note over Client: Token Expires After 24h
    Client->>FastAPI: POST /auth/refresh
    FastAPI->>Redis: Get Refresh Token
    Redis-->>FastAPI: Token Found
    FastAPI->>FastAPI: Generate New Access Token
    FastAPI-->>Client: Return New Access Token
```

---

## 2. Audio Management Flows

### File: `diagrams/02_audio_management_flows.md`

#### Flow 2.1: Audio Upload Flow
Shows the complete process of uploading an audio file.

```mermaid
flowchart TD
    A["User Selects Audio File"] --> B["Client Starts Upload"]
    B --> C["FastAPI: POST /audio/upload"]
    C --> D["Validate File Type"]
    D --> E{Valid Audio?}
    E -->|No| F["Return 400 Error"]
    E -->|Yes| G["Check File Size"]
    G --> H{Size < 500MB?}
    H -->|No| I["Return 413 Error"]
    H -->|Yes| J["Save File to Disk"]
    J --> K["Create AudioFile Record"]
    K --> L["Extract Metadata"]
    L --> M["Create TaskJob for Processing"]
    M --> N["Return 201 Created"]
    N --> O["Enqueue to Redis"]
    O --> P["Background Worker Picks Up"]
    P --> Q["Start Transcription"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style P fill:#ffe0b2
    style Q fill:#c8e6c9
```

#### Flow 2.2: Audio Processing Pipeline
Shows the async processing of uploaded audio files.

```mermaid
flowchart TD
    A["TaskJob in Queue"] --> B["Worker Starts Processing"]
    B --> C["Download Audio from Storage"]
    C --> D["Initialize Transcription Service"]
    D --> E["Send to Speech-to-Text API"]
    E --> F["Wait for Transcription Result"]
    F --> G["Save Transcript to Database"]
    G --> H["Create Embedding Vectors"]
    H --> I["Store Embeddings in Vector DB"]
    I --> J["Generate Auto-Summary"]
    J --> K["Generate Auto-Notes"]
    K --> L["Create NoteChunks for Search"]
    L --> M["Update TaskJob Status = SUCCESS"]
    M --> N["Send Completion Notification"]
    N --> O["Processing Complete"]
    
    style A fill:#fff3e0
    style B fill:#ffe0b2
    style O fill:#c8e6c9
```

#### Flow 2.3: Audio Retrieval & Metadata
Shows how users retrieve audio files and associated metadata.

```mermaid
flowchart TD
    A["User Requests Audio List"] --> B["FastAPI: GET /audio/?skip=0&limit=10"]
    B --> C["Get Current User ID"]
    C --> D["Query AudioFile with Pagination"]
    D --> E["Include Related Data"]
    E --> F["Count Associated Notes"]
    F --> G["Get TaskJob Status"]
    G --> H["Build Response DTO"]
    H --> I["Return 200 OK with Audio List"]
    I --> J["User Selects One Audio"]
    J --> K["FastAPI: GET /audio/{audio_id}"]
    K --> L["Verify User Ownership"]
    L --> M["Fetch All Related Data"]
    M --> N["Return Complete Audio Object"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style N fill:#c8e6c9
```

#### Sequence 2.4: Complete Audio Upload & Processing
Shows the interaction between Client, API, Storage, Worker, and External APIs.

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Storage as GCS Storage
    participant Database as PostgreSQL
    participant Redis
    participant Worker as Background Worker
    participant SpeechAPI as Speech-to-Text API
    participant VectorDB as Vector Database

    Client->>FastAPI: POST /audio/upload (multipart)
    FastAPI->>FastAPI: Validate Audio File
    FastAPI->>Storage: Upload File to GCS
    Storage-->>FastAPI: File Saved
    FastAPI->>Database: Create AudioFile Record
    Database-->>FastAPI: Record ID=123
    FastAPI->>FastAPI: Extract Metadata
    FastAPI->>Database: Create TaskJob (Status=PENDING)
    Database-->>FastAPI: TaskJob ID=456
    FastAPI->>Redis: Enqueue Job
    Redis-->>FastAPI: Enqueued
    FastAPI-->>Client: 201 Created with Audio ID

    Worker->>Redis: Dequeue Job
    Worker->>Database: Get TaskJob & AudioFile
    Database-->>Worker: Task Details
    Worker->>Storage: Download Audio File
    Storage-->>Worker: Audio Stream
    Worker->>SpeechAPI: Send Audio for Transcription
    SpeechAPI-->>Worker: Transcript Text
    Worker->>Database: Save Transcript
    Worker->>VectorDB: Generate & Store Embeddings
    VectorDB-->>Worker: Embeddings Stored
    Worker->>Database: Auto-generate Summary & Notes
    Worker->>Database: Create NoteChunks
    Worker->>Database: Update TaskJob Status=SUCCESS
    Database-->>Worker: Updated
    Worker->>Redis: Publish Completion Event
    Redis-->>Client: WebSocket Notification (via Socket.IO)
    Client-->>Client: Update UI - Audio Ready
```

---

## 3. Async Task Processing

### File: `diagrams/03_async_task_processing.md`

#### Flow 3.1: Task Job Lifecycle
Shows the complete lifecycle of a background task.

```mermaid
flowchart TD
    A["Task Created"] --> B["Status: PENDING"]
    B --> C["Task Enqueued to Redis"]
    C --> D["Status: QUEUED"]
    D --> E["Worker Available?"]
    E -->|No| F["Wait in Queue"]
    F --> E
    E -->|Yes| G["Worker Dequeues"]
    G --> H["Status: PROCESSING"]
    H --> I["Execute Task"]
    I --> J{Task Success?}
    J -->|Yes| K["Status: SUCCESS"]
    J -->|No| L["Status: FAILED"]
    K --> M["Store Result"]
    L --> N["Store Error Message"]
    M --> O["Task Complete"]
    N --> O
    
    style A fill:#e1f5ff
    style E fill:#fff3e0
    style K fill:#c8e6c9
    style L fill:#ffcdd2
```

#### Flow 3.2: Error Handling & Retry
Shows error handling and automatic retry mechanism.

```mermaid
flowchart TD
    A["Task Fails"] --> B["Catch Exception"]
    B --> C["Log Error Details"]
    C --> D["Check Retry Count"]
    D --> E{Retry Count < Max?}
    E -->|No| F["Status: FAILED"]
    E -->|Yes| G["Increment Retry Count"]
    G --> H["Calculate Backoff Time"]
    H --> I["Re-enqueue Task"]
    I --> J["Status: RETRYING"]
    J --> K["Wait for Next Execution"]
    K --> L["Worker Retries"]
    L --> M{Retry Success?}
    M -->|Yes| N["Status: SUCCESS"]
    M -->|No| O["Check Retry Count Again"]
    O --> E
    
    style A fill:#ffcdd2
    style F fill:#ff5252
    style N fill:#c8e6c9
```

#### Sequence 3.3: Task Processing with Worker
Shows the detailed interaction between API, Redis, Worker, and Services.

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant Redis
    participant Worker
    participant Service as Service Layer
    participant Database as PostgreSQL
    participant External as External API

    API->>Database: Create TaskJob Record
    Database-->>API: TaskJob ID=123
    API->>Redis: Enqueue Job Message
    Redis-->>API: Enqueued
    API-->>API: Return Response Immediately

    Worker->>Redis: Listen for Jobs
    Redis->>Worker: Job Message
    Worker->>Database: Get TaskJob Details
    Database-->>Worker: Task Info
    Worker->>Database: Update Status=PROCESSING
    Database-->>Worker: Updated
    Worker->>Service: Call Business Logic
    Service->>External: Call External Service
    External-->>Service: Response
    Service->>Database: Save Results
    Database-->>Service: Saved
    Service-->>Worker: Success Result
    Worker->>Database: Update Status=SUCCESS
    Database-->>Worker: Updated
    Worker->>Redis: Publish Completion Event
    Redis-->>Redis: Event Stored
    Note over Worker: Task Complete
```

---

## 4. Note Generation Flows

### File: `diagrams/04_note_generation_flows.md`

#### Flow 4.1: Automatic Note Generation from Audio
Shows how notes are automatically generated from transcribed audio.

```mermaid
flowchart TD
    A["Transcription Complete"] --> B["Extract Text"]
    B --> C["Split into Chunks"]
    C --> D["Process Each Chunk"]
    D --> E["Generate Summary per Chunk"]
    E --> F["Create NoteChunk Records"]
    F --> G["Generate Full-Document Summary"]
    G --> H["Create Note Record"]
    H --> I["Store Embeddings"]
    I --> J["Notes Ready for User"]
    
    style A fill:#e1f5ff
    style D fill:#fff3e0
    style J fill:#c8e6c9
```

#### Flow 4.2: User Creates Manual Notes
Shows the process of users creating and editing notes manually.

```mermaid
flowchart TD
    A["User Writes Note"] --> B["Click Save"]
    B --> C["FastAPI: POST /notes/"]
    C --> D["Validate Note Data"]
    D --> E{Valid?}
    E -->|No| F["Return 400 Error"]
    E -->|Yes| G["Save to Database"]
    G --> H["Generate Embedding"]
    H --> I["Index in Vector DB"]
    I --> J["Return Note ID"]
    J --> K["Note Saved"]
    
    K --> L["User Edits Note"]
    L --> M["Click Update"]
    M --> N["FastAPI: PUT /notes/{note_id}"]
    N --> O["Verify Ownership"]
    O --> P{"Owner?"}
    P -->|No| Q["Return 403 Forbidden"]
    P -->|Yes| R["Update Database"]
    R --> S["Update Embedding"]
    S --> T["Return Updated Note"]
    T --> U["Update Complete"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style K fill:#c8e6c9
    style L fill:#e1f5ff
    style N fill:#fff3e0
    style U fill:#c8e6c9
```

#### Flow 4.3: Note Search with Embeddings
Shows semantic search functionality using embeddings.

```mermaid
flowchart TD
    A["User Enters Search Query"] --> B["FastAPI: GET /notes/search?q=keyword"]
    B --> C["Generate Query Embedding"]
    C --> D["Search Vector DB"]
    D --> E["Calculate Similarity Score"]
    E --> F["Filter Results > Threshold"]
    F --> G["Sort by Relevance"]
    G --> H["Paginate Results"]
    H --> I["Return Matching Notes"]
    I --> J["Display Results to User"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style J fill:#c8e6c9
```

#### Sequence 4.4: Complete Note Lifecycle
Shows interaction from audio transcription to note search.

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant Database as PostgreSQL
    participant EmbedService as Embedding Service
    participant VectorDB as Vector DB
    participant EmbeddingModel as ML Model

    Worker->>Database: Get Transcript Text
    Database-->>Worker: Text Retrieved
    Worker->>Worker: Split into Chunks
    Worker->>EmbedService: Generate Embeddings for Chunks
    EmbedService->>EmbeddingModel: Encode Text
    EmbeddingModel-->>EmbedService: Vector Output
    EmbedService-->>Worker: Embeddings Generated
    Worker->>Database: Create NoteChunk Records with Embeddings
    Database-->>Worker: Records Created
    Worker->>VectorDB: Store Embedding Vectors
    VectorDB-->>Worker: Vectors Indexed

    User->>FastAPI: POST /notes/ (manual note)
    FastAPI->>FastAPI: Validate Note
    FastAPI->>Database: Create Note Record
    Database-->>FastAPI: Note ID=789
    FastAPI->>EmbedService: Generate Note Embedding
    EmbedService->>EmbeddingModel: Encode Note Text
    EmbeddingModel-->>EmbedService: Vector Output
    EmbedService-->>FastAPI: Embedding Generated
    FastAPI->>VectorDB: Store Note Embedding
    VectorDB-->>FastAPI: Stored
    FastAPI-->>User: 201 Created

    User->>FastAPI: GET /notes/search?q=important topics
    FastAPI->>EmbedService: Generate Query Embedding
    EmbedService->>EmbeddingModel: Encode Query
    EmbeddingModel-->>EmbedService: Vector Output
    EmbedService-->>FastAPI: Query Embedding
    FastAPI->>VectorDB: Similarity Search
    VectorDB-->>FastAPI: Matching Results with Scores
    FastAPI->>Database: Get Full Note Data
    Database-->>FastAPI: Note Details
    FastAPI-->>User: Return Ranked Search Results
```

---

## 5. Chatbot Interaction Flows

### File: `diagrams/05_chatbot_interaction_flows.md`

#### Flow 5.1: Chatbot Session Initialization
Shows how a chatbot session is created and initialized.

```mermaid
flowchart TD
    A["User Opens Chat"] --> B["FastAPI: POST /chatbot/sessions"]
    B --> C["Verify Audio Files Exist"]
    C --> D{Audio Exists?}
    D -->|No| E["Return 404 Error"]
    D -->|Yes| F["Create ChatbotSession Record"]
    F --> G["Initialize Context from Audio"]
    G --> H["Load Embeddings"]
    H --> I["Prepare RAG Context"]
    I --> J["Return Session ID"]
    J --> K["Session Ready"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style K fill:#c8e6c9
```

#### Flow 5.2: RAG-based Chatbot Response Generation
Shows how the chatbot generates contextual responses using RAG.

```mermaid
flowchart TD
    A["User Sends Message"] --> B["FastAPI: POST /chatbot/messages"]
    B --> C["Get Session & Context"]
    C --> D["Generate Message Embedding"]
    D --> E["Semantic Search in Vector DB"]
    E --> F["Retrieve Top K Similar Chunks"]
    F --> G["Build RAG Context"]
    G --> H["Construct LLM Prompt"]
    H --> I["Call LLM API"]
    I --> J["Stream Response to Client"]
    J --> K["Save Message Pair to DB"]
    K --> L["Update Session History"]
    L --> M["Response Sent"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style E fill:#fff3e0
    style I fill:#ffe0b2
    style M fill:#c8e6c9
```

#### Flow 5.3: Intent Detection
Shows how user intents are detected and routed.

```mermaid
flowchart TD
    A["User Message Received"] --> B["Extract Intent"]
    B --> C["Run Intent Classifier"]
    C --> D{Detected Intent?}
    D -->|Summarize| E["Fetch Summary Data"]
    D -->|Search| F["Perform Search"]
    D -->|Analysis| G["Generate Analysis"]
    D -->|General| H["Use RAG Response"]
    E --> I["Format Response"]
    F --> I
    G --> I
    H --> I
    I --> J["Send to User"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style J fill:#c8e6c9
```

#### Sequence 5.4: Complete Chatbot Interaction
Shows the full flow from message to response.

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant Database as PostgreSQL
    participant VectorDB as Vector DB
    participant EmbedService as Embedding Service
    participant LLMService as LLM Service
    participant LLMProvider as LLM Provider

    User->>FastAPI: POST /chatbot/messages (user_input)
    FastAPI->>Database: Get ChatbotSession
    Database-->>FastAPI: Session Found
    FastAPI->>EmbedService: Generate Message Embedding
    EmbedService-->>FastAPI: Embedding Vector
    FastAPI->>VectorDB: Semantic Search (top_k=5)
    VectorDB-->>FastAPI: Similar Chunks with Scores
    FastAPI->>Database: Get Full Context from Chunks
    Database-->>FastAPI: Context Text
    FastAPI->>FastAPI: Build RAG Prompt

    FastAPI->>LLMService: Call LLM with Context & Prompt
    LLMService->>LLMProvider: POST /chat/completions
    LLMProvider-->>LLMService: Stream Response Tokens
    LLMService-->>FastAPI: Response Chunks
    FastAPI-->>User: Stream Response via WebSocket

    FastAPI->>Database: Save ChatbotMessage (user)
    FastAPI->>Database: Save ChatbotMessage (assistant)
    FastAPI->>Database: Update Session last_message_at
    Database-->>FastAPI: Records Saved
    
    Note over FastAPI,User: Real-time Response via WebSocket
```

---

## 6. Folder Organization Flows

### File: `diagrams/06_folder_organization_flows.md`

#### Flow 6.1: Folder Creation & Management
Shows how users create and manage folders.

```mermaid
flowchart TD
    A["User Creates Folder"] --> B["FastAPI: POST /folders/"]
    B --> C["Validate Folder Data"]
    C --> D{Valid?}
    D -->|No| E["Return 400 Error"]
    D -->|Yes| F["Check Name Uniqueness"]
    F --> G{Unique?}
    G -->|No| H["Return 409 Conflict"]
    G -->|Yes| I["Create Folder Record"]
    I --> J["If is_default=True, unset others"]
    J --> K["Return Folder ID"]
    K --> L["Folder Created"]
    
    L --> M["User Updates Folder"]
    M --> N["FastAPI: PUT /folders/{folder_id}"]
    N --> O["Verify Ownership"]
    O --> P{"Owner?"}
    P -->|No| Q["Return 403 Forbidden"]
    P -->|Yes| R["Update Folder Fields"]
    R --> S["Return Updated Folder"]
    S --> T["Update Complete"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style L fill:#c8e6c9
    style M fill:#e1f5ff
    style N fill:#fff3e0
    style T fill:#c8e6c9
```

#### Flow 6.2: Audio Organization into Folders
Shows moving audio files between folders.

```mermaid
flowchart TD
    A["User Selects Audio"] --> B["Click Move to Folder"]
    B --> C["FastAPI: POST /folders/move-audio"]
    C --> D["Verify Audio Ownership"]
    D --> E{Owned?}
    E -->|No| F["Return 403 Forbidden"]
    E -->|Yes| G["Verify Folder Ownership"]
    G --> H{Folder Owned?}
    H -->|No| I["Return 403 Forbidden"]
    H -->|Yes| J["Update audio.folder_id"]
    J --> K["Save to Database"]
    K --> L["Return Success"]
    L --> M["Audio Moved"]
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style M fill:#c8e6c9
```

#### Flow 6.3: Folder Deletion with Cascading
Shows what happens when a folder is deleted.

```mermaid
flowchart TD
    A["User Deletes Folder"] --> B["FastAPI: DELETE /folders/{folder_id}"]
    B --> C["Verify Ownership"]
    C --> D{Owner?}
    D -->|No| E["Return 403 Forbidden"]
    D -->|Yes| F["Get All Audio in Folder"]
    F --> G["Unassign Audio (set folder_id=NULL)"]
    G --> H["Delete Folder Record"]
    H --> I["Return 204 No Content"]
    I --> J["Folder Deleted, Audio Unassigned"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style J fill:#c8e6c9
```

#### Sequence 6.4: Complete Folder Management
Shows full interaction from folder creation to audio organization.

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant Database as PostgreSQL

    User->>FastAPI: POST /folders/
    FastAPI->>FastAPI: Validate Input
    FastAPI->>Database: Check Name Uniqueness
    Database-->>FastAPI: Available
    FastAPI->>Database: Create Folder
    Database-->>FastAPI: Folder ID=10
    FastAPI-->>User: 201 Created

    User->>FastAPI: GET /folders/
    FastAPI->>Database: Query User Folders
    Database-->>FastAPI: Folder List
    FastAPI->>Database: Count Audio per Folder
    Database-->>FastAPI: Counts
    FastAPI-->>User: Return Folders with Counts

    User->>FastAPI: POST /folders/move-audio
    FastAPI->>Database: Get AudioFile
    Database-->>FastAPI: Audio Found
    FastAPI->>Database: Get Folder
    Database-->>FastAPI: Folder Found
    FastAPI->>Database: Update audio.folder_id=10
    Database-->>FastAPI: Updated
    FastAPI-->>User: 200 OK

    User->>FastAPI: GET /folders/{folder_id}/audio
    FastAPI->>Database: Get Audio in Folder
    Database-->>FastAPI: Audio List
    FastAPI-->>User: Return Paginated Audio Files

    User->>FastAPI: DELETE /folders/{folder_id}
    FastAPI->>Database: Get All Audio in Folder
    Database-->>FastAPI: Audio List
    FastAPI->>Database: Unassign All Audio
    Database-->>FastAPI: Updated
    FastAPI->>Database: Delete Folder
    Database-->>FastAPI: Deleted
    FastAPI-->>User: 204 No Content
```

---

## 7. Notification System Flows

### File: `diagrams/07_notification_system_flows.md`

#### Flow 7.1: Notification Trigger & Queue
Shows how notifications are triggered and queued.

```mermaid
flowchart TD
    A["Event Occurs"] --> B["Event Type?"]
    B -->|Audio Processed| C["Transcription Completed"]
    B -->|Task Failed| D["Task Failed"]
    B -->|Note Created| E["Note Auto-Generated"]
    B -->|User Action| F["Manual Event"]
    C --> G["Create Notification Record"]
    D --> G
    E --> G
    F --> G
    G --> H["Store in Database"]
    H --> I["Enqueue to Redis"]
    I --> J["Query User Preferences"]
    J --> K["Check Notification Settings"]
    K --> L["Should Send?"]
    L -->|Yes| M["Prepare Notification Payload"]
    L -->|No| N["Skip"]
    M --> O["Send via Channels"]
    
    style A fill:#e1f5ff
    style G fill:#fff3e0
    style O fill:#c8e6c9
```

#### Flow 7.2: Multi-Channel Notification Delivery
Shows how notifications are delivered via multiple channels.

```mermaid
flowchart TD
    A["Notification Ready"] --> B{Enabled Channels?}
    B -->|Push FCM| C["Firebase Cloud Messaging"]
    B -->|In-App| D["WebSocket Event"]
    B -->|Email| E["Email Service"]
    C --> F["Send FCM Push"]
    D --> G["Broadcast via Socket.IO"]
    E --> H["Send Email"]
    F --> I["Device Receives Push"]
    G --> J["Update In-App UI"]
    H --> K["User Receives Email"]
    I --> L["User Sees Notification"]
    J --> L
    K --> L
    
    style A fill:#e1f5ff
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style L fill:#c8e6c9
```

#### Flow 7.3: Notification Preferences Management
Shows how users manage notification settings.

```mermaid
flowchart TD
    A["User Opens Settings"] --> B["FastAPI: GET /notifications/preferences"]
    B --> C["Get User Preferences"]
    C --> D["Return Settings"]
    D --> E["User Changes Preferences"]
    E --> F["FastAPI: PUT /notifications/preferences"]
    F --> G["Validate Settings"]
    G --> H["Update Database"]
    H --> I["Clear Cache"]
    I --> J["Return Success"]
    J --> K["Preferences Updated"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style F fill:#fff3e0
    style K fill:#c8e6c9
```

#### Sequence 7.4: End-to-End Notification Flow
Shows the complete notification journey from event to delivery.

```mermaid
sequenceDiagram
    participant Worker as Background Worker
    participant Database as PostgreSQL
    participant Redis
    participant NotificationService as Notification Service
    participant Socket as WebSocket/Socket.IO
    participant FCM as Firebase Cloud Messaging
    participant EmailService as Email Service
    participant Client

    Worker->>Database: Task Complete
    Database-->>Worker: Task Updated
    Worker->>Database: Create Notification Record
    Database-->>Worker: Notification ID=999
    Worker->>Redis: Enqueue Notification Event
    Redis-->>Worker: Enqueued

    NotificationService->>Redis: Dequeue Notification
    NotificationService->>Database: Get User Preferences
    Database-->>NotificationService: Preferences
    NotificationService->>NotificationService: Check Settings
    
    NotificationService->>Socket: Broadcast In-App Event
    Socket-->>Client: Real-time Notification
    Client-->>Client: Update UI

    NotificationService->>Database: Get User FCM Tokens
    Database-->>NotificationService: Device Tokens
    NotificationService->>FCM: Send Push Notification
    FCM-->>NotificationService: Delivery Confirmed
    FCM-->>Client: Push Notification
    Client-->>Client: Display Notification

    NotificationService->>EmailService: Send Email Notification
    EmailService-->>EmailService: Format Email
    EmailService-->>Client: Email Received
    
    NotificationService->>Database: Mark Notification Sent
    Database-->>NotificationService: Updated
```

---

## 8. Database Relationships

### File: `diagrams/08_database_relationships.md`

#### Diagram 8.1: Complete Entity Relationship Diagram
Shows all database tables and their relationships.

```mermaid
erDiagram
    USER ||--o{ AUDIO_FILE : uploads
    USER ||--o{ FOLDER : owns
    USER ||--o{ NOTE : creates
    USER ||--o{ TASK_JOB : initiates
    USER ||--o{ CHATBOT_SESSION : starts
    USER ||--o{ NOTIFICATION : receives
    USER ||--o{ USER_DEVICE : registers
    
    FOLDER ||--o{ AUDIO_FILE : contains
    
    AUDIO_FILE ||--o{ NOTE : references
    AUDIO_FILE ||--o{ TASK_JOB : processes
    AUDIO_FILE ||--o{ CHATBOT_SESSION : analyzes
    AUDIO_FILE ||--o{ NOTE_CHUNK : generates
    
    NOTE ||--o{ NOTE_CHUNK : splits
    
    CHATBOT_SESSION ||--o{ CHATBOT_MESSAGE : contains
    
    TASK_JOB {
        int id
        int user_id
        int audio_id
        string task_type
        string status
        string progress
        datetime created_at
        datetime updated_at
    }
    
    USER {
        int id
        string email
        string password_hash
        string full_name
        boolean is_active
        datetime created_at
    }
    
    AUDIO_FILE {
        int id
        int user_id
        int folder_id
        string filename
        string gcs_path
        string mime_type
        int duration_seconds
        datetime created_at
    }
    
    FOLDER {
        int id
        int user_id
        string name
        string description
        string color
        boolean is_default
        datetime created_at
    }
    
    NOTE {
        int id
        int user_id
        int audio_id
        string title
        string content
        datetime created_at
        datetime updated_at
    }
    
    NOTE_CHUNK {
        int id
        int note_id
        int audio_id
        string chunk_text
        vector embedding
        int start_time
        int end_time
    }
    
    CHATBOT_SESSION {
        int id
        int user_id
        int audio_id
        string title
        datetime created_at
    }
    
    CHATBOT_MESSAGE {
        int id
        int session_id
        string role
        string content
        datetime created_at
    }
    
    NOTIFICATION {
        int id
        int user_id
        string type
        string title
        string message
        boolean is_read
        datetime created_at
    }
    
    USER_DEVICE {
        int id
        int user_id
        string fcm_token
        string device_name
        string os
        datetime registered_at
    }
```

#### Diagram 8.2: Data Flow Through the System
Shows how data flows from input to storage.

```mermaid
graph LR
    A["User Input"] --> B["FastAPI<br/>Validation"]
    B --> C["Database<br/>Storage"]
    C --> D["Cache<br/>Redis"]
    D --> E["Search<br/>Vector DB"]
    E --> F["External API<br/>Processing"]
    F --> G["Result<br/>Storage"]
    G --> H["Return to<br/>User"]
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#ffe0b2
    style G fill:#fff3e0
    style H fill:#c8e6c9
```

---

## Implementation Instructions

### For Each Diagram File

#### Step 1: File Creation
Create a new markdown file in `docs/diagrams/` directory:
```
docs/diagrams/01_authentication_flows.md
docs/diagrams/02_audio_management_flows.md
docs/diagrams/03_async_task_processing.md
docs/diagrams/04_note_generation_flows.md
docs/diagrams/05_chatbot_interaction_flows.md
docs/diagrams/06_folder_organization_flows.md
docs/diagrams/07_notification_system_flows.md
docs/diagrams/08_database_relationships.md
```

#### Step 2: Content Structure for Each File
Each diagram file should follow this structure:

```markdown
# [Module Name] Diagrams

## Overview
[Brief description of what this module does]

## Flow Diagrams

### Flow X.1: [Flow Name]
[Description of the flow]

\`\`\`mermaid
[Mermaid flowchart code]
\`\`\`

### Flow X.2: [Next Flow Name]
[Description]

\`\`\`mermaid
[Mermaid code]
\`\`\`

## Sequence Diagrams

### Sequence X.3: [Complete Process Name]
[Description of participants and interactions]

\`\`\`mermaid
[Mermaid sequence diagram code]
\`\`\`

## Key Components
- List important services
- List important models
- List important endpoints

## Error Handling
- Common errors
- Retry mechanisms
- Fallback strategies

## Performance Notes
- Caching strategies
- Pagination
- Optimization tips
```

#### Step 3: Styling Conventions

Use these colors in your flowcharts for consistency:
- **Input/Start**: `fill:#e1f5ff` (Light Blue)
- **Processing**: `fill:#fff3e0` (Light Orange)
- **External/Async**: `fill:#ffe0b2` (Darker Orange)
- **Output/Success**: `fill:#c8e6c9` (Light Green)
- **Error/Failure**: `fill:#ffcdd2` (Light Red)
- **Critical**: `fill:#ff5252` (Red)

---

## Creating New Diagrams

### Mermaid Flowchart Syntax
```markdown
flowchart TD
    A["Node Label"] --> B["Another Node"]
    B --> C{Decision?}
    C -->|Yes| D["Success"]
    C -->|No| E["Failure"]
    
    style A fill:#e1f5ff
    style D fill:#c8e6c9
```

### Mermaid Sequence Diagram Syntax
```markdown
sequenceDiagram
    participant A
    participant B
    participant C
    
    A->>B: Message
    B->>C: Process
    C-->>B: Response
    B-->>A: Final Result
```

### Mermaid ER Diagram Syntax
```markdown
erDiagram
    ENTITY_A ||--o{ ENTITY_B : relationship
    
    ENTITY_A {
        type column_name
        type column_name
    }
```

---

## Integration with Documentation

### Referencing Diagrams
In other documentation files, reference diagrams like:

```markdown
See [Authentication Flow Diagram](diagrams/01_authentication_flows.md#flow-11-user-registration-flow)
for the complete registration process.
```

### Embedding in README
Add a summary section in main README:

```markdown
## System Architecture

### User Flows
- [Authentication](docs/diagrams/01_authentication_flows.md)
- [Audio Management](docs/diagrams/02_audio_management_flows.md)

### Processing Flows
- [Async Tasks](docs/diagrams/03_async_task_processing.md)
- [Audio Processing](docs/diagrams/02_audio_management_flows.md)

### Feature Flows
- [Notes](docs/diagrams/04_note_generation_flows.md)
- [Chatbot](docs/diagrams/05_chatbot_interaction_flows.md)
- [Folders](docs/diagrams/06_folder_organization_flows.md)
- [Notifications](docs/diagrams/07_notification_system_flows.md)

### Data Model
- [Database Schema](docs/diagrams/08_database_relationships.md)
```

---

## Best Practices

### Do's ✓
- Keep flows focused on a single feature
- Use clear, descriptive labels
- Include error paths in sequences
- Show data transformations
- Document external service calls
- Use consistent styling
- Break complex flows into multiple diagrams

### Don'ts ✗
- Don't overcrowd a single diagram
- Don't mix multiple unrelated processes
- Don't forget error handling
- Don't omit database operations
- Don't use ambiguous node names
- Don't ignore async operations
- Don't forget user verification/authorization

---

## Updating Diagrams

When the system changes:

1. **Identify affected diagrams**
   - List which flows are impacted
   - Check related sequences

2. **Update diagrams**
   - Modify flowchart nodes
   - Update sequence participants
   - Adjust decision points

3. **Update documentation**
   - Add notes about the change
   - Update version/date
   - Link to related changes

4. **Version control**
   - Commit diagram changes with code changes
   - Add descriptive commit messages

---

## Viewing Diagrams

### Online Tools
- **Mermaid Live Editor**: https://mermaid.live/
- **Mermaid Documentation**: https://mermaid.js.org/
- **GitHub**: Automatically renders in markdown files

### Local Rendering
1. Install Mermaid CLI:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```

2. Generate SVG:
   ```bash
   mmdc -i diagram.md -o diagram.svg
   ```

3. View in VS Code:
   - Install "Markdown Preview Mermaid Support" extension

---

## Testing Diagrams

Before publishing:

1. **Syntax Validation**
   - Paste code in https://mermaid.live/
   - Check for syntax errors

2. **Completeness Check**
   - All flows have start and end
   - All decision nodes have branches
   - All participants in sequences are used

3. **Accuracy Check**
   - Matches actual code implementation
   - Includes all error paths
   - Database operations are correct

4. **Clarity Review**
   - Ask colleague to review
   - Check for ambiguous labels
   - Verify styling is consistent

---

## Useful Examples

### Example 1: Simple API Endpoint Flow
```mermaid
flowchart TD
    A["Client Request"] --> B["API Handler"]
    B --> C["Validate Input"]
    C --> D{Valid?}
    D -->|No| E["Return 400 Error"]
    D -->|Yes| F["Process Request"]
    F --> G["Save to DB"]
    G --> H["Return 200 OK"]
    
    style A fill:#e1f5ff
    style F fill:#fff3e0
    style H fill:#c8e6c9
```

### Example 2: Async Task with Retry
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Queue as Redis Queue
    participant Worker
    participant ExternalService
    
    Client->>API: Request async operation
    API->>Queue: Enqueue task
    Queue-->>API: Task ID
    API-->>Client: 202 Accepted
    
    Worker->>Queue: Dequeue task
    Worker->>ExternalService: Call API
    ExternalService-->>Worker: Error
    Worker->>Queue: Re-enqueue with backoff
    Queue-->>Worker: Requeued
    
    Worker->>ExternalService: Retry call
    ExternalService-->>Worker: Success
    Worker->>Queue: Mark complete
```

---

## FAQ

**Q: Should I include all error cases?**
A: Yes, especially in sequence diagrams. Show common errors and how they're handled.

**Q: How detailed should diagrams be?**
A: Show the main flow clearly. Use separate diagrams for complex details.

**Q: Should I include database transaction details?**
A: Show key operations (create, read, update, delete) but don't overcomplicate.

**Q: How often should I update diagrams?**
A: Whenever the flow changes significantly, update diagrams before code review.

**Q: Can I use different colors?**
A: Yes, but maintain consistency across all diagrams.

---

## Support & Maintenance

- **Diagram Issues**: Check Mermaid documentation
- **Syntax Errors**: Use Mermaid Live Editor for debugging
- **Questions**: Refer to implementation code for details
- **Updates**: Keep version history in commit messages

---

**Document Version**: 1.0  
**Last Updated**: December 30, 2025  
**Maintained By**: Development Team
