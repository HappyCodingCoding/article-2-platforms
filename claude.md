# Project Context

When working with this codebase, prioritize readability over cleverness. Ask clarifying questions before making architectural changes.

## About This Project

A series of skills to speed up the process from proofreading, providing title alternatives, creating brief captions … to publishing articles to multiple Chinese social platforms.

## Behavioral Guidelines

- Create skills under the skill structure specification `references/skill-structure-specification.md`.
- Use `qingyun-` as the prefix of skills' names when creating new skills.
- Create a `{skill-folder}/scripts/script.py` file as the main script file for the skill working on to invoke if scripts needed to complete tasks. Other script files, each of which might carry on a specific and small task, must be called within the main script and can’t be called directly by the skill working on itself.
- Write instructions or prompts in English, and write copies, titles or something else that is inappropriate to be written in English in languages the target audiences speak.
- Use Edit tool rather than Python string-splice via Bash to edit codes.
- Don't keep evidences or traces of changes in the prompts of skills being edited.
- Record alternative approaches/mechanisms/features that works but not the best option, and have been ruled out from skills to `{skill-name}/references/useful-alternatives.md`. Multiple alternatives that can be classified under a larger category should be placed under the larger category.
- When testing skills in the project, deploy them to the global skills folder you support(for example, `~/.claude/skills` for Claude) first(overide the deployed versions if any), and then test them on the deployed versions. Afer testing, back to the skills in the project to edit them if you are told to or have to eidt the skills accroding to the testing results or instructions. Remember: never edit the deployed versions.
- Prioritize scripts to do tasks if they are competent and efficient to do. Only when scripts couldn't do the jobs, use Reasoning, Browser Use, Computer Use or other tools.