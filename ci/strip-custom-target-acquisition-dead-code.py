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
    b=s.find('{',i); d=0; end=None
    for j in range(b,len(s)):
        if s[j]=='{': d+=1
        elif s[j]=='}':
            d-=1
            if d==0:
                end=j+1; break
    if end is None: raise SystemExit(f'unclosed method: {signature}')
    while end < len(s) and s[end] in '\r\n': end += 1
    s=s[:i]+s[end:]
    return True

# Delete acquisition-related overrides: Java dispatch now goes directly to IronGolem.
remove_method('\t@Override\n\tprotected void registerGoals() {', required=True)
remove_method('\t@Override\n\tpublic boolean canAttackType(final EntityType<?> type) {', required=True)
remove_method('\t@Override\n\tpublic void setTarget(@Nullable LivingEntity pTarget) {', required=True)

# Delete all obsolete target recovery/selector machinery from earlier iterations.
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
    '\tprivate void configureConstructedVillageTargeting() {',
    '\tprivate void updateConstructedNeutralTargetingMode() {',
):
    remove_method(sig, required=False)

# Remove any call sites to deleted target helpers that existed in compatibility paths.
for name in (
    'hardResetInvalidPlayerProvocationBeforeAiTick',
    'seedNearestNormalHostileTarget',
    'recoverInterruptedDirectPlayerProvocation',
    'sanitizeSilentAggravationState',
    'configureConstructedNeutralTargeting',
    'configureBedrockNaturalIronGolemTargeting',
    'configureConstructedVillageTargeting',
    'updateConstructedNeutralTargetingMode',
    'migrateLegacyPlayerCreatedConstructedGolem',
    'migrateBedrockNaturalHostilityState',
    'maintainConstructedNeutralRetaliation',
):
    s=re.sub(r'^\s*this\.'+re.escape(name)+r'\(\);\s*\n','',s,flags=re.M)
    s=re.sub(r'^\s*'+re.escape(name)+r'\(\);\s*\n','',s,flags=re.M)

# Remove private state used only by the deleted target model.
for pat in (
    r'\n\tprivate boolean assigningVillageDefensePlayerTarget;\n',
    r'\n\t@Nullable\n\tprivate Player interruptedDirectPlayerProvoker;\n',
):
    s=re.sub(pat,'\n',s,count=1)

# No custom target helper or provenance symbol may survive anywhere in GolemBase.
for token in (
    'hardResetInvalidPlayerProvocationBeforeAiTick',
    'seedNearestNormalHostileTarget',
    'recoverInterruptedDirectPlayerProvocation',
    'sanitizeSilentAggravationState',
    'hasVanillaVillageReputationReason',
    'configureConstructedNeutralTargeting',
    'configureBedrockNaturalIronGolemTargeting',
    'configureConstructedVillageTargeting',
    'updateConstructedNeutralTargetingMode',
    'migrateLegacyPlayerCreatedConstructedGolem',
    'migrateBedrockNaturalHostilityState',
    'maintainConstructedNeutralRetaliation',
    'assigningVillageDefensePlayerTarget',
    'interruptedDirectPlayerProvoker',
):
    if token in s: raise SystemExit(f'custom acquisition token remains: {token}')

for token in (
    'protected void registerGoals()',
    'public void setTarget(@Nullable LivingEntity pTarget)',
    'public boolean canAttackType(final EntityType<?> type)',
):
    if token in s: raise SystemExit(f'acquisition override remains: {token}')

# Safe material reinitialization: stop old selectors and then call inherited IronGolem.registerGoals().
if 'this.targetSelector.removeAllGoals(goal -> true);\n\t\t\tthis.registerGoals();' not in s:
    raise SystemExit('safe target-selector rebuild missing')

p.write_text(s)
print('Stripped all custom target acquisition code; GolemBase directly inherits IronGolem targeting.')
