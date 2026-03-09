# Run Intro Chapter Generation Prompt

You are writing the opening chapter of a technical ebook about agentic systems.

## Context
- Topic: {phrase}
- Normalized topic: {normalized_phrase}

## POCs covered in this series
{poc_list}

## Instructions

Write a prose introduction chapter for the topic above. This chapter opens the series and gives the reader the conceptual grounding they need before diving into the individual POC implementations.

## Required Sections

### Title (H1)
The normalized topic title (e.g. "Prompt Injection Guardrails")

### Introduction
2-3 paragraphs introducing the topic. Why does it matter in the context of agentic systems? What goes wrong when it is not addressed? Set the scene for a technical practitioner.

### The Core Challenge
One section explaining the fundamental problem space. Be specific about the failure modes, edge cases, and system-level consequences that make this topic non-trivial.

### How This Series Approaches It
Explain the overall philosophy behind the POC series — what kinds of approaches will be explored, why a range of implementations is valuable, and how they build understanding progressively. Do NOT enumerate or name the individual POCs. Stay at the conceptual level.

### What You Will Build
A brief section describing what the reader will have at the end of the series: working code, tested implementations, documented patterns, and a grounded understanding of the tradeoffs involved.

### How to Use This Series
2-3 sentences on how to read the series — whether to read linearly or dip into specific POCs, how the code and the chapters relate, and how to run the implementations.

## Style Requirements
- Full prose, not bullet lists (except where lists genuinely help)
- Technical but readable — written for a senior engineer or technical lead
- No filler phrases
- Do NOT name or reference the individual POCs by title, slug, or number
- Length: 600-1000 words

## Output
Output the complete markdown chapter. Start with the H1 title.
