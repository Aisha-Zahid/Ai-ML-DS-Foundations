```mermaid
flowchart TD
    A([START]) --> P[plan]
    P --> R[retrieve]
    R --> G[generate]
    G --> C[critique]

    C -->|quality < threshold AND retries < max| G
    C -->|acceptable quality OR retries exhausted| H[human_review (interrupt_before)]

    H -->|human_approved = true| F[format]
    H -->|human_approved = false| G[generate]  %% revise (retries++)

    F --> E([END])
```

