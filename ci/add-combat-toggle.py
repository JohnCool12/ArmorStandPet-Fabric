from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")


def insert_once(path: Path, marker: str, addition: str, description: str) -> None:
    source = path.read_text(encoding="utf-8")
    if addition.strip() in source:
        return
    if marker not in source:
        raise SystemExit(f"Could not find {description} insertion point in {path}")
    source = source.replace(marker, marker + addition, 1)
    path.write_text(source, encoding="utf-8")


# Persist the setting in each pet's JSON data. Gson leaves this primitive false
# when reading an older save that does not contain the field, so all existing
# pets safely begin with combat disabled.
pet_data = root / "storage/PetData.java"
insert_once(
    pet_data,
    "\tpublic double speed = 0.3;\n",
    "\tpublic boolean combatEnabled;\n",
    "PetData combat field",
)

# Keep the runtime flag on Pet, default it to false, and include it in the
# existing serialize/deserialize path used for shutdown, autosaves, and type
# changes.
pet = root / "types/Pet.java"
insert_once(
    pet,
    "\tprotected String name;\n",
    "\tpublic boolean combatEnabled;\n",
    "Pet runtime combat field",
)
insert_once(
    pet,
    "\t\tthis.speed = 0.3;\n",
    "\t\tthis.combatEnabled = false;\n",
    "Pet combat default",
)
insert_once(
    pet,
    "\t\tdata.speed = this.speed;\n",
    "\t\tdata.combatEnabled = this.combatEnabled;\n",
    "Pet combat serialization",
)
insert_once(
    pet,
    "\t\tthis.speed = data.speed;\n",
    "\t\tthis.combatEnabled = data.combatEnabled;\n",
    "Pet combat deserialization",
)

# Register the command with the normal /aspet dispatcher. fix-command-args.py
# already ensures CombatCommand receives ["combat", "on"|"off"].
command_dispatcher = root / "normalcommands/ASPetCommand.java"
insert_once(
    command_dispatcher,
    "\t\tcommands.put(\"greetrange\", new GreetrangeCommand());\n",
    "\t\tcommands.put(\"combat\", new CombatCommand());\n",
    "/aspet combat registration",
)

checks = {
    pet_data: ["public boolean combatEnabled;"],
    pet: [
        "public boolean combatEnabled;",
        "this.combatEnabled = false;",
        "data.combatEnabled = this.combatEnabled;",
        "this.combatEnabled = data.combatEnabled;",
    ],
    command_dispatcher: ["commands.put(\"combat\", new CombatCommand());"],
}
for path, required in checks.items():
    source = path.read_text(encoding="utf-8")
    for text in required:
        if source.count(text) != 1:
            raise SystemExit(f"Expected exactly one {text!r} in {path}")

print("Added persistent, default-off /aspet combat on|off toggle")
