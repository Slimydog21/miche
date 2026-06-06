# Router mode honesty — MPLAT2-SPR-01

**Status:** Accepted  
**Date:** 2026-06-06

## Problem

v1 exposed `MICHE_ROUTER_LLM_API_KEY` and `router_mode=llm` while executing the same keyword rules as `production`. Egghead review flagged this as honesty debt.

## Decision

- Rename default production path to **`rules_v0`**.
- Remove **`MICHE_ROUTER_LLM_API_KEY`** entirely.
- Use **`inbox_fallback`** when rules classifier returns no fixture (blocked triage).
- Lock enum in `schemas/miche_router_decision.json`.

## What would reverse this

A dedicated MPLAT2-LLM spec ships a real model call with structured output validation and cassette fallback — only then may `router_mode=llm` reappear in schema.