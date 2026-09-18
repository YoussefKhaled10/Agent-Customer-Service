# مرحلة بناء الـTools

## 1. هدف المرحلة

تهدف مرحلة الـTools إلى تحويل وظائف المشروع إلى أدوات موحدة يستطيع الـAgent اكتشافها واختيارها وتنفيذها بأمان.

بدل استدعاء الخدمات وقاعدة البيانات مباشرة من الـAgent، أصبح المسار:

```text
Agent
↓
Tool Definition
↓
ToolExecutionRequest
↓
ToolExecutionService
↓
Tool
↓
Service / Model / Database
↓
ToolExecutionResult
```

---

## 2. الأدوات المكتملة

عدد الأدوات الحالي:

```text
12 Tools
```

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

## 3. البنية العامة للملفات

```text
src/
├── tools/
│   ├── __init__.py
│   ├── ToolInterface.py
│   ├── ToolRegistry.py
│   ├── knowledge/
│   ├── products/
│   ├── customers/
│   ├── orders/
│   ├── sales/
│   └── support/
│
├── schemas/
│   └── ToolSchemas.py
│
├── exceptions/
│   └── ToolExceptions.py
│
├── services/
│   ├── ToolExecutionService.py
│   └── ToolBootstrapService.py
│
├── routes/
│   └── ToolRoutes.py
│
└── core/
    └── AuthenticationDependencies.py
```

---

## 4. ملفات البنية الأساسية

### `src/schemas/ToolSchemas.py`

يحتوي على العقود المشتركة.

#### `ToolDefinition`

يعرّف الأداة للـAgent:

```text
name
description
input_schema
requires_authentication
requires_confirmation
is_idempotent
tags
```

#### `ToolExecutionRequest`

يمثل طلب التنفيذ:

```text
tool_name
arguments
request_id
user_id
confirmed
metadata
```

#### `ToolExecutionContext`

يحمل بيانات موثقة لا يرسلها الـAgent:

```text
user_id من JWT
request_id
confirmed
metadata
```

#### `ToolExecutionResult`

الشكل الموحد للنجاح أو الفشل:

```text
success
tool_name
data
message
error_code
execution_time_ms
request_id
metadata
```

---

### `src/exceptions/ToolExceptions.py`

يحتوي على أخطاء موحدة:

```text
ToolError
ToolRegistrationError
ToolNotFoundError
ToolValidationError
ToolAuthenticationRequiredError
ToolConfirmationRequiredError
ToolExecutionError
```

أمثلة `error_code`:

```text
tool_not_found
invalid_tool_arguments
authentication_required
confirmation_required
tool_execution_error
```

---

### `src/tools/ToolInterface.py`

العقد الإجباري لكل Tool:

```python
@property
def definition(self) -> ToolDefinition:
    ...

def execute(self, **arguments):
    ...
```

كل Tool يجب أن توفر:

- تعريفًا يفهمه الموديل.
- تنفيذًا فعليًا يرجع بيانات قابلة للتحويل إلى JSON.

---

### `src/tools/ToolRegistry.py`

السجل المركزي للأدوات.

مسؤول عن:

```text
register
unregister
get
definitions
model_schemas
names
```

ويمنع تسجيل أداتين بنفس الاسم.

---

### `src/services/ToolExecutionService.py`

بوابة التنفيذ والحماية.

```text
Resolve Tool
↓
Authentication Check
↓
Confirmation Check
↓
Arguments Validation
↓
Inject ToolExecutionContext
↓
Execute Tool
↓
Return Structured Result
```

يدعم Validation على:

```text
required
string
integer
number
boolean
object
array
minimum
minLength
maxLength
minItems
enum
nested objects
array items
additionalProperties
```

---

### `src/services/ToolBootstrapService.py`

ينشئ الـRegistry الافتراضية ويسجل كل الأدوات المتاحة.

```python
registry = ToolBootstrapService.create_registry()
```

ويجب تحديثه عند إضافة أي Tool جديدة.

