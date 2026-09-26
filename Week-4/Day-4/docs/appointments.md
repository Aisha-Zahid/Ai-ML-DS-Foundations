# Appointment management (Task 3)

| Action | API | Side effects |
|--------|-----|--------------|
| Book | `appointments.book_appointment` / `book_from_phrase` | Calendar create + email + CRM row + follow-up |
| Reschedule | `reschedule_appointment` | Calendar update + email + CRM update |
| Cancel | `cancel_appointment` | Calendar cancel + email + CRM status=cancelled |

Slots: `src/slots.py` (`offer_slots`, `parse_slot`, `is_slot_free`).
