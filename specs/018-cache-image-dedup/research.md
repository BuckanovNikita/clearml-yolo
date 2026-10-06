# Design decisions

- Exact filename is the identity: user selected it over manifest image_name. Content
  comparison protects collisions. Do not deduplicate equal content with different names.
- Unsupported reflinks are skips: user selected this over failure. Unexpected I/O errors fail.
- Linux FICLONE creates a copy-on-write sibling; atomic replacement avoids truncating
  original files. Hardlinks and ordinary copies do not satisfy the requested behavior.
- Keep CLI outside apps: inspecting apps/__init__.py established eager directory creation.
  Reuse cy_home for defaults without invoking initialize_filesystem.
- Metadata preservation includes mode, uid/gid, atime/mtime and xattrs; inode identity,
  ctime and birth time cannot survive replacement. Require an idle cache and detect observed
  changes, without claiming atomic coordination with external writers.
