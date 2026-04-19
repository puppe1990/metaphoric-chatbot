# Ebook Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python-only fallback so `.mobi` and `.azw3` books also become Markdown in the existing batch conversion flow.

**Architecture:** Keep `markitdown` as the primary converter. For unsupported ebook formats, extract an intermediate `.epub`, `.html`, or `.pdf` with Python libraries, then feed that intermediate back through the existing Markdown conversion path and record the fallback method in the report.

**Tech Stack:** Python 3.13, markitdown, mobi, pathlib, unittest/pytest-compatible tests

---
