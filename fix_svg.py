import re

path = r'd:\TrustMesh\TrustMesh\web-astro\src\components\SessionView.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix h1
content = content.replace(
    '<h2 class="text-sm font-semibold text-text-primary tracking-wide">Transcript</h2>',
    '<h1 class="text-sm font-semibold text-text-primary tracking-wide">Transcript</h1>'
)

# Fix scrollable region tabindex
content = content.replace(
    'class="flex-1 overflow-y-auto px-card py-card space-y-6"',
    'class="flex-1 overflow-y-auto px-card py-card space-y-6" tabIndex={0}'
)

# Fix SVG attributes
content = content.replace('class=', 'className=')
content = content.replace('stroke-width=', 'strokeWidth=')
content = content.replace('stroke-linecap=', 'strokeLinecap=')
content = content.replace('stroke-linejoin=', 'strokeLinejoin=')
content = content.replace('fill-rule=', 'fillRule=')
content = content.replace('clip-rule=', 'clipRule=')
content = content.replace('stroke-dasharray=', 'strokeDasharray=')
content = content.replace('stroke-dashoffset=', 'strokeDashoffset=')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
