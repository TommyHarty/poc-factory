# Run Intro Chapter Generation Prompt

You are writing the opening chapter of a technical ebook about agentic systems.

## Context
- Topic: {phrase}
- Normalized topic: {normalized_phrase}

## POCs in this series
{poc_details}

## Instructions

Write a complete introduction chapter for the topic above. The chapter opens the series, gives the reader conceptual grounding, and then provides a concrete overview of every POC that was built.

## Required Sections

### Title (H1)
The normalized topic title (e.g. "Prompt Injection Guardrails")

### Introduction
2-3 paragraphs introducing the topic. Why does it matter in the context of agentic systems? What goes wrong when it is not addressed? Set the scene for a technical practitioner.

### The Core Challenge
One section explaining the fundamental problem space. Be specific about the failure modes, edge cases, and system-level consequences that make this topic non-trivial.

### How This Series Approaches It
Explain the overall philosophy behind the POC series — what kinds of approaches will be explored, why a range of implementations is valuable, and how they build understanding progressively.

### What You Will Build
A brief section describing what the reader will have at the end of the series: working code, tested implementations, documented patterns, and a grounded understanding of the tradeoffs involved.

### POC Overview
A subsection for **each POC** in the series. Use `####` for each POC heading in the format `#### NN. <Title>`.

For each POC write 2-3 paragraphs covering:
- The specific approach this POC demonstrates and why it was chosen
- What problem it solves and the design decisions involved
- Key packages or techniques used and any important tradeoffs
- How it relates to the broader topic and to adjacent POCs in the series

Base the overview directly on the POC data provided above (goal, why it matters, scope boundaries, packages). Do not invent details.

### How to Use This Series
2-3 sentences on how to read the series — whether to read linearly or dip into specific POCs, how the code and the chapters relate, and how to run the implementations.

## Style Requirements
- Full prose, not bullet lists (except where lists genuinely help)
- Technical but readable — written for a senior engineer or technical lead
- No filler phrases or generic AI padding
- The POC Overview section must reference each POC specifically and concretely
- Length: 1200-2000 words total

## Output
Output the complete markdown chapter. Start with the H1 title.
