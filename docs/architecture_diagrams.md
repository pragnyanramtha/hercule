# Hercule Backend Architecture & System Flows

A comprehensive technical documentation of the Hercule Privacy Policy Analyzer's distributed backend infrastructure.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        EXT["Chrome Extension<br/>React + TypeScript"]
    end
    
    subgraph "Azure Cloud Infrastructure"
        subgraph "Compute Layer"
            AF["Azure Functions V2<br/>Serverless ASGI Runtime"]
            FAST["FastAPI Application<br/>Async HTTP Handler"]
        end
        
        subgraph "Persistence Layer"
            COSMOS[("Azure Cosmos DB<br/>NoSQL Document Store<br/>Geo-Replicated")]
        end
    end
    
    subgraph "External Intelligence Services"
        OR["OpenRouter API Gateway"]
        GROQ["Groq Cloud Inference"]
        
        subgraph "Large Language Models"
            NEM["NVIDIA Nemotron<br/>30B A3B"]
            COMP["Groq Compound<br/>Web-Enabled"]
            LLAMA["LLaMA 3.3<br/>70B Versatile"]
            KIMI["Moonshot Kimi K2<br/>Instruct"]
        end
    end
    
    subgraph "Discovery Services"
        DDG["DuckDuckGo<br/>Privacy Search"]
        GOOG["Google Custom<br/>Search API"]
    end
    
    EXT -->|"HTTPS REST"| AF
    AF --> FAST
    FAST -->|"Cache Lookup/Store"| COSMOS
    FAST -->|"Primary Inference"| OR
    FAST -->|"Fallback Inference"| GROQ
    OR --> NEM
    GROQ --> COMP
    GROQ --> LLAMA
    GROQ --> KIMI
    FAST -->|"Policy Discovery"| DDG
    FAST -->|"Fallback Search"| GOOG
```

---

## 2. Request Processing Pipeline

```mermaid
flowchart TD
    START(["Incoming HTTP Request"]) --> PARSE["Request Deserialization<br/>Pydantic Schema Validation"]
    
    PARSE --> CACHE_URL{"Multi-Tier Cache<br/>Interrogation"}
    
    CACHE_URL -->|"URL Hash Match"| CACHE_HIT_URL["Cache Materialization<br/>via URL Signature"]
    CACHE_URL -->|"Miss"| CACHE_DOMAIN{"Domain-Level<br/>Cache Probe"}
    
    CACHE_DOMAIN -->|"Domain Hash Match"| CACHE_HIT_DOM["Cache Materialization<br/>via Domain Signature"]
    CACHE_DOMAIN -->|"Miss"| DISCOVERY["Initiate Discovery<br/>Protocol"]
    
    CACHE_HIT_URL --> RETURN["Response Serialization<br/>& Transmission"]
    CACHE_HIT_DOM --> RETURN
    
    DISCOVERY --> CONCURRENT["Concurrent Execution<br/>Strategy"]
    
    subgraph "Parallel Discovery Operations"
        CONCURRENT --> PATH_ENUM["Path Enumeration<br/>25+ Common Endpoints"]
        CONCURRENT --> SCRAPE["Homepage Scraping<br/>Link Extraction"]
        CONCURRENT --> DDG_SEARCH["DuckDuckGo<br/>Site-Specific Query"]
    end
    
    PATH_ENUM --> AGGREGATE["Result Aggregation<br/>& Prioritization"]
    SCRAPE --> AGGREGATE
    DDG_SEARCH --> AGGREGATE
    
    AGGREGATE -->|"Policy Located"| EXTRACT["Content Extraction<br/>& Normalization"]
    AGGREGATE -->|"Timeout/Failure"| LLM_FALLBACK["LLM Fallback Chain<br/>Initiation"]
    
    EXTRACT --> TEXT_CACHE{"Text-Based<br/>Cache Lookup"}
    
    TEXT_CACHE -->|"Hit"| CACHE_HIT_TEXT["Cache Materialization<br/>via Content Hash"]
    TEXT_CACHE -->|"Miss"| LLM_ANALYSIS["LLM Analysis<br/>Pipeline"]
    
    CACHE_HIT_TEXT --> RETURN
    
    LLM_ANALYSIS --> PERSIST["Multi-Key Cache<br/>Persistence"]
    LLM_FALLBACK --> PERSIST
    
    PERSIST --> RETURN