---

### `src/routes/ToolRoutes.py`

يوفر:

```text
GET  /api/tools
POST /api/tools/execute
```

#### `GET /api/tools`

يعرض تعريفات الأدوات التي يمكن للموديل استخدامها.

#### `POST /api/tools/execute`

يستقبل اسم الأداة ومدخلاتها، ويستخرج هوية العميل من JWT إن وجدت، ثم ينفذ الأداة.

---

## 5. Knowledge Tool

### `src/tools/knowledge/KnowledgeRAGTool.py`

اسم الأداة:

```text
knowledge_rag
```

الوظيفة:

```text
Question
↓
RAGService
↓
Retrieval
↓
Reranking
↓
Context Builder
↓
Answer Generation
↓
Answer + Sources
```

لا تحتاج Login ولا Confirmation.

---

## 6. Product Tools

### `ProductSearchTool.py`

اسم الأداة:

```text
product_search
```

تبحث باستخدام:

```text
query
category_id
min_price
max_price
in_stock_only
limit
```

لا تحتاج Login.

---

### `ProductDetailsTool.py`

اسم الأداة:

```text
product_details
```

تجلب منتجًا واحدًا باستخدام:

```text
product_id
```

أو:

```text
sku
```

ويجب إرسال واحد فقط.

---

### `InventoryCheckTool.py`

اسم الأداة:

```text
inventory_check
```

تحسب:

```text
available_stock = stock - reserved_stock
can_fulfill = available_stock >= requested_quantity
```

لا تغيّر المخزون.

---

### `ProductToolHelpers.py`

يحوّل Product ORM Object إلى Dictionary، وينسق:

```text
price
currency
stock
features
warnings
metadata
```

---

## 7. Customer Tool

### `CustomerLookupTool.py`

اسم الأداة:

```text
customer_lookup
```

ترجع بيانات الحساب الحالي فقط.

```text
JWT
↓
customer_id
↓
CustomerModel.get_by_id()
```

لا تسمح للـAgent بإرسال `customer_id`.

تحتاج Login، ولا تحتاج Confirmation.

---

## 8. Order Read Tools

### `CustomerOrdersTool.py`

اسم الأداة:

```text
customer_orders
```

تعرض طلبات العميل الحالي، مع فلترة اختيارية بالحالة والعدد.

### `OrderStatusTool.py`

اسم الأداة:

```text
order_status
```

تجلب حالة طلب باستخدام:

```text
order_number + authenticated customer_id
```

### `OrderDetailsTool.py`

اسم الأداة:

```text
order_details
```

ترجع تفاصيل الطلب وعناصره والأسعار المحفوظة وقت الإنشاء.

### `OrderToolHelpers.py`

يحوّل Order وOrderItem إلى JSON ويجهز Summary أو Details كاملة.

كل أدوات القراءة تحتاج Login ولا تحتاج Confirmation.

---

## 9. Order Action Tools

### `OrderCreationTool.py`

اسم الأداة:

```text
order_creation
```

الـFlow:

```text
JWT Customer
↓
Confirmation
↓
Validate Products
↓
Check Inventory
↓
Read Authoritative Prices
↓
Create Order Transaction
↓
Reduce Stock
↓
Return Order Number
```

خصائص الحماية:

```text
Login Required
Confirmation Required
Idempotency Key
Database Prices Only
Stock Validation
Transaction Safety
```

---

### `OrderCancellationTool.py`

اسم الأداة:

```text
order_cancellation
```

الـFlow:

```text
JWT Customer
↓
Confirmation
↓
Ownership Check
↓
Order Status Check
↓
Cancel Order
↓
Restore Stock
```

مسموح في الحالات المبكرة فقط، وتكرار الإلغاء لا يعيد المخزون مرتين.

---

## 10. Sales Recommendation Tool

### `src/tools/sales/SalesRecommendationTool.py`

اسم الأداة:

```text
sales_recommendation
```

