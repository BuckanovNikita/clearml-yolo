# Research and decisions — 2026-10-20

The approved plan follows [OpenAI's maintenance article](https://developers.openai.com/blog/maintaining-software-with-the-gpt-6-family).
Current source and historical callers corroborate five bounded cleanup groups: retired direct GPU
helpers and process wait (31a5bd5edc2fe122791005526ae747e7fe5b0401), obsolete generation-era recovery
(dcbbc4903cec07c67ce50cd9b116ea3f6dab8216), publication naming and orphan test assertion
(589dc4a563e8a767a3cf9b675df66820b0a3c83b). Dynamic fields/hooks and public-looking queue
methods remain. GitHub has no recent test CI evidence supporting CI optimization here.

The initial tree has 522 task-history files, including 14 untracked files. Test consumers require
the scientific baseline and migration map. Installed Spec Kit numbers by existing spec directories,
not old Git branches; retain tooling and clear stale feature selection at cutoff. One baseline plus
immutable Git history was selected over an archive folder. Existing current guides remain useful.

Feature036 has outstanding real publication/cache checks; prior feature029/031 physical/NFS waivers
remain closed but unverified. Checkbox counts do not determine current acceptance. Approved existing
changes are included; unrelated private environment evidence is preserved.
