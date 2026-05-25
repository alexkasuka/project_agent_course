# Demo Lecture: LangGraph Basics

This is synthetic course material created for the public demo repository.

## Goal

LangGraph is useful when an agent needs an explicit workflow instead of a single linear prompt. A graph lets us split work into small nodes, pass a typed state between them, and make routing decisions based on intermediate results.

## Core Terms

- State: a typed dictionary or model that stores data shared across the graph.
- Node: a function that receives the current state and returns a partial state update.
- Edge: a transition from one node to another.
- Conditional edge: a transition chosen by a routing function.
- Tool: deterministic code that performs a concrete action, such as reading a file or searching course notes.
- Human-in-the-loop: a review step where a person approves, rejects, or edits the agent result.

## Student Assignment Assistant

For a learning project, a simple graph can use this workflow:

1. Load the assignment from text, PDF, or notebook.
2. Search course materials for relevant context.
3. Draft a solution with an LLM or local fallback.
4. Ask a human to review the draft.
5. Save the approved result as a Markdown artifact.

The graph state should include the assignment text, retrieved context, draft solution, review request, citations, risk flags, and model name.

## Why Human Review Matters

Generated answers can miss requirements, cite weak context, or overfit to irrelevant snippets. A human review step keeps the student responsible for the final submission and makes the system safer for learning.