```

---

## 3. LLM Fallback Chain Architecture

```mermaid
flowchart LR
    subgraph "Model Prioritization Strategy"
        direction TB
        
        M1["1. NVIDIA Nemotron 3<br/>30B A3B Free Tier<br/>━━━━━━━━━━━━━<br/>Provider: OpenRouter<br/>Context: 1M chars<br/>Latency: ~8s"]
        
        M2["2. Groq Compound<br/>Web-Enabled Search<br/>━━━━━━━━━━━━━<br/>Provider: Groq<br/>Context: 70K chars<br/>Latency: ~5s"]
        
        M3["3. LLaMA 3.3<br/>70B Versatile<br/>━━━━━━━━━━━━━<br/>Provider: Groq<br/>Context: 12K chars<br/>Latency: ~3s"]
        
        M4["4. Groq Compound Mini<br/>Lightweight Inference<br/>━━━━━━━━━━━━━<br/>Provider: Groq<br/>Context: 70K chars<br/>Latency: ~2s"]
        
        M5["5. Moonshot Kimi K2<br/>Last Resort Fallback<br/>━━━━━━━━━━━━━<br/>Provider: Groq<br/>Context: 10K chars<br/>Mode: Website-Only"]
    end
    
    M1 -->|"429 Rate Limit<br/>or Failure"| M2
    M2 -->|"429 Rate Limit<br/>or Failure"| M3
    M3 -->|"429 Rate Limit<br/>or Failure"| M4
    M4 -->|"429 Rate Limit<br/>or Failure"| M5
    
    M1 -->|"Success"| OUT(["Analysis Result"])
    M2 -->|"Success"| OUT
    M3 -->|"Success"| OUT
    M4 -->|"Success"| OUT
    M5 -->|"Success"| OUT
```

---

## 4. API Key Rotation & Management

```mermaid
stateDiagram-v2
    [*] --> KeyPoolInitialization
    
    KeyPoolInitialization --> LoadFromPersistence: Load keys.json
    LoadFromPersistence --> PrimarySelection: Select Current Index
    
    state "Active Key Usage" as Active {
        PrimarySelection --> RequestExecution
        RequestExecution --> IncrementCounter: Track Usage Metrics
    }
    
    IncrementCounter --> RateLimitCheck: Monitor Response
    
    RateLimitCheck --> MarkLimited: HTTP 429 Detected
    RateLimitCheck --> PrimarySelection: Continue with Current
    
    MarkLimited --> RotateIndex: Advance Pool Index
    RotateIndex --> NextKeySelection: Select Non-Limited Key
    
    NextKeySelection --> PoolExhausted: All Keys Limited
    NextKeySelection --> RequestExecution: Retry with New Key
    
    PoolExhausted --> CooldownReset: Clear Rate Limit Flags
    CooldownReset --> PrimarySelection: Wrap to First Key
    
    state UserKeyInjection {
        [*] --> ValidateKey
        ValidateKey --> AddToPool: Deduplicate & Persist
        AddToPool --> UpdateKeysJson: Persist to Storage
    }
```

---

## 5. Caching Strategy & Data Flow

```mermaid
flowchart TB
    subgraph "Cache Key Generation"
        URL["Input URL"] --> NORMALIZE["URL Normalization<br/>Strip Protocol, WWW"]
        NORMALIZE --> DOMAIN_EXTRACT["Domain Extraction<br/>Base Domain Isolation"]
        
        TEXT["Policy Text"] --> TEXT_NORM["Text Normalization<br/>Lowercase, Trim"]
        
        NORMALIZE --> SHA_URL["SHA-256 Hash<br/>URL Signature"]
        DOMAIN_EXTRACT --> SHA_DOMAIN["SHA-256 Hash<br/>Domain Signature"]
        TEXT_NORM --> SHA_TEXT["SHA-256 Hash<br/>Content Signature"]
        
        SHA_URL --> KEY_URL["url:abc123..."]
        SHA_DOMAIN --> KEY_DOMAIN["domain:def456..."]
        SHA_TEXT --> KEY_TEXT["789xyz..."]
    end
    
    subgraph "Storage Backend Selection"
        ENV["STORAGE_MODE<br/>Environment Variable"]
        
        ENV -->|"local"| JSON_CACHE[("cache.json<br/>Local File Store")]
        ENV -->|"cosmos"| COSMOS_CACHE[("Azure Cosmos DB<br/>NoSQL Container")]
    end
    
    subgraph "Cache Operations"
        GET["cache.get(key)"] --> TTL_CHECK{"TTL Validation<br/>30-Day Expiry"}
        TTL_CHECK -->|"Valid"| DESERIALIZE["Document<br/>Deserialization"]
        TTL_CHECK -->|"Expired"| EVICT["Cache Eviction"]
        
        SET["cache.set(key, result)"] --> SERIALIZE["Document<br/>Serialization"]
        SERIALIZE --> UPSERT["Upsert Operation<br/>Create/Update"]
    end
    
    KEY_URL --> GET
    KEY_DOMAIN --> GET
    KEY_TEXT --> GET
    
    DESERIALIZE --> RESULT["AnalysisResult<br/>Object"]
    UPSERT --> COSMOS_CACHE
