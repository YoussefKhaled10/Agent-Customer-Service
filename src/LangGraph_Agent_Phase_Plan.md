# مرحلة بناء الـAgent باستخدام LangGraph

## 1. هدف المرحلة

تهدف هذه المرحلة إلى تحويل النظام من مجموعة خدمات وأدوات يتم استدعاؤها يدويًا إلى Agent ذكي يستطيع:

- فهم رسالة المستخدم المكتوبة باللغة الطبيعية.
- اختيار الأداة المناسبة تلقائيًا.
- تجهيز مدخلات الأداة بصورة صحيحة.
- تنفيذ أداة واحدة أو أكثر عند الحاجة.
- التعامل مع تسجيل الدخول والصلاحيات.
- إيقاف العمليات الحساسة لحين تأكيد المستخدم.
- الحفاظ على سياق المحادثة.
- تكوين رد نهائي واضح اعتمادًا على نتائج الأدوات الحقيقية.

الـAgent لن يعيد تنفيذ منطق الـRAG أو المنتجات أو الطلبات. الـAgent سيكون طبقة تنظيم وتشغيل فوق الأدوات الموجودة بالفعل.

---

## 2. لماذا نستخدم LangGraph؟

سنستخدم **LangGraph** لأنه يسمح ببناء Workflow واضح مكوّن من Nodes وEdges، بدل الاعتماد على استدعاء واحد للـLLM.

LangGraph مناسب للمشروع لأنه يدعم:

- توجيه الطلبات بين مسارات مختلفة.
- تنفيذ الأدوات في Loop منظم.
- تحديد حد أقصى لعدد مرات التنفيذ.
- حفظ حالة المحادثة.
- إيقاف التنفيذ لانتظار تأكيد المستخدم.
- استكمال نفس العملية بعد وصول التأكيد.
- التعامل مع الأخطاء ومسارات الفشل بوضوح.

---

## 3. الـFlow العام للـAgent

```text
User Message
↓
Load Conversation
↓
Check Pending Action
↓
Agent Decision
├── Direct Response
├── Call Tool
├── Ask for Missing Information
└── Resume Confirmation
↓
Tool Execution
↓
Check Tool Result
├── Success
├── Authentication Required
├── Confirmation Required
└── Error
↓
Generate Final Response
↓
Save Conversation
↓
END
```

---

## 4. الأدوات التي سيستخدمها الـAgent

### أدوات عامة لا تحتاج Login

```text
knowledge_rag
product_search
product_details
inventory_check
sales_recommendation
```

### أدوات خاصة تحتاج Login

```text
customer_lookup
customer_orders
order_status
order_details
human_handoff
```

### أدوات تحتاج Login وتأكيد

```text
order_creation
order_cancellation
```

---

## 5. ملفات المرحلة

```text
src/
├── agent/
│   ├── __init__.py
│   ├── AgentState.py
│   ├── AgentPrompts.py
│   ├── AgentNodes.py
│   ├── AgentGraph.py
│   └── AgentRouter.py
│
├── schemas/
│   └── AgentSchemas.py
│
├── services/
│   └── AgentService.py
│
└── routes/
    └── AgentRoutes.py

tests/
├── test_agent_state.py
├── test_agent_nodes.py
├── test_agent_graph.py
├── test_agent_service.py
├── test_agent_routes.py
├── test_agent_confirmation.py
└── test_agent_end_to_end.py
```

---

## 6. وظيفة كل ملف

### `src/agent/AgentState.py`

يحدد شكل الحالة المشتركة التي تنتقل بين Nodes داخل LangGraph.

الـState ستحتوي على بيانات مثل:

```text
session_id
user_message
customer_id
messages
selected_tool
tool_arguments
tool_results
pending_action
final_response
error
iteration_count
```

كل Node تقرأ البيانات التي تحتاجها وتعيد فقط التعديلات الجديدة على الـState.

---

### `src/agent/AgentPrompts.py`

يحتوي على تعليمات الـAgent الخاصة بفهم الرسالة واختيار الأدوات.

أمثلة التوجيه:

```text
سؤال معرفي → knowledge_rag
بحث عن منتج → product_search
تفاصيل منتج → product_details
فحص مخزون → inventory_check
اقتراح منتج → sales_recommendation
بيانات الحساب → customer_lookup
طلبات العميل → customer_orders
حالة طلب → order_status
تفاصيل طلب → order_details
إنشاء طلب → order_creation
إلغاء طلب → order_cancellation
طلب موظف أو صيدلي → human_handoff
تحية أو سؤال عام → Direct Response
```

التعليمات ستمنع الموديل من:

- اختراع نتائج أدوات.
- إرسال `user_id` داخل Arguments.
- تنفيذ عملية حساسة بدون تأكيد.
- اختراع سعر أو مخزون أو رقم طلب.

