# Context memory (Day 3 Task 3)

`CallMemory` stores: name, phone, purpose, city, area, budget, bedrooms, amenities, investment goal, last shortlist, objections.

## Reference resolution

| User says | Memory use |
|-----------|------------|
| "Budget 3 crore hai" | Sets `budget_text` / `budget_pkr` |
| "DHA mein kya options hain?" | Uses city + budget + sets area DHA |
| "Us se sasti koi option?" | Tightens budget vs last shortlist price |

Demo: `python scripts/demo_conversation.py` → `results/memory_demo.json`.