```

---

## 6. Privacy Policy Discovery Protocol

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Handler
    participant Discovery as DiscoveryService
    participant HTTPClient as Async HTTP Client
    participant Search as Search Engines
    participant LLM as LLM Fallback
    
    Client->>API: POST /analyze {url}
    
    API->>API: Cache Interrogation (URL + Domain)
    
    alt Cache Hit
        API-->>Client: Cached AnalysisResult
    end
    
    API->>Discovery: discover_and_extract(url)
    
    par Concurrent Discovery Strategy
        Discovery->>HTTPClient: Check 25+ Common Paths
        Note right of HTTPClient: /privacy<br/>/privacy-policy<br/>/legal/privacy<br/>/terms/privacy
        
        Discovery->>HTTPClient: Scrape Homepage
        Note right of HTTPClient: Extract <a> elements<br/>Match privacy keywords
        
        Discovery->>Search: DuckDuckGo Site Search
        Note right of Search: site:domain.com<br/>privacy policy
    end
    
    HTTPClient-->>Discovery: Policy Candidates
    Search-->>Discovery: Search Results
    
    Discovery->>Discovery: Result Prioritization
    
    alt Policy Found
        Discovery-->>API: PolicyText + URL
        API->>API: Generate Content Hash
        API->>API: LLM Analysis
    else Discovery Timeout (10s)
        Discovery-->>API: Failure
        API->>LLM: Fallback Chain Activation
        LLM-->>API: Web-Search Analysis
    end
    
    API->>API: Multi-Key Cache Persistence
    API-->>Client: AnalysisResult
```

---

## 7. Component Dependency Graph

```mermaid
graph LR
    subgraph "Entry Points"
        FUNC["function_app.py<br/>Azure Functions"]
        MAIN["main.py<br/>FastAPI App"]
    end
    
    subgraph "Core Services"
        LLM_SVC["service_llm.py<br/>LLMService"]
        DISC_SVC["service_discovery.py<br/>DiscoveryService"]
    end
    
    subgraph "Data Management"
        CACHE["cache.py<br/>CacheManager"]
        COSMOS["cache_cosmos.py<br/>CosmosDBCacheManager"]
        KEYS["api_key_manager.py<br/>APIKeyManager"]
    end
    
    subgraph "Models & Types"
        MODELS["models.py<br/>AnalysisResult<br/>ActionItem"]
    end
    
    subgraph "External Dependencies"
        GROQ_SDK["groq<br/>Python SDK"]
        HTTPX["httpx<br/>Async HTTP"]
        COSMOS_SDK["azure-cosmos<br/>SDK"]
        BS4["beautifulsoup4<br/>HTML Parser"]
    end
    
    FUNC --> MAIN
    MAIN --> LLM_SVC
    MAIN --> DISC_SVC
    MAIN --> CACHE
    
    LLM_SVC --> KEYS
    LLM_SVC --> MODELS
    LLM_SVC --> GROQ_SDK
    LLM_SVC --> HTTPX
    
    DISC_SVC --> HTTPX
    DISC_SVC --> BS4
    
    CACHE --> COSMOS
    COSMOS --> COSMOS_SDK
    CACHE --> MODELS
```

---

## 8. Data Transformation Pipeline

```mermaid
flowchart LR
    subgraph "Input Processing"
        RAW["Raw Policy Text<br/>~50KB Average"]
        URL["Source URL"]
    end
    
    subgraph "Preprocessing"
        TRUNC["Context Truncation<br/>Model-Specific Limits"]
        NORM["Text Normalization<br/>Unicode Handling"]
        PROMPT["System Prompt<br/>Construction"]
    end
    
    subgraph "LLM Inference"
        API_CALL["API Request<br/>JSON Payload"]
        INFERENCE["Model Inference<br/>~5-30 seconds"]
        JSON_PARSE["Response Parsing<br/>Schema Validation"]
    end
    
    subgraph "Output Processing"
        SCORE["Privacy Score<br/>0-100 Scale"]
        FLAGS["Red Flags<br/>Array Extraction"]
        ACTIONS["Action Items<br/>URL Generation"]
        MAILTO["Mailto Links<br/>URL Encoding"]
    end
    
    subgraph "Persistence"
        RESULT["AnalysisResult<br/>Pydantic Model"]
        CACHE_STORE["Multi-Key<br/>Cache Storage"]
    end
    
    RAW --> TRUNC
    URL --> PROMPT
    TRUNC --> NORM
    NORM --> PROMPT
    
    PROMPT --> API_CALL
    API_CALL --> INFERENCE
    INFERENCE --> JSON_PARSE
    
    JSON_PARSE --> SCORE
    JSON_PARSE --> FLAGS
    JSON_PARSE --> ACTIONS
    ACTIONS --> MAILTO
    
    SCORE --> RESULT
    FLAGS --> RESULT
    MAILTO --> RESULT
    
    RESULT --> CACHE_STORE
```

---

## Technical Specifications

| Component | Technology | Specification |
|-----------|------------|---------------|
| **Runtime** | Azure Functions V2 | Python 3.11, ASGI |
| **Framework** | FastAPI | Async/Await, Pydantic |
| **Primary LLM** | NVIDIA Nemotron 3 | 30B parameters, 1M context |
| **Cache Backend** | Azure Cosmos DB | NoSQL, Serverless, Geo-distributed |
| **Hash Algorithm** | SHA-256 | 256-bit cryptographic digest |
| **TTL Policy** | 30 days | Configurable via CACHE_TTL_DAYS |
| **Concurrency** | asyncio | Non-blocking I/O operations |
| **Serialization** | JSON | Pydantic model_dump() |

---

*Generated for Hercule Privacy Policy Analyzer - Imagine Cup 2026*