---

### `src/agent/AgentRouter.py`

مسؤول عن تحديد المسار التالي حسب حالة الـAgent.

أمثلة:

```text
selected_tool موجودة → Tool Execution
final_response موجودة → END
المعلومات ناقصة → Ask Clarifying Question
pending_action موجودة → Confirmation Flow
حدث خطأ → Error Handler
```

---

### `src/agent/AgentNodes.py`

يحتوي على الوظائف التي تمثل مراحل الـGraph.

الـNodes الأساسية:

```text
load_conversation_node
agent_decision_node
tool_execution_node
tool_result_node
request_confirmation_node
generate_response_node
save_conversation_node
error_handler_node
```

#### `load_conversation_node`

يجلب سجل المحادثة السابقة والحالة المعلقة إن وجدت.

#### `agent_decision_node`

يعرض تعريفات الأدوات للموديل ويطلب منه اختيار:

- Tool Call.
- رد مباشر.
- سؤال توضيحي.

#### `tool_execution_node`

يحوّل قرار الموديل إلى `ToolExecutionRequest` ثم يستخدم `ToolExecutionService`.

#### `tool_result_node`

يفحص النتيجة ويفرق بين:

```text
success
authentication_required
confirmation_required
invalid_tool_arguments
tool_not_found
tool_execution_error
```

#### `request_confirmation_node`

يجهز ملخص العملية ويوقف التنفيذ لحين موافقة المستخدم.

#### `generate_response_node`

يحوّل نتيجة الأداة إلى رد طبيعي وواضح.

#### `save_conversation_node`

يحفظ رسالة المستخدم ورد الـAgent وبيانات Tool Call الأساسية.

---

### `src/agent/AgentGraph.py`

يبني الـStateGraph ويربط الـNodes والـEdges.

شكل مبدئي:

```text
START
↓
Load Conversation
↓
Agent Decision
├── Direct Response → Save → END
├── Tool Execution → Tool Result
├── Ask Clarification → Save → END
└── Confirmation → Interrupt
```

بعد تنفيذ Tool:

```text
Tool Result
├── يحتاج Tool أخرى → Agent Decision
├── يحتاج Login → Generate Response
├── يحتاج Confirmation → Confirmation Node
├── نجح → Generate Response
└── فشل → Error Handler
```

---

### `src/schemas/AgentSchemas.py`

يحتوي على عقود API ونتائج الـAgent، مثل:

```text
AgentChatRequest
AgentChatResponse
AgentToolCall
PendingAction
AgentError
```

مثال Request:

```json
{
  "message": "عندكم ترمومتر؟",
  "session_id": "session-123"
}
```

مثال Response:

```json
{
  "session_id": "session-123",
  "response": "متوفر ترمومتر رقمي بسعر 450 جنيه.",
  "tool_calls": [
    {
      "tool_name": "product_search",
      "success": true
    }
  ],
  "requires_confirmation": false
}
```

---

### `src/services/AgentService.py`

واجهة بسيطة لاستخدام الـGraph من أي مكان.

```python
response = agent_service.chat(
    message="عندكم ترمومتر؟",
    session_id="session-123",
    customer_id=None,
)
```

مسؤولياته:

- تجهيز الـState الأولية.
- تحديد `thread_id`.
- تشغيل أو استكمال الـGraph.
- تحويل الحالة النهائية إلى `AgentChatResponse`.

---

### `src/routes/AgentRoutes.py`

يوفر API للمحادثة:

```text
POST /api/agent/chat
```

الـFlow:

```text
HTTP Request
↓
Optional Bearer Token
↓
استخراج customer_id إن وجدت Token
↓
AgentService.chat()
↓
LangGraph
↓
JSON Response
```

الـAgent لا يستقبل `customer_id` من المستخدم. الهوية تأتي من JWT فقط.

---

## 7. Tool Loop

بعض الطلبات تحتاج أكثر من أداة.

مثال:

```text
عاوز ترمومتر أقل من 600 جنيه ومتوفر منه قطعتين
```

الـFlow المحتمل:

```text
sales_recommendation
↓
inventory_check
↓
Final Response
```

الـGraph ستسمح بالعودة من `tool_result_node` إلى `agent_decision_node`.

سنضع حدًا أقصى:

```text
MAX_TOOL_ITERATIONS = 5
```

لمنع Loop لا نهائية.

---

## 8. Authentication Flow

```text
Bearer JWT
↓
AuthenticationDependencies
↓
customer_id
↓
AgentState.customer_id
↓
ToolExecutionRequest.user_id
↓
ToolExecutionService
```

لو المستخدم غير مسجل وطلب بيانات خاصة:

```text
وريني طلباتي
```

النتيجة:

```text
customer_orders
→ authentication_required
→ رد يطلب تسجيل الدخول
```

---

## 9. Confirmation Flow

