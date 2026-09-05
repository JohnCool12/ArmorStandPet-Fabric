from pathlib import Path

root = Path('project')
data_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/data/ShootBehaviorData.java'
data = data_path.read_text()

old = '''\tpublic void trackTarget(final @Nullable LivingEntity target, final long gameTime) {\n\t\tif (target != this.trackedTarget) {\n\t\t\tthis.trackedTarget = target;\n\t\t\tthis.targetAcquiredGameTime = target == null ? Long.MIN_VALUE : gameTime;\n\t\t\t// A new target must independently fail to receive a melee hit for ten seconds.\n\t\t\tthis.lastSuccessfulMeleeHitGameTime = Long.MIN_VALUE;\n\t\t\tthis.lastRangedShotGameTime = Long.MIN_VALUE;\n\t\t}\n\t}\n'''

new = '''\tpublic void trackTarget(final @Nullable LivingEntity target, final long gameTime) {\n\t\tif (target != this.trackedTarget) {\n\t\t\tthis.trackedTarget = target;\n\t\t\tthis.targetAcquiredGameTime = target == null ? Long.MIN_VALUE : gameTime;\n\t\t\tthis.lastSuccessfulMeleeHitGameTime = Long.MIN_VALUE;\n\t\t\t// IMPORTANT: the ranged shot cooldown is per golem, not per target. Hurt/retaliation\n\t\t\t// logic can reassign or briefly transition targets. Resetting the timestamp here\n\t\t\t// made taking damage bypass the normal attack interval and produce an instant\n\t\t\t// extra projectile. Preserve lastRangedShotGameTime across all target changes.\n\t\t}\n\t}\n'''

if old not in data:
    raise SystemExit('Could not locate ShootBehaviorData target-tracking cooldown reset block')
data = data.replace(old, new, 1)
data_path.write_text(data)

# Static invariants: firing records one global timestamp, every ranged attempt checks it,
# and target changes must never reset it.
final_data = data_path.read_text()
if 'this.lastRangedShotGameTime = gameTime;' not in final_data:
    raise SystemExit('Missing ranged shot timestamp recording')
if 'gameTime - this.lastRangedShotGameTime >= ticks' not in final_data:
    raise SystemExit('Missing ranged cooldown elapsed check')

track_start = final_data.index('public void trackTarget(')
track_end = final_data.index('\n\t}', track_start) + len('\n\t}')
track_block = final_data[track_start:track_end]
if 'lastRangedShotGameTime = Long.MIN_VALUE' in track_block:
    raise SystemExit('Target tracking still resets the ranged shot cooldown')

shoot_path = root / 'src/main/java/com/mcmoddev/golems/data/behavior/ShootArrowsBehavior.java'
shoot = shoot_path.read_text()
for required in (
    'data.hasRangedShotCooldownElapsed(gameTime, getAttackInterval())',
    'data.markRangedShot(gameTime);',
):
    if required not in shoot:
        raise SystemExit(f'Missing global firing-cooldown invariant: {required}')

print('Applied pass 19: Dispenser Golem ranged cooldown now survives hurt/retarget transitions; damage cannot trigger an instant extra shot.')

# Finally layer optional Mob Battle compatibility: explicit Mob Enrager / Mob Group
# forced player targets must be accepted without weakening normal player safeguards.
pass20 = Path('ci/port-neoforge-26-1-2-pass20-mobbattle-forced-player-targets.py')
exec(compile(pass20.read_text(), str(pass20), 'exec'))
