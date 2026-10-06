# 02. System Architecture & Data Model

> **Tags**: #data-model #schema #graph #architecture
> **Parent**: [[00_Map_of_Content]] | **Next**: [[03_Socratic_Question_Engine_and_Stop_Rules]]

---

## 🏛️ The 6-Level Semantic Hierarchy

The system models application architecture not as flat files or arbitrary canvas cards, but as a strongly-typed Directed Acyclic Graph (DAG) with bidirectional relational traversal.

```
Level 1: [User / Persona]
   │
   ▼ (owns / engages with)
Level 2: [User Flow] (Ordered step sequence)
   │
   ▼ (renders)
Level 3: [Screen] (States: Default, Loading, Empty, Error)
   │
   ▼ (contains)
Level 4: [CTA / Action] ── CONNECTIVE TISSUE ──
   │                     ├── On Success ──► Target Screen
   │                     └── On Failure ──► Fallback Screen / State
   ▼ (dispatches)
Level 5: [API Contract] (Shared node: 1 definition, N screen references)
   │
   ▼ (executes)
Level 6: [Backend Logic & Failure Path] (Vendors, idempotency, edge cases)
```

---

## 📋 Strongly-Typed Node Schemas (Pydantic / TypeScript)

### 1. Screen Node
```typescript
interface ScreenNode {
  id: string; // e.g. "W05_CHECKOUT"
  type: "SCREEN";
  title: string;
  flowId: string;
  owner: "FRONTEND" | "PM";
  states: {
    loading: string;
    empty: string;
    error: string;
    default: string;
  };
  acceptanceCriteria: string[];
  ctaIds: string[];
  status: "DRAFT" | "UNDER_REVIEW" | "READY" | "IMPLEMENTED" | "TESTED";
}
```

### 2. CTA Node (The Connective Tissue)
```typescript
interface CTANode {
  id: string; // e.g. "CTA_W05_CONTINUE"
  type: "CTA";
  parentScreenId: string;
  label: string;
  preconditions: string[]; // e.g. ["Form isValid == true", "PIN code length == 6"]
  apisCalled: string[]; // e.g. ["API32_DELIVERY_CHECK", "API42_QUOTE_REVALIDATE"]
  onSuccess: {
    targetScreenId: string; // e.g. "W06_PAYMENT"
    stateTransition: Record<string, any>;
  };
  onFailure: {
    targetScreenId: string; // e.g. "W05_CHECKOUT"
    preservedFields: string[]; // Form fields preserved across error
    errorDisplay: "INLINE" | "TOAST" | "MODAL";
  };
  retryPolicy: {
    allowRetry: boolean;
    maxRetries: number;
    debounceMs: number;
  };
}
```

### 3. API Node (Deduplicated Single Source of Truth)
```typescript
interface APINode {
  id: string; // e.g. "API32_DELIVERY_CHECK"
  type: "API";
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  service: string;
  vendor?: string; // e.g. "Shiprocket", "Stripe"
  inputs: Record<string, string>; // Typed payload schema
  outputs: Record<string, string>;
  errorCodes: Record<number | string, {
    description: string;
    actionableFix: string;
  }>;
  idempotency: boolean;
  timeoutMs: number;
  cacheTtlSeconds: number;
  callingScreenIds: string[]; // Reverse-lookup graph link
  logicStepIds: string[];
}
```

### 4. Question & Blocking Node
```typescript
interface QuestionNode {
  id: string;
  targetNodeId: string; // Attaches to Screen, CTA, API, etc.
  category: "FRONTEND" | "BACKEND" | "PM" | "COMPLIANCE";
  questionText: string;
  isBlocking: boolean; // If true, Branch Readiness Score drops to 0
  assignedTo: string;
  status: "OPEN" | "ANSWERED" | "DISMISSED";
  answerText?: string;
  answeredAt?: string;
}
```

---

## 🔄 Bidirectional Traversal Engine

- **Top-Down (PM & Designer View)**:
  `User` $\to$ `Flow` $\to$ `Screen` $\to$ `CTA` $\to$ `API` $\to$ `Backend Steps`
- **Bottom-Up (Backend & Impact Analysis View)**:
  `API32` modified $\implies$ Immediately flags all 3 Screens and 2 Flows dependent on it.
  Calculates **blast radius** of API contract updates.
