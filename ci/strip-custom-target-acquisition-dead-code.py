from pathlib import Path
import re

p=Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s=p.read_text()


def remove_method(signature, required=False):
    global s
    i=s.find(signature)
    if i<0:
        if required: raise SystemExit(f'method missing: {signature}')
        return False
    # Include immediately preceding @Override when the signature itself starts after it only if requested signature includes it.
    b=s.find('{',i); d=0; end=None
    for j in range(b,len(s)):
        if s[j]=='{': d+=1
        elif s[j]=='}':
            d-=1
            if d==0:
                end=j+1; break
    if end is None: raise SystemExit(f'unclosed method: {signature}')
    # Consume following blank lines for clean source.
    while end < len(s) and s[end] in '\r\n': end += 1
    s=s[:i]+s[end:]
    return True

# Delete the three acquisition-related overrides completely. GolemBase extends IronGolem,
# so Java now dispatches directly to Minecraft's own implementations.
remove_method('\t@Override\n\tprotected void registerGoals() {', required=True)
remove_method('\t@Override\n\tpublic boolean canAttackType(final EntityType<?> type) {', required=True)
remove_method('\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {', required=True)

# Delete all obsolete private target-recovery/acquisition machinery from earlier iterations.
for sig in (
    '\tprivate boolean hasVanillaVillageReputationReason(final Player player) {',
    '\tprivate boolean isInvalidPlayerCombatTarget(@Nullable final Player player) {',
    '\tprivate boolean isInvalidRememberedPlayerProvoker(@Nullable final Player player) {',
    '\tprivate void hardResetInvalidPlayerProvocationBeforeAiTick() {',
    '\tprivate void seedNearestNormalHostileTarget() {',
    '\tprivate void recoverInterruptedDirectPlayerProvocation() {',
    '\tprivate void sanitizeSilentAggravationState() {',
    '\tprivate void maintainConstructedNeutralRetaliation() {',
    '\tprivate void migrateLegacyPlayerCreatedConstructedGolem() {',
    '\tprivate void migrateBedrockNaturalHostilityState() {',
    '\tprivate void configureConstructedNeutralTargeting() {',
    '\tprivate void configureBedrockNaturalIronGolemTargeting() {',
):
    remove_method(sig, required=False)

# Remove private state that existed only for the deleted custom target model.
for pat in (
    r'\n\tprivate boolean assigningVillageDefensePlayerTarget;\n',
    r'\n\t@Nullable\n\tprivate Player interruptedDirectPlayerProvoker;\n',
):
    s=re.sub(pat,'\n',s,count=1)

# No direct call to any deleted acquisition helper may remain.
for token in (
    'hardResetInvalidPlayerProvocationBeforeAiTick(',
    'seedNearestNormalHostileTarget(',
    'recoverInterruptedDirectPlayerProvocation(',
    'sanitizeSilentAggravationState(',
    'hasVanillaVillageReputationReason(',
    'configureConstructedNeutralTargeting(',
    'configureBedrockNaturalIronGolemTargeting(',
    'migrateLegacyPlayerCreatedConstructedGolem(',
    'migrateBedrockNaturalHostilityState(',
    'maintainConstructedNeutralRetaliation(',
):
    if token in s:
        raise SystemExit(f'custom acquisition token remains: {token}')

# The inherited methods themselves must not be redeclared by GolemBase.
for token in (
    'protected void registerGoals()',
    'public void setTarget(@Nullable LivingEntity pTarget)',
    'public boolean canAttackType(final EntityType<?> type)',
):
    if token in s:
        raise SystemExit(f'acquisition override remains: {token}')

# Goal rebuild still clears targetSelector then invokes this.registerGoals(); because there is
# now no override, that virtual call resolves directly to IronGolem.registerGoals().
if 'this.targetSelector.removeAllGoals(goal -> true);\n\t\t\tthis.registerGoals();' not in s:
    raise SystemExit('safe target-selector rebuild missing')

p.write_text(s)
print('Stripped custom target acquisition code; GolemBase now directly inherits IronGolem targeting methods.')
