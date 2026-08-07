from pathlib import Path

root = Path("project/src/main/java/io/github/kyzderp/armorstandpet")

# Expose the owning pet of scheduled pet tasks so the scheduler can cancel
# only that pet's current action chain when combat takes priority.
task_path = root / "tasks/ASPetTask.java"
task_source = task_path.read_text(encoding="utf-8")
getter = '''
	public Pet getPet()
	{
		return this.pet;
	}
'''
marker = '''	public ASPetTask(Pet pet, List<ASPetAction> callback)
	{
		this.pet = pet;
		this.callback = callback;
	}
'''
if getter.strip() not in task_source:
    if marker not in task_source:
        raise SystemExit("Could not find ASPetTask getter insertion point")
    task_source = task_source.replace(marker, marker + getter, 1)
if task_source.count("public Pet getPet()") != 1:
    raise SystemExit("ASPetTask must contain exactly one getPet() method")
task_path.write_text(task_source, encoding="utf-8")

# Add a targeted cancellation API. It removes queued movement/action tasks for
# one pet without touching autosaves, doorman cooldowns, or other pets.
scheduler_path = root / "scheduler/TickScheduler.java"
scheduler_source = scheduler_path.read_text(encoding="utf-8")
imports = '''import io.github.kyzderp.armorstandpet.tasks.ASPetTask;
import io.github.kyzderp.armorstandpet.types.Pet;
'''
import_marker = "package io.github.kyzderp.armorstandpet.scheduler;\n\n"
if "import io.github.kyzderp.armorstandpet.tasks.ASPetTask;" not in scheduler_source:
    if import_marker not in scheduler_source:
        raise SystemExit("Could not find TickScheduler import insertion point")
    scheduler_source = scheduler_source.replace(import_marker, import_marker + imports, 1)

method = '''
	/**
	 * Cancel every queued task in the current action chain for one pet.
	 * Combat uses this to override following, walking, delayed callbacks and
	 * temporary name changes immediately, without cancelling unrelated tasks.
	 */
	public static void cancelPetTasks(Pet pet)
	{
		if (pet == null)
			return;

		synchronized (pending)
		{
			pending.removeIf(entry -> belongsToPet(entry.runnable, pet));
		}
		entries.removeIf(entry -> belongsToPet(entry.runnable, pet));
	}

	private static boolean belongsToPet(ModRunnable runnable, Pet pet)
	{
		return runnable instanceof ASPetTask task && task.getPet() == pet;
	}
'''
method_marker = '''	/**
	 * Cancel every scheduled task, used on server shutdown so nothing keeps
	 * a reference to a stale world after a reload.
	 */
'''
if "public static void cancelPetTasks(Pet pet)" not in scheduler_source:
    if method_marker not in scheduler_source:
        raise SystemExit("Could not find TickScheduler cancellation insertion point")
    scheduler_source = scheduler_source.replace(method_marker, method + "\n" + method_marker, 1)

required = [
    "import io.github.kyzderp.armorstandpet.tasks.ASPetTask;",
    "import io.github.kyzderp.armorstandpet.types.Pet;",
    "public static void cancelPetTasks(Pet pet)",
    "pending.removeIf(entry -> belongsToPet(entry.runnable, pet));",
    "entries.removeIf(entry -> belongsToPet(entry.runnable, pet));",
    "task.getPet() == pet",
]
for text in required:
    if scheduler_source.count(text) != 1:
        raise SystemExit(f"Expected exactly one {text!r} in TickScheduler")
scheduler_path.write_text(scheduler_source, encoding="utf-8")

print("Added per-pet task cancellation so combat immediately overrides current actions")
