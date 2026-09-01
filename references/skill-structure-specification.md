---
name: skill-name
description: What it does, when to use it, what it doesn't.
             Name user-selectable modes here.
---

# Skill Name

One or two sentences to describe what the skill does.

## Usage

Usage is built on options.
The skill is callable by explicit options, and by natural language too,
by inferring options and their values from the input regardless of
typos, vague meanings, etc.
When a value was inferred rather than stated, name the resolved options
before running.
If no option value can be inferred from the input, or two match equally
well, ask instead of guessing.

### Options

The options defined here target to the skill itself 
rather than to the script invoked in the skill 
although some options'names are the same as some of the script's.

Table: Option | Type | Values | Default | Description.

Explanations:
- Type = option | flag; mark a required one as `option (required)`.
- Values = the allowed values; `—` for a flag.
- Description = a brief explanation of what the option is used for
and what situation each of its values is for.


## Workflow

Steps and substeps numbered by the default path.
Workflow is determined by the options defined in the `Usage` section:
option values form conditions that skip, gate or add steps,
for example `if --attachments is no, skip Step 3 and continue to Step 4`.
Mark every branch with the literal option string so all of its sites
can be grepped.
Keep step numbers as they are regardless of how steps are arranged,
so that they can be referenced from anywhere in the skill.
Update the workflow when options are modified, added or removed,
and update the options table when a branch changes.

If this skill has to run scripts to complete tasks,
`scripts/script.py`, which may call other scripts, is the only script 
the workflow is allowed to invoke directly.
When a step runs the script, write the exact command at that step.
If the signature is unclear, read the script's argument parsing to
confirm it — never run the script to find out.

## Output

Content template, file tree, or both.

## [Other sections — replace this heading with the real ones] (optional)

Add only when the skill earns them:
Gotchas, Examples, Verification, Dependencies, Error Handling, etc..
Reference documents are cited inline at the step that needs them,
not collected into a section.