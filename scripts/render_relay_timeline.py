"""Render the Relay SFT explanation as an editable SVG and PNG."""
from html import escape
from pathlib import Path
import subprocess

out = Path(__file__).resolve().parents[1] / 'assets/img/snowball'
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="2409" height="957" viewBox="0 0 2409 957">',
         '<rect width="2409" height="957" fill="white"/>',
         '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="none" stroke="context-stroke" stroke-width="1.5"/></marker></defs>']
ink, muted, blue, cyan, orange = '#253346', '#65758b', '#2563eb', '#06a9df', '#f59e0b'

def text(x, y, label, size=28, color=ink, weight=400, anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(label)}</text>')

def line(x1, y1, x2, y2, color=muted, arrow=False, dash=False):
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="3"'+
                 (' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="8 6"' if dash else '')+'/>')

def block(x, y, label, fill, color='white', border=None):
    parts.append(f'<rect x="{x}" y="{y}" width="107" height="102" rx="17" fill="{fill}" stroke="{border or fill}" stroke-width="2"/>')
    text(x+53.5,y+61,label,30,color,700,'middle')

def bracket(x1,x2,y,label,color):
    parts.append(f'<path d="M{x1},{y-10} V{y} H{x2} V{y-10}" fill="none" stroke="#d8e1ec" stroke-width="3"/>')
    text((x1+x2)/2,y+40,label,25,color,anchor='middle')

text(82,135,'(a) Teacher-only SFT',36,weight=700)
text(82,207,'The teacher solves the task alone.')
text(82,248,'Every teacher turn is trained.')
for i in range(12): block(735+i*125,106,'T',orange)
bracket(741,2210,237,'Teacher-generated history · every turn trained','#b96800')
line(2285,157,2344,157,arrow=True)
text(2315,210,'turns',24,muted,anchor='middle')

text(82,682,'(b) Relay SFT',36,weight=700)
text(82,750,'The student starts the task.')
text(82,791,'The teacher repairs an action or')
text(82,832,'checks and continues the work.')
for i in range(12):
    label='R' if i==3 else ('S' if i<7 else 'T')
    fill=cyan if i==3 else ('#f1f5f9' if i<7 else blue)
    block(735+i*125,632,label,fill,muted if label=='S' else 'white','#bac8d8' if label=='S' else None)
text(1163,440,'Invalid action',26,anchor='middle')
text(1163,474,'One-turn teacher repair (R), trained;',26,anchor='middle')
text(1163,508,'then the student resumes.',26,anchor='middle')
line(1163,537,1163,614,ink,True)
text(1610,440,'Teacher checks or continues',26,weight=500)
text(1610,474,'Context budget reached, or',26)
text(1610,508,'student declares completion.',26)
line(1598,537,1598,614,blue,True)
line(1598,619,1598,744,blue,dash=True)
text(1580,589,'handover',26,blue,anchor='end')
bracket(741,1585,764,'Student turns · context only, no loss',muted)
bracket(1610,2210,764,'Teacher continuation · trained',blue)
line(2285,683,2344,683,arrow=True)
text(2315,737,'turns',24,muted,anchor='middle')
parts.append('</svg>')
svg=out/'relay-timeline.svg'
svg.write_text('\n'.join(parts)+'\n')
subprocess.run(['rsvg-convert','-o',str(out/'relay-timeline.png'),str(svg)],check=True)