تعتمد على المنتجات الحقيقية الموجودة في قاعدة البيانات.

```text
User Need
↓
Product Search
↓
Active and In-stock Filtering
↓
Price Filtering
↓
Recommendations
```

لا تحتاج Login أو Confirmation، ولا تنشئ طلبًا تلقائيًا.

لا يجوز لها:

- اختراع منتج.
- اختراع سعر أو كمية.
- تقديم تشخيص.
- تقديم وصفة علاجية.
- ادعاء فوائد غير موجودة في بيانات المنتج.

---

## 11. Human Handoff Tool

### `src/tools/support/HumanHandoffTool.py`

اسم الأداة:

```text
human_handoff
```

الهدف هو إنشاء طلب مراجعة بشرية، وليس توصيل Live Chat فوري.

تعمل كـRouter:

```text
route=support
→ customer_inquiries

route=pharmacist
→ pharmacist_requests
```

### حالات الدعم العام

```text
شكوى
مشكلة طلب
مشكلة دفع
مشكلة تقنية
طلب موظف خدمة عملاء
```

### حالات الصيدلي

```text
طلب مراجعة صيدلي
سؤال منتج يحتاج مختصًا
طلب اتصال من صيدلي
```

تحتاج Login، ولا تحتاج Confirmation.

لا نستخدم جدول `support_tickets` جديد لأن الجداول الحالية تغطي الوظيفة.

---

## 12. ربط JWT بالـTools

```text
Authorization: Bearer <token>
↓
AuthenticationDependencies
↓
customer_id
↓
ToolExecutionRequest.user_id
↓
ToolExecutionContext.user_id
↓
Protected Tool
```

المستخدم والـAgent لا يستطيعان إرسال `user_id` يدويًا.

---

## 13. الفرق بين الأدوات حسب الحماية

### بدون Login

```text
knowledge_rag
product_search
product_details
inventory_check
sales_recommendation
```

### Login فقط

```text
customer_lookup
customer_orders
order_status
order_details
human_handoff
```

### Login + Confirmation

```text
order_creation
order_cancellation
```

---

## 14. الاختبارات المنفذة

```text
Tool Registration
Duplicate Name Rejection
Tool Resolution
Model Schemas
Input Validation
Authentication Protection
Confirmation Protection
Hidden Execution Context
Knowledge RAG Execution
Product Search and Details
Inventory Calculation
Customer Ownership
Order Ownership
Order Creation
Idempotency
Stock Reduction
Order Cancellation
Stock Restoration
Sales Recommendation
Human Handoff Routing
Tool API with JWT
Postman End-to-End Tests
```

---

## 15. الـFlow النهائي لطبقة الـTools

### Tool عامة

```text
HTTP / Agent
↓
ToolRoutes
↓
ToolExecutionService
↓
Public Tool
↓
Model / Service
↓
ToolExecutionResult
```

### Tool خاصة

```text
Bearer JWT
↓
AuthenticationDependencies
↓
customer_id
↓
ToolExecutionService
↓
Protected Tool
↓
Ownership Check
↓
ToolExecutionResult
```

### Tool كتابية

```text
Bearer JWT
↓
customer_id
↓
confirmed=true
↓
Authentication + Confirmation
↓
Order Action Tool
↓
Database Transaction
↓
Order and Inventory Update
↓
ToolExecutionResult
```

---

## 16. حالة مرحلة الـTools

```text
Tools Infrastructure        مكتملة
Knowledge Tool              مكتملة
Product Tools               مكتملة
Customer Tool               مكتملة
Order Read Tools            مكتملة
Order Action Tools          مكتملة
Sales Recommendation        مكتملة
Human Handoff               مكتملة
JWT Integration             مكتملة
Tool HTTP API               مكتملة
Automated Tests             مكتملة
Postman Tests               مكتملة
```

المرحلة التالية هي بناء **LangGraph Agent** الذي سيختار الأدوات تلقائيًا بدل تحديد `tool_name` يدويًا.
