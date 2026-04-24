---
name: UI redesign from prototype
description: LoreMaster frontend redesigned to match the UI-LoreMaster handoff prototype (Space Grotesk/Lora fonts, glassmorphism surfaces, animated starfield canvas, interactive collection stars)
type: project
---

The frontend UI was redesigned to match the `docs/desings/extracted/ui-loremaster/project/LoreMaster Prototype.html` handoff.

**Changes applied (2026-04-23):**
- Fonts switched from Cinzel/Crimson Text → Space Grotesk (body) + Lora (headings)
- Design tokens updated: glassmorphism surfaces (`rgba(12,12,22,0.85)`), `--lm-accent` alias for gold, `--lm-border-accent`
- `body::before` grid background + `body::after` violet nebula glow
- New animations: `lm-glyph-pulse` (brand ✦), `lm-btn-glow` (accent buttons pulse), `lm-modal-in`
- Navbar: sticky, backdrop-filter blur, animated gold bottom line
- Created `StarfieldCanvas.tsx` — animated canvas with background stars, collection stars, shooting stars; dispatches `lm:collections` custom event to register clickable collections
- `CollectionsPage` dispatches `lm:collections` event on every collection list change
- Collection type extended with optional `document_count?` and `entity_count?`
- Collection card footer shows doc/entity counts if present, otherwise shows date
- GenerateTab in CollectionDetailPage updated to side-by-side layout (form 380px fixed + result flex)

**Why:** User provided the handoff bundle from Claude Design to translate into the real React frontend.
**How to apply:** The visual design is fully implemented. If the backend starts returning `document_count`/`entity_count` in collection list responses, the card footer will automatically show them.
