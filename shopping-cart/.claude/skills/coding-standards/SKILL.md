---
name: coding-standards
description: "Apply project coding standards when writing or reviewing code"
user-invocable: true
argument-hint: "<file-or-directory>"
---

# Coding Standards

## General (all components)
- All functions must have docstrings explaining purpose and parameters
- Use descriptive variable names — no single-letter variables except loop counters
- Handle errors explicitly — never silently swallow exceptions
- Keep functions under 50 lines — extract helpers for complex logic

## Frontend (React)
- Components use PascalCase for filenames and function names
- State management through context — no prop drilling beyond 2 levels
- All user-facing text must be in a single constants file
- Use CSS classes from styles.css — no inline styles

## Backend (Python/Flask)
- Follow REST conventions: GET for reads, POST for creates, PUT for updates, DELETE for removes
- Return consistent JSON structure: { "data": ... } for success, { "error": "..." } for failure
- Validate all input before processing
- Never access DynamoDB directly — always go through the models layer

## API Standards (from project documentation)

!`cat docs/api-standards.md 2>/dev/null || echo "No api-standards.md found — use general REST conventions above"`

---

Apply these standards when reviewing or writing code in: $ARGUMENTS

After applying standards, provide a summary:
- List each file that was modified
- For each file, note which standards were applied
- Flag any areas that could not be fixed automatically