العمليات التي تحتاج تأكيد:

```text
order_creation
order_cancellation
```

مثال إنشاء طلب:

```text
المستخدم: اطلبلي اتنين من الترمومتر
↓
Resolve Product
↓
Inventory Check
↓
Prepare Order Summary
↓
Pause Graph
↓
الـAgent: الإجمالي 900 جنيه. هل تؤكد؟
```

بعد رد المستخدم:

```text
أيوه أكد
↓
Resume Graph
↓
order_creation مع confirmed=True
↓
إرجاع رقم الطلب
```

لو قال المستخدم "لا":

```text
إلغاء Pending Action
↓
عدم إنشاء الطلب
```

---

## 10. Conversation Memory وPersistence

نحتاج نوعين من الحفظ:

### LangGraph Checkpointer

لحفظ مكان تنفيذ الـGraph وحالة التأكيد والـTool Loop.

في التطوير:

```text
InMemorySaver
```

في النسخة النهائية:

```text
PostgresSaver
```

### جداول المشروع

```text
conversations
messages
tool_executions
```

تُستخدم لحفظ سجل دائم للـDashboard والـAudit.

الفرق:

```text
Checkpointer → حالة تنفيذ الـGraph
Database Tables → سجل المحادثات والعمليات
```

---

## 11. Response Strategy

### ردود Deterministic

للعمليات الحساسة:

```text
تم إنشاء الطلب
تم إلغاء الطلب
تسجيل الدخول مطلوب
المخزون غير كافٍ
التأكيد مطلوب
```

تعتمد على Templates ونتائج الأدوات الفعلية.

### ردود LLM

للأجزاء المرنة:

```text
شرح Knowledge RAG
توصيات المنتجات
تلخيص نتائج البحث
الردود العامة
```

---

## 12. تقسيم التنفيذ

### الجزء الأول: Agent Core

```text
AgentSchemas
AgentState
AgentPrompts
AgentNodes
AgentGraph
AgentService
```

اختبار التوجيه الأساسي:

```text
عندكم ترمومتر؟ → product_search
الديسلفرام بيعمل إيه؟ → knowledge_rag
وريني بيانات حسابي → customer_lookup
أهلًا → direct_response
```

### الجزء الثاني: Tool Loop

```text
Tool Selection
Tool Execution
Multiple Tool Calls
Maximum Iterations
Final Response
```

### الجزء الثالث: Auth + Agent API

```text
JWT Integration
POST /api/agent/chat
Public and Protected Flows
```

### الجزء الرابع: Confirmation + Memory

```text
Interrupt and Resume
Pending Actions
Checkpointer
Conversation Persistence
```

### الجزء الخامس: Evaluation

```text
Unit Tests
Integration Tests
End-to-End Scenarios
Tool Selection Accuracy
Confirmation Safety
```

---

## 13. سيناريوهات الاختبار النهائية

### سيناريو بيع

```text
المستخدم: عاوز ترمومتر للبيت
الـAgent: يبحث ويعرض المنتج

المستخدم: متوفر منه اتنين؟
الـAgent: يفحص المخزون

المستخدم: اطلبهم
الـAgent: يعرض الملخص ويطلب التأكيد

المستخدم: أيوه
الـAgent: ينشئ الطلب ويرجع رقمه
```

### سيناريو خدمة عملاء

```text
المستخدم: طلبي وصل لفين؟
الـAgent: يطلب رقم الطلب إذا كان ناقصًا

المستخدم: PC-123
الـAgent: يستخدم order_status
```

### سيناريو دعم بشري

```text
المستخدم: عاوز أكلم موظف
الـAgent: يجمع ملخص المشكلة
الـAgent: ينفذ human_handoff
```

### سيناريو سؤال معرفي

```text
المستخدم: الديسلفرام بيعمل إيه مع الكحول؟
الـAgent: يستخدم knowledge_rag
الـAgent: يرجع إجابة مدعومة بالمصادر
```

---

## 14. معيار اكتمال مرحلة الـAgent

```text
LangGraph Workflow يعمل فعليًا
الـAgent يختار الأدوات الصحيحة
الأدوات تُنفذ من خلال ToolExecutionService
JWT تحدد هوية العميل
العمليات الحساسة تتوقف للتأكيد
الـGraph تستكمل بعد الرد
المحادثات تُحفظ
الـTool Loop لها حد أقصى
الأخطاء لها مسارات واضحة
POST /api/agent/chat يعمل
السيناريوهات End-to-End تنجح
```

---

## 15. موضعنا الحالي

```text
Database and ORM       مكتملة تقريبًا
RAG Core               مكتمل
Authentication         مكتملة
Tools Layer            مكتملة
LangGraph Agent        المرحلة الحالية
Dashboard              بعد الـAgent
Documentation          بعد الـDashboard
```
