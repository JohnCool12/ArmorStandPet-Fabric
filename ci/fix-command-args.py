from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")
paths = [
    root / "normalcommands/ASPetCommand.java",
    root / "admincommands/ASPetAdminCommand.java",
]

old_block = '''\t\t// Rebuild an args[] array where args[0] is the subcommand name,
\t\t// matching what the original's Bukkit onCommand(...) received.
\t\tString[] args = new String[rest.length + 1];
\t\targs[0] = "aspet";
\t\tSystem.arraycopy(rest, 0, args, 1, rest.length);
'''
old_admin_block = '''\t\tString[] args = new String[rest.length + 1];
\t\targs[0] = "aspetadmin";
\t\tSystem.arraycopy(rest, 0, args, 1, rest.length);
'''

for path in paths:
    source = path.read_text(encoding="utf-8")
    if path.name == "ASPetCommand.java":
        if old_block not in source:
            raise SystemExit("Could not find the normal-command argument rebuilding block")
        source = source.replace(
            old_block,
            '''\t\t// rest already has the exact argument layout used by the original
\t\t// subcommands: rest[0] is the subcommand and rest[1] is its first
\t\t// argument. Do not prepend the root literal ("aspet").
''',
            1,
        )
    else:
        if old_admin_block not in source:
            raise SystemExit("Could not find the admin-command argument rebuilding block")
        source = source.replace(
            old_admin_block,
            '''\t\t// rest already starts with the subcommand. Prepending "aspetadmin"
\t\t// shifts player names and all other arguments one position to the right.
''',
            1,
        )

    if "command.execute(sender, args);" not in source:
        raise SystemExit(f"Could not find command dispatch in {path}")
    source = source.replace("command.execute(sender, args);", "command.execute(sender, rest);", 1)

    if "new String[rest.length + 1]" in source or "command.execute(sender, args);" in source:
        raise SystemExit(f"Argument offset bug remains in {path}")
    if "command.execute(sender, rest);" not in source:
        raise SystemExit(f"Correct dispatch missing in {path}")

    path.write_text(source, encoding="utf-8")

print("Fixed /aspet and /aspetadmin argument offsets; subcommands now receive player names at args[1]")
