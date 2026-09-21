# Task 2 — Conversation Flows

All flows assume: agent = RealEstate Hub UrduLish sales exec; goal = qualify → recommend → book site visit (or help returning client manage appointment).

Shared entry: ring → greeting → intent detect → branch.

```mermaid
flowchart TD
  Start([Incoming call]) --> Greet[Greeting UrduLish]
  Greet --> Intent{Intent}
  Intent -->|buy| Buy[Buyer flow]
  Intent -->|rent| Rent[Rental flow]
  Intent -->|commercial| Comm[Commercial flow]
  Intent -->|invest| Inv[Investment flow]
  Intent -->|returning| Ret[Returning customer]
  Intent -->|reschedule| Resched[Reschedule]
  Intent -->|cancel| Cancel[Cancel]
  Intent -->|unclear| Clarify[Clarify purpose]
  Clarify --> Intent
```

---

## 1. Buyer inquiry

```mermaid
flowchart TD
  A[Greet + ask purpose] --> B[Confirm buy / city]
  B --> C[Budget range]
  C --> D[Preferred areas / society]
  D --> E[Bedrooms + possession timeline]
  E --> F[Structured search SQL]
  F --> G{Matches?}
  G -->|yes| H[Recommend 1-2 options + key facts from RAG]
  G -->|no| I[Widen budget/area or waitlist]
  H --> J{Interest?}
  J -->|yes| K[Objection handle if any]
  J -->|more options| F
  J -->|no| I
  K --> L[Offer site visit]
  L --> M[Collect name phone preferred slot]
  M --> N[Availability check]
  N --> O[Book calendar + email agent + CRM]
  O --> P[Confirm details + goodbye]
```

**Sample path:** budget → DHA/Bahria → 3 bed → shortlist → “price thoda zyada” → payment plan FAQ → visit Saturday 4pm.

---

## 2. Rental inquiry

```mermaid
flowchart TD
  A[Greet] --> B[Confirm rent]
  B --> C[Monthly rent budget]
  C --> D[Family / bachelor / shared]
  D --> E[Area + bedrooms + furnished?]
  E --> F[SQL rental inventory]
  F --> G[Recommend + deposit / advance rules from KB]
  G --> H{Visit?}
  H -->|yes| I[Book viewing]
  H -->|no| J[Send shortlist via SMS/WhatsApp later day]
  I --> K[Calendar + email + CRM]
```

---

## 3. Commercial property inquiry

```mermaid
flowchart TD
  A[Greet] --> B[Shop / office / warehouse]
  B --> C[City + corridor / plaza]
  C --> D[Size sq ft + budget / lease vs buy]
  D --> E[Footfall / parking / power needs]
  E --> F[SQL commercial filter]
  F --> G[Recommend + RAG brochure facts]
  G --> H[Site visit or broker meet]
  H --> I[Book + notify commercial desk]
```

---

## 4. Investment inquiry

```mermaid
flowchart TD
  A[Greet] --> B[Confirm invest]
  B --> C[Capital + horizon 1-5y]
  C --> D[Risk: plot / apartment / under-construction]
  D --> E[Preferred developer / city]
  E --> F[Filter + payment plan docs RAG]
  F --> G[Explain yield / appreciation carefully - no guarantees]
  G --> H{Objection?}
  H -->|builder trust| I[Share verified developer FAQ]
  H -->|liquidity| J[Exit / resale notes from KB]
  H -->|ok| K[Book consultant meeting]
  I --> K
  J --> K
  K --> L[Calendar + email investment advisor]
```

**Guardrail:** never promise ROI percentages not in the knowledge base.

---

## 5. Returning customer

```mermaid
flowchart TD
  A[Greet] --> B[Ask phone / name]
  B --> C[CRM lookup]
  C --> D{Found?}
  D -->|yes| E[Recall last prefs + open appointment]
  D -->|no| F[Treat as new + soft re-qualify]
  E --> G{Need?}
  G -->|new options| H[Resume recommend with memory]
  G -->|visit status| I[Read appointment]
  G -->|change visit| Resched
  G -->|cancel| Cancel
```

---

## 6. Appointment rescheduling

```mermaid
flowchart TD
  A[Verify identity phone] --> B[Load existing event]
  B --> C[Offer 2-3 new slots]
  C --> D[Client picks]
  D --> E[Check free/busy]
  E --> F{Free?}
  F -->|no| C
  F -->|yes| G[Update Calendar]
  G --> H[Email client + employee]
  H --> I[CRM log reschedule]
  I --> J[Confirm aloud + goodbye]
```

---

## 7. Appointment cancellation

```mermaid
flowchart TD
  A[Verify identity] --> B[Confirm which booking]
  B --> C[Ask brief reason optional]
  C --> D[Confirm cancel intent]
  D --> E[Delete/cancel Calendar event]
  E --> F[Email notification]
  F --> G[CRM status cancelled]
  G --> H[Offer rebook later]
  H --> I[Polite goodbye]
```

---

## Turn-taking rules (all flows)

| Situation | Agent behavior |
|-----------|----------------|
| User interrupts | Stop TTS; listen; acknowledge (“Ji boliye…”) |
| Silence &gt; 3s | Soft prompt (“Sir, aap sun rahe hain?”) |
| Anger | Empathy → clarify → human escalation offer |
| Unknown fact | “Confirm karke batata hoon” → RAG/SQL → never invent |
| Ready to book | Collect name, phone, slot; read back once |

## Success metrics per flow

- Buyer/rental/commercial/invest: **qualified lead** or **booked visit**  
- Returning: correct recall without re-asking everything  
- Reschedule/cancel: calendar + email + CRM all updated  
