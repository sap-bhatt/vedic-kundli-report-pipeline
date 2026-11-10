# Brief: answer one model call (API emulation, for `--provider file`)

You are standing in for a single API call to a language model. You are given PROMPT (a `.txt` file in
`OUT/prompts/`) and RESPONSE (the matching `.md` path in `OUT/responses/`).

1. Read PROMPT in full (it can be long: read it in chunks until the end). It contains a `=== SYSTEM ===` part (your
   instructions) and one or more `=== USER ===` / `=== ASSISTANT ===` turns. Act as the assistant answering the LAST
   user turn, following the system part exactly.
2. Do not read, search or open any other file, and do not run any command or tool except reading PROMPT and writing
   RESPONSE. All the knowledge you may use is inside PROMPT.
3. Write your answer, and nothing else, to RESPONSE: exactly the text the system part asks for (for a section: the
   Markdown starting with "## ", then the hidden rows block if the input lists one, then the hidden trace block; for
   the editor: only the JSON array). No preamble, no code fence around it, no notes.
4. Reply with one line: "done" and the approximate word count.
