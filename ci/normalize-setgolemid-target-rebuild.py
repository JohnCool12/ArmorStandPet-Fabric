from pathlib import Path

p=Path('project/src/main/java/com/mcmoddev/golems/entity/GolemBase.java')
s=p.read_text()
sig='\tpublic void setGolemId('
start=s.find(sig)
if start<0: raise SystemExit('setGolemId missing')
brace=s.find('{',start); depth=0; end=None
for i in range(brace,len(s)):
    if s[i]=='{': depth+=1
    elif s[i]=='}':
        depth-=1
        if depth==0:
            end=i+1; break
if end is None: raise SystemExit('setGolemId unclosed')
body=s[start:end]
reg=body.find('\t\t\tthis.registerGoals();')
if reg<0: raise SystemExit('registerGoals call missing in setGolemId')
# Find the nearest preceding goalSelector mutation line; cumulative patches may have
# changed clear() to removeAllGoals() and comments may differ.
pre=body.rfind('\t\t\tthis.goalSelector.',0,reg)
if pre<0: raise SystemExit('goalSelector rebuild line missing before registerGoals')
line_end=body.find('\n',reg)
if line_end<0: line_end=len(body)
normalized='''\t\t\t// remove and re-instantiate goals\n\t\t\tthis.goalSelector.getAvailableGoals().clear();\n\t\t\tthis.registerGoals();'''
body=body[:pre]+normalized+body[line_end:]
s=s[:start]+body+s[end:]
p.write_text(s)
print('Normalized setGolemId goal rebuild block for parity replacement.')
