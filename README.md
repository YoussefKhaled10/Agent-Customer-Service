# PharmaCare AI Sales & Customer Service Agent

PharmaCare is a Flask-based AI sales and customer service platform for a pharmacy-style business domain. The project combines a LangGraph agent, PostgreSQL business data, customer authentication, order operations, support workflows, an administration dashboard, and a document-grounded Retrieval-Augmented Generation pipeline.

The system follows three primary principles:

1. The LLM understands the request, selects actions, and writes natural responses.
2. Application code validates, authorizes, confirms, and controls execution.
3. Tools and the database are the only sources of business facts and operation results.

> The demonstration catalog and products are fictional. Document-grounded health information is informational only and is not personalized medical advice.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Business Domain](#business-domain)
- [Main Features](#main-features)
- [System Architecture](#system-architecture)
- [LangGraph Agent Flow](#langgraph-agent-flow)
- [Agent Components](#agent-components)
- [Available Tools](#available-tools)
- [Order and Confirmation Flow](#order-and-confirmation-flow)
- [RAG Pipeline](#rag-pipeline)
- [Database Design](#database-design)
- [Authentication and Authorization](#authentication-and-authorization)
- [Admin Dashboard](#admin-dashboard)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running the Application](#running-the-application)
- [API Usage](#api-usage)
- [Postman Verification](#postman-verification)
- [End-to-End Demo](#end-to-end-demo)
- [Grounding and Safety](#grounding-and-safety)
- [Error Handling](#error-handling)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)
- [Final Submission Checklist](#final-submission-checklist)

---

## Project Overview

PharmaCare provides two connected experiences:

- **Customer experience:** A conversational assistant for product discovery, customer-account support, order operations, support handoff, pharmacist requests, and document-grounded questions.
- **Administration experience:** A protected dashboard for managing products, categories, customers, orders, inquiries, pharmacist requests, conversations, tool executions, and RAG knowledge documents.

The agent is LLM-first. Every normal user message is interpreted by the decision LLM before a direct response, clarification, or tool call is selected. Sensitive operations remain protected by deterministic application logic.

---

## Business Domain

The project models a pharmacy and healthcare retail service. The platform supports:

- Browsing product categories.
- Searching products by text, category, price, and availability.
- Product recommendations based on needs and budget.
- Inventory checks for requested quantities.
- Customer registration and authentication.
- Customer profile and order lookup.
- Order creation with explicit confirmation.
- Order cancellation with explicit confirmation.
- Support inquiries and pharmacist contact requests.
- Document-grounded answers with citations.
- Administrative monitoring and management.

---

## Main Features

### Customer Features

- Registration and login.
- JWT-authenticated customer operations.
- Guest product and category browsing.
- Multilingual conversational requests.
- Egyptian Arabic response support.
- Product cards with prices, currencies, stock, SKUs, and images.
- Follow-up conversation context.
- Customer profile lookup.
- Customer order listing and order-status checks.
- Confirmation-controlled order creation and cancellation.
- Customer-support and pharmacist handoff.
- RAG answers grounded in indexed PDF documents.

### Admin Features

- Admin-only authorization.
- Overview dashboard.
- Category management.
- Product management.
- Customer management.
- Order management.
- Customer inquiry monitoring.
- Pharmacist request monitoring.
- Conversation inspection.
- Tool execution auditing.
- RAG knowledge document management.

### Engineering Features

- Flask backend and templates.
- SQLAlchemy ORM.
- PostgreSQL database.
- Alembic migrations.
- pgvector-based semantic retrieval.
- LangGraph orchestration.
- Structured JSON decisions.
- Tool schema validation.
- Duplicate tool-call protection.
- Maximum tool-iteration limits.
- Compact decision prompts.
- Separate compact final-response prompts.
- Deterministic fallback when the final LLM is unavailable.
- Safe error sanitization.

---

## System Architecture

```mermaid
flowchart LR
    USER[Customer or Admin] --> UI[Flask Templates and JavaScript]
    UI --> ROUTES[Flask Routes]
    ROUTES --> AUTH[Authentication and Authorization]
    ROUTES --> AGENT[AgentService]
    AGENT --> CONV[ConversationService]
    AGENT --> GRAPH[LangGraph]
    GRAPH --> DLLM[Decision LLM]
    GRAPH --> REGISTRY[Tool Registry]
    REGISTRY --> BTOOLS[Business Tools]
    REGISTRY --> RAGTOOL[Knowledge RAG Tool]
    BTOOLS --> DB[(PostgreSQL)]
    RAGTOOL --> RAGSERVICE[RAG Service]
    RAGSERVICE --> RETRIEVAL[Hybrid Retrieval and Reranking]
    RETRIEVAL --> VECTORDB[(PostgreSQL and pgvector)]
    GRAPH --> FLLM[Final Response LLM]
    FLLM --> AGENT
    AGENT --> ROUTES
```

### Responsibility Boundaries

- **Routes:** HTTP input validation and response serialization.
- **Authentication:** Customer identity and admin authorization.
- **AgentService:** Conversation lifecycle, pending actions, graph invocation, persistence, and API response construction.
- **LangGraph:** Decision routing, tool execution loops, confirmation routing, and final-response routing.
- **Tools:** Verified business reads and actions.
- **Models and services:** Database access and business rules.
- **RAG:** Ingestion, retrieval, reranking, context construction, answer generation, and citations.

---

## LangGraph Agent Flow

```mermaid
flowchart TD
    START([START]) --> SERVICE[Load Conversation, Authentication, and Pending Action]
    SERVICE --> PENDING{Pending Action Exists?}

    PENDING -->|No| DECISION[Decision LLM]
    PENDING -->|Yes| PA_LLM[Pending-Action Understanding LLM]

    PA_LLM -->|confirm| EXEC_PENDING[Execute Stored Action with Application Confirmation]
    PA_LLM -->|reject| CLEAR_PENDING[Clear Pending Action]
    PA_LLM -->|modify| MODIFY[Clarify or Safely Rebuild Modified Action]
    PA_LLM -->|unrelated| DECISION
    PA_LLM -->|unclear| CLARIFY_PENDING[Ask for Clear Confirmation]

    DECISION -->|direct_response| RESPONSE[Response Node]
    DECISION -->|clarification| RESPONSE
    DECISION -->|tool_call| VALIDATE[Validate Tool Call]
    DECISION -->|error| ERROR[Safe Error Node]

    VALIDATE -->|invalid| ERROR
    VALIDATE -->|authentication required| RESPONSE
    VALIDATE -->|confirmation required| STORE_PENDING[Store Pending Action]
    VALIDATE -->|valid| EXECUTE[Execute Tool]

    EXECUTE --> RESULT{Evaluate Tool Result}
    RESULT -->|more data required| DECISION
    RESULT -->|confirmation required| STORE_PENDING
    RESULT -->|sufficient successful data| COMPACT[Compact Successful Tool Results]
    RESULT -->|recoverable failure| DECISION
    RESULT -->|terminal failure| RESPONSE
    RESULT -->|iteration limit| LIMIT[Limit Node]

    STORE_PENDING --> RESPONSE
    EXEC_PENDING --> COMPACT
    CLEAR_PENDING --> FINAL[Final Response LLM]
    MODIFY --> RESPONSE
    CLARIFY_PENDING --> RESPONSE
    COMPACT --> FINAL

    FINAL -->|success| RESPONSE
    FINAL -->|provider failure| FALLBACK[Safe Deterministic Fallback]
    FALLBACK --> RESPONSE

    RESPONSE --> SAVE[Save Messages, Pending State, and Tool Audit]
    ERROR --> SAVE
    LIMIT --> SAVE
    SAVE --> END([END])
```

### Decision Types

The decision LLM returns one structured action:

- `tool_call`
- `direct_response`
- `clarification`
- `error`

### Pending-Action Decisions

When an action is already awaiting confirmation, a compact LLM prompt classifies the next message as:

- `confirm`
- `reject`
- `modify`
- `unrelated`
- `unclear`

The LLM identifies the user's intent, but the application controls whether and how the stored action is executed.

---

## Agent Components

### `src/agent/AgentGraph.py`

Defines LangGraph nodes and transitions.

### `src/agent/AgentNodes.py`

Implements decision generation, tool execution, final-response generation, response handling, iteration limits, and safe errors.

### `src/agent/AgentRouter.py`

Maps decision types to graph paths.

### `src/agent/AgentState.py`

Defines the state shared between nodes, including messages, selected tools, tool results, iterations, pending actions, and final responses.

### `src/agent/AgentPrompts.py`

Contains compact decision prompts, pending-action prompts, final-response prompts, grounding rules, and tool-result compaction.

### `src/services/AgentService.py`

Coordinates conversation persistence, authentication context, pending-action handling, graph execution, tool auditing, and API responses.

### `src/services/ConversationService.py`

Loads and stores conversations, messages, and pending actions.

### `src/services/ToolExecutionService.py`

Validates and executes tools while enforcing authentication and confirmation requirements.

### `src/services/ToolBootstrapService.py`

Registers the tools available to the agent.

---

## Available Tools

### Catalog and Sales

- `category_list`
- `product_search`
- `product_details`
- `sales_recommendation`
- `inventory_check`

### Customer

- `customer_lookup`
- `customer_orders`

### Orders

- `order_status`
- `order_details`
- `order_creation`
- `order_cancellation`

### Support

- `human_handoff`

### Knowledge

- `knowledge_rag`

### Tool Security Rules

- Customer identity comes from the authenticated application context.
- The LLM must not generate `customer_id`, `user_id`, access tokens, confirmation flags, database prices, current stock, order totals, or roles.
- Prices, stock, categories, products, customers, orders, and operation states come from tools.
- Confirmation-sensitive tools are never executed before explicit approval.
- Identical tool calls are blocked within the same graph run.

---

## Order and Confirmation Flow

```mermaid
flowchart TD
    ORDER_REQUEST[User Requests Product and Quantity] --> SEARCH[product_search]
    SEARCH --> INVENTORY[inventory_check]
    INVENTORY -->|insufficient| NO_STOCK[Grounded Availability Response]
    INVENTORY -->|available| PROFILE[Use Authenticated Customer Context]
    PROFILE --> PREPARE[Select order_creation]
    PREPARE --> PENDING[Store Pending Action]
    PENDING --> ASK[Ask for Confirmation]
    ASK --> USER_REPLY[User Replies Naturally]
    USER_REPLY --> PA_LLM[Pending-Action LLM]
    PA_LLM -->|confirm| CREATE[Execute order_creation with confirmed=true]
    PA_LLM -->|reject| CANCEL_PENDING[Clear Pending Action]
    PA_LLM -->|modify| REBUILD[Re-check Product, Quantity, and Inventory]
    CREATE --> DB_ORDER[(Create Order and Items)]
    DB_ORDER --> UPDATE_STOCK[Update Stock]
    UPDATE_STOCK --> CLEAR[Clear Pending Action]
    CLEAR --> FINAL[Final Response LLM]
```

### Order Safety

- No order is created before confirmation.
- The pending action stores only validated operation arguments.
- The backend retrieves product prices and calculates totals.
- Product rows are locked during order creation when required.
- `idempotency_key` protects against accidental duplicate execution.
- A success response requires a successful `order_creation` result.
- Repeated confirmation after completion must not create another order.

---

## RAG Pipeline

The RAG system has two major flows.

### Ingestion

```mermaid
flowchart TD
    PDF[PDF Upload] --> VALIDATE[Validate Type and Size]
    VALIDATE --> EXTRACT[Layout-aware Extraction]
    EXTRACT --> REFINE[Refine Document Blocks]
    REFINE --> CHUNK[Model-assisted Chunk Planning]
    CHUNK --> POST[Post-process and Deduplicate]
    POST --> EMBED[Generate Embeddings]
    EMBED --> STORE[(Knowledge Documents and Chunks)]
    STORE --> INDEXED[Indexed and Searchable]
```

### Retrieval and Generation

```mermaid
flowchart TD
    Q[Question] --> PREP[Query Preparation and Language Detection]
    PREP --> QEMBED[Generate Query Embedding]
    QEMBED --> SEM[Semantic Search]
    PREP --> KEY[Keyword Search]
    SEM --> FUSION[Hybrid Fusion]
    KEY --> FUSION
    FUSION --> RERANK[Reranking]
    RERANK --> EVIDENCE[Evidence Selection]
    EVIDENCE --> CONTEXT[Token-limited Context]
    CONTEXT --> GENERATE[Grounded Answer Generation]
    GENERATE --> CITE[Sources and Citation Validation]
```

### Verified RAG Behavior

The complete RAG pipeline has been tested with:

- Direct factual questions.
- Semantic questions.
- Arabic questions over English documents.
- Multi-chunk questions.
- Citation markers such as `[S1]`, `[S2]`, and `[S3]`.
- Context token budgets.

### Knowledge Administration

The admin knowledge area supports or is designed to support:

- PDF upload.
- Document listing and filtering.
- Document details.
- Chunk inspection.
- Activation and deactivation.
- Re-indexing.
- Metadata editing.
- Safe PDF replacement.
- Document deletion.

Inactive or non-indexed documents must be excluded from retrieval.

---

## Database Design

The system uses PostgreSQL with SQLAlchemy ORM and pgvector.

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ CONVERSATION : owns
    CUSTOMER ||--o{ CUSTOMER_INQUIRY : creates
    CUSTOMER ||--o{ PHARMACIST_REQUEST : creates
    CATEGORY ||--o{ PRODUCT : contains
    ORDER ||--|{ ORDER_ITEM : includes
    PRODUCT ||--o{ ORDER_ITEM : referenced_by
    CONVERSATION ||--o{ MESSAGE : contains
    CONVERSATION ||--o{ TOOL_EXECUTION : records
    MESSAGE ||--o{ TOOL_EXECUTION : triggers
    KNOWLEDGE_DOCUMENT ||--o{ KNOWLEDGE_CHUNK : contains
```

### Main Tables

- `customers`
- `categories`
- `products`
- `orders`
- `order_items`
- `conversations`
- `messages`
- `tool_executions`
- `customer_inquiries`
- `pharmacist_requests`
- `knowledge_documents`
- `knowledge_chunks`
- `alembic_version`

### Important Integrity Rules

- Customer email addresses must be unique.
- Product SKUs must be unique.
- Order items preserve product name, SKU, and price snapshots.
- Stock values must not become invalid.
- Customer conversation and order ownership must be enforced.
- Knowledge chunks belong to one knowledge document.
- Deactivation should not delete chunks.
- Final deletion should remove related chunks according to configured cascade rules.

---

## Authentication and Authorization

### Customer Authentication

Protected API requests use:

```http
Authorization: Bearer <access_token>
```

The backend extracts customer identity from the verified token. Customer IDs from request bodies or model-generated arguments are not trusted.

### Admin Authorization

An active admin account has:

```text
role = admin
is_active = true
```

Expected behavior:

- Guest access to `/admin`: rejected or redirected.
- Authenticated customer with `role=customer`: forbidden.
- Active admin: allowed.
- Inactive admin: rejected.

Hiding the Admin navigation link is not a substitute for backend authorization.

---

## Admin Dashboard

Main sections include:

- `/admin`
- `/admin/categories`
- `/admin/products`
- `/admin/customers`
- `/admin/orders`
- `/admin/inquiries`
- `/admin/pharmacist-requests`
- `/admin/conversations`
- `/admin/tool-executions`
- `/admin/knowledge`

The administration interface supports operational management, auditing, and knowledge maintenance.

---

## Project Structure

```text
.
├── main.py
├── alembic.ini
├── requirements.txt
├── README.md
├── .env.example
├── src/
│   ├── agent/
│   │   ├── AgentGraph.py
│   │   ├── AgentNodes.py
│   │   ├── AgentRouter.py
│   │   ├── AgentState.py
│   │   ├── AgentPrompts.py
│   │   ├── AgentResponseFormatter.py
│   │   └── CatalogResponseFormatter.py
│   ├── helpers/
│   ├── ingestion/
│   ├── models/
│   ├── retrieval/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   ├── stores/
│   └── tools/
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── migrations/
├── tests/
└── uploads/
    └── knowledge/
```

---

## Prerequisites

- Python 3.12 or a compatible supported version.
- PostgreSQL.
- pgvector extension.
- Python virtual environment.
- Valid credentials for configured LLM, embedding, reranking, and chunk-planning providers.
- Postman for API verification is recommended.

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create a Virtual Environment

```bash
python -m venv agent
source agent/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create the Environment File

```bash
cp .env.example .env
```

Never commit `.env`.

### 5. Create the Database

```sql
CREATE DATABASE pharmacare_db;
```

Enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 6. Apply Migrations

```bash
python -m alembic upgrade head
```

### 7. Run Tests

```bash
python -m pytest tests -q
```

### 8. Start the Application

```bash
python main.py
```

Default local address:

```text
http://127.0.0.1:5001
```

---

## Environment Variables

The exact environment-variable names must match `src/helpers/config.py`.

Example template:

```env
APP_NAME=PharmaCare
APP_VERSION=1.0.0
APP_HOST=0.0.0.0
APP_PORT=5001
DEBUG=true

SECRET_KEY=replace-with-a-long-random-value
JWT_SECRET_KEY=replace-with-a-different-long-random-value

DATABASE_URL=postgresql+psycopg://postgres:password@127.0.0.1:5432/pharmacare_db

AGENT_PROVIDER=groq
AGENT_MODEL=openai/gpt-oss-120b
AGENT_MAX_TOOL_ITERATIONS=5
GROQ_API_KEY=

GEMINI_API_KEY=
COHERE_API_KEY=

KNOWLEDGE_UPLOAD_DIR=uploads/knowledge
MAX_KNOWLEDGE_FILE_SIZE_MB=20
```

Before submission, compare `.env.example` against the configuration class and remove or rename variables not used by the implementation.

---

## Database Migrations

Inspect current migration status:

```bash
python -m alembic current
python -m alembic heads
python -m alembic history
```

Apply migrations:

```bash
python -m alembic upgrade head
```

Create a revision after ORM changes:

```bash
python -m alembic revision \
  --autogenerate \
  -m "describe the schema change"
```

Review generated revisions before applying them. Do not rely on manual database changes that are absent from version-controlled migrations.

---

## Running the Application

```bash
python main.py
```

Health check:

```http
GET /health
```

The Flask development server is intended only for local development. Use a production WSGI server and secure production configuration for deployment.

---

## API Usage

### Agent Chat

```http
POST /api/agent/chat
Content-Type: application/json
```

```json
{
  "message": "وريني المنتجات المتاحة في فئة العناية الشخصية",
  "session_id": "demo-agent-001"
}
```

### Authenticated Agent Request

```http
POST /api/agent/chat
Content-Type: application/json
Authorization: Bearer <access_token>
```

### Direct RAG Tool Test

Use the tool execution endpoint implemented by the project to invoke:

```json
{
  "tool_name": "knowledge_rag",
  "arguments": {
    "query": "Who is the author of the document?",
    "document_id": 13
  },
  "request_id": "rag-test-001",
  "confirmed": false,
  "metadata": {
    "test_type": "full_rag_pipeline"
  }
}
```

### Retrieval Debug Test

Development-only retrieval endpoint:

```http
POST /api/retrieval/search
Content-Type: application/json
```

```json
{
  "query": "What psychological treatments are mentioned?",
  "document_id": 13,
  "candidate_limit": 10,
  "final_limit": 5
}
```

The debug endpoint should not be exposed in production because raw chunks and scores may reveal indexed content.

---

### Required Verification Areas

- Direct LLM response.
- Clarification.
- Catalog routing.
- Multi-tool execution.
- Conversation follow-ups.
- Authentication-required tools.
- Order confirmation and pending actions.
- Duplicate confirmation protection.
- Customer service tools.
- RAG routing through the agent.
- Grounded final responses.
- Duplicate tool-call protection.
- Maximum iteration protection.
- Provider failure handling.
- Final-response fallback.

---

## Postman Verification

### Guest Session

Use:

```text
agent-e2e-guest-001
```

Messages:

```text
1. عامل إيه؟
2. أنا محتاج حاجة مناسبة
3. عاوز أشوف الفئات المتاحة
4. وريني المنتجات المتاحة في فئة العناية الشخصية
5. إيه الفرق بينهم واختارلي الأرخص؟
6. وريني بيانات حسابي وطلباتي
```

### Authenticated Session

After login, use:

```text
agent-e2e-customer-001
```

Messages:

```text
1. وريني بيانات حسابي
2. عاوز أطلب قطعتين من CareCheck Digital Thermometer
3. عنوان الشحن: Alexandria
4. أيوه تمام، نفذ الطلب
5. أكد الطلب
6. وريني طلباتي
7. والطلب الأخير وصل لفين؟
8. عندي مشكلة في الطلب وعاوز أكلم خدمة العملاء
9. محتاج أتواصل مع صيدلي بخصوص استفسار عام
10. حسب المستند، مين المؤلف المذكور في ملف اضطراب استخدام الكحول؟
11. سيبنا من المستند، وريني الفئات المتاحة في الكتالوج
12. عاوز حاجة للحساسية الدوائية
```

### Business-Action Success Rule

Do not consider an order created because the LLM says so. Order creation is successful only if:

- `order_creation` appears as a successful tool result.
- A real order exists in the database.
- The returned order number and totals match persisted data.

### Generic Postman Tests

```javascript
pm.test("HTTP status is 200", function () {
    pm.response.to.have.status(200);
});

const body = pm.response.json();

pm.test("Execution completed", function () {
    pm.expect(body.requires_tool_execution).to.eql(false);
});

pm.test("No sensitive internal error leaked", function () {
    const raw = JSON.stringify(body);

    [
        "Traceback",
        "sqlalchemy",
        "organization",
        "billing",
        "API key",
        "database connection"
    ].forEach(value => {
        pm.expect(raw).not.to.include(value);
    });
});
```

---

## End-to-End Demo

Recommended demonstration:

1. Run migrations on a clean database.
2. Create and promote an admin account.
3. Log in to the admin dashboard.
4. Add categories and fictional products.
5. Upload and index a PDF.
6. Register a separate customer.
7. Browse categories through the agent.
8. Browse products in a selected category.
9. Compare products using catalog facts only.
10. Check a requested product quantity.
11. Prepare an order and show that confirmation is required.
12. Confirm the order with a natural user message.
13. Show the created order and changed stock.
14. Send a second confirmation and prove no duplicate order is created.
15. View customer orders.
16. Ask for the latest order status.
17. Create a customer inquiry.
18. Create a pharmacist request.
19. Ask a document-grounded RAG question.
20. Verify source citations.
21. Inspect conversation and tool-execution records in the admin dashboard.

---

## Grounding and Safety

### Catalog Grounding

Final responses may organize and translate facts from successful tool results, but must not invent missing product properties.

Allowed catalog facts include returned fields such as:

- Product name.
- Brand.
- Price.
- Currency.
- Available stock.
- SKU.
- Short or full description.
- Explicit returned features and warnings.

The LLM must not infer:

- Ingredients.
- Antibacterial or antiviral effectiveness.
- Suitability for sensitive skin.
- Scent, texture, or packaging.
- Clinical or treatment benefits.
- Medical safety or certification.

### Identifier Preservation

Registered names, SKUs, order numbers, and technical identifiers should remain exactly as returned by tools. Unicode punctuation substitutions should be avoided in identifiers.

### RAG Grounding

- Answers use retrieved document context only.
- Citation markers are preserved.
- Unsupported document questions must not be answered from general model knowledge.
- Document information must not be converted into personalized treatment advice.

### Operational Grounding

- Prices and stock come from tools.
- Customer identity comes from authentication context.
- Totals are calculated by backend code.
- Confirmation-sensitive actions require a stored pending action and explicit user approval.
- Success claims require successful operation tool results.

---

## Error Handling

Recommended public error codes include:

```text
agent_generation_unavailable
authentication_required
authorization_forbidden
confirmation_required
no_pending_action
category_not_found
product_not_found
insufficient_stock
duplicate_tool_call
maximum_tool_iterations_reached
knowledge_unavailable
```

Provider errors must be logged server-side, while clients receive safe messages. Never expose:

- API keys.
- Provider organization IDs.
- Billing URLs.
- Raw rate-limit payloads.
- SQL statements.
- Tracebacks.
- Database connection details.

If a final-response LLM request fails after a successful tool result, the system should use a grounded deterministic fallback rather than returning an error alongside successful UI cards.

---

## Known Limitations

- An LLM-first architecture requires a provider call even for simple greetings.
- Provider token and rate limits can temporarily block the first decision call.
- Product comparison depth depends on catalog-description quality.
- Structured product context should be reused or re-retrieved for follow-up comparisons.
- Natural pending-action modifications should trigger fresh inventory and confirmation checks.
- Synchronous RAG ingestion may be slow for large documents.
- The Flask development server is not suitable for production.
- Retrieval thresholds for unsupported questions should be calibrated with a larger evaluation dataset.

---


## Repository Hygiene

Recommended `.gitignore` entries:

```gitignore
.env
*.dump
*.log
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
agent/
.venv/
venv/

uploads/knowledge/*
!uploads/knowledge/.gitkeep

*_backup_*/
*.before_*
*.zip
```

Before submission:

```bash
git status
python -m pytest tests -q
python -m alembic current
python -m alembic heads
```

---




## License and Data Notice

Add the intended repository license before public distribution. Use only authorized documents, product images, and business data. Do not commit confidential customer information, provider credentials, copyrighted documents without permission, or production database exports.
