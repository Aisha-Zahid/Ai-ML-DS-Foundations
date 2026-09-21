# Task 4 — Fish Audio Evaluation (vs ElevenLabs)

**Goal:** pick the primary TTS for a Pakistani real-estate voice agent that must do fluent **UrduLish**, low latency, and production cost control.

Sources checked (product docs / public pages, 2026): [Fish Audio TTS](https://fish.audio/text-to-speech-api/), [Fish pricing](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits), [Fish S2.1 Pro](https://fish.audio/blog/s2-1-pro-free-api/). ElevenLabs compared from known product positioning (Flash/Turbo streaming, Multilingual v2, Instant Voice Cloning, usage-based tiers).

## Scorecard

| Criterion | Fish Audio | ElevenLabs | Edge for this project |
|-----------|------------|------------|------------------------|
| **Latency** | Claims ~70–100 ms time-to-first-audio on S2.1 Pro; WebSocket streaming | Strong Flash/Turbo streaming; often competitive on English | **Fish** slightly favored for marketed real-time agent use |
| **Naturalness** | Expressive, emotion tags, conversational prosody | Excellent English naturalness; very polished | Tie / content-dependent |
| **Emotion** | Open-domain emotion tags in API | SSML-ish / style controls, good drama voices | **Fish** for casual sales warmth |
| **Streaming** | First-class streaming + timestamps | Mature streaming SDKs | Tie |
| **Voice cloning** | Instant clone from short reference; works across 80+ langs | Instant + professional clones; industry standard | Tie (both usable for brand voice) |
| **Pricing** | Pay-as-you-go ~$15 / M UTF-8 bytes; free `s2.1-pro-free` for dev (fair use, no SLA) | Character-based plans / credits; can get pricey at call volume | **Fish** for predictable byte pricing + free prototype tier |
| **Multilingual** | 80–83 languages, one model | Strong multilingual models | Tie |
| **Urdu pronunciation** | Listed in broad multilingual set; must A/B with local names (DHA, Bahria, G-11) | Multilingual support; Urdu quality varies by model | **Validate both** — lean Fish if code-switch is smoother |
| **Urdu–English switching** | Marketed “instant code-switching” in one generation | Handles mixed text but often uneven stress on switches | **Fish** (assignment + docs emphasize this) |

## UrduLish-specific notes

Phone sales lines look like:

> “Ji bilkul, DHA Phase 6 mein teen bed ka option hai around 2.85 crore — weekend pe visit karna chahenge?”

Requirements:

1. English tokens (DHA, Phase, crore, visit) must not sound broken.  
2. Urdu particles (ji, bilkul, mein) need soft, local rhythm.  
3. Numbers and society names must stay clear for the client.  

Fish’s positioning (code-switch + emotion + low TTFA) matches this better than a pure “studio English” voice. Final Week-4 Day 3 work should still **listen-test** 10 sample lines on both engines before locking production voice ID.

## Latency budget (agent design)

| Segment | Target |
|---------|--------|
| STT finalization | &lt; 300–500 ms after end-of-speech |
| LLM first token (no tool) | &lt; 400 ms |
| Tool path (SQL/RAG) | &lt; 800 ms warm |
| TTS time-to-first-audio | &lt; 200–400 ms |
| **User-perceived reply start** | **&lt; 2 s** overall |

Fish streaming helps the last hop; tools + caching matter more than TTS alone.

## Risks / caveats

- Free Fish tier: no SLA — fine for class/demo, not live client traffic.  
- Concurrent request limits scale with spend — plan for call concurrency.  
- Always run a Pakistani speaker listening panel (Day 3 human eval).  
- Keep ElevenLabs as **optional A/B** if a specific English-heavy investor persona needs it.

## Conclusion

**Primary TTS: Fish Audio (S2.1 Pro / S2 Pro).**  
**Optional comparison path: ElevenLabs** for English-forward investor calls or backup vendor.

Rationale for RealEstate Hub:

1. Strong fit for UrduLish code-switching and expressive sales tone.  
2. Streaming + low time-to-first-audio for phone agents.  
3. Instant cloning for a consistent “Ali / brand” voice.  
4. Transparent usage pricing and a free prototype model for Week 4 build-out.  

Stack decision for later days: **Deepgram (STT) → LangGraph LLM → Fish Audio (TTS)**.
