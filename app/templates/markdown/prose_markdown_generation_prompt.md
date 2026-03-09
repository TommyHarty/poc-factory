# Prose Markdown Generation Prompt

You are writing a chapter for a technical ebook about agentic systems.

## Context
- Topic Area: {phrase}
- POC Title: {poc_title}
- POC Goal: {poc_goal}
- Why It Matters: {why_it_matters}
- Scope Boundaries: {scope_boundaries}

## Instructions

Write a conceptual prose chapter about this approach/pattern. This chapter is about the **idea**, not the specific POC implementation. Do NOT reference the generated repo, its files, its directory structure, or its code. Do NOT describe implementation decisions made in the POC. Save all of that for the code implementation walkthrough file.

Write as though you are explaining the concept to a technical reader who hasn't seen any code yet.

## Required Sections

### 1. Title (H1)
The POC title

### 2. The Problem
What problem does this approach solve? Why does it exist? What breaks in real production systems when you don't have it? Be specific about the failure modes.

### 3. When to Use This Pattern
Specific scenarios where this approach is the right choice. Include explicit anti-patterns — when NOT to use it and why.

### 4. How It Works
Explain the core mechanism of this approach conceptually. What are the moving parts? How do they interact? Use prose, diagrams in words, or abstract examples — but not code from the POC.

### 5. Trade-offs and Limitations
What this approach doesn't handle well. What assumptions it makes. Where it breaks down at scale or in edge cases.

### 6. Integration into Larger Systems
How this pattern fits into a real production system. What you'd connect it to. What comes before and after it in a real pipeline. What other patterns it composes well with.

### 7. Summary
2-3 paragraph synthesis of the key takeaway for a practitioner building production agentic systems.

## Style Requirements
- Full prose, not bullet lists (except where lists genuinely help)
- Technical but readable
- No filler phrases like "In conclusion" or "As we can see"
- No references to the specific generated POC repo, its files, or its code
- Do NOT mention, reference, or link to any other POCs, approaches, or patterns by name or number. This chapter stands alone.
- Length: 800-1400 words

## Output
Output the complete markdown chapter. Start with the H1 title.
