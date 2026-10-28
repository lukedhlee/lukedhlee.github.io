#!/usr/bin/env python3
"""Recreate the draft-decoding figure with balanced title and plot spacing.
Acceptance data: public gist bd14e461b13557a3a541e721fcda643e,
snowball_ns_c_per_step.csv. Timing sums: spec-decode-report-figs-20260911.py.
"""
from pathlib import Path
import argparse,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
TITLE_FONT = FontProperties(family=["Helvetica Neue", "Arial", "DejaVu Sans"], weight="medium")
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[r for r in csv.DictReader(a.source.open()) if 1 <= int(r['step']) <= 60]
steps=[int(r['step']) for r in rows];tau=[float(r['tau']) for r in rows]
assert len(steps)==60 and min(steps)==1 and max(steps)==60
ink,muted,grid,blue,gray='#18212C','#64748B','#E8EDF3','#3677C4','#B7C1CD'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'text.color':ink,'axes.labelcolor':ink,'xtick.color':muted,'ytick.color':muted,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#CBD5E1','savefig.facecolor':'white'})
fig=plt.figure(figsize=(15.4,6.6),facecolor='white')
fig.text(.045,.91,'Train the draft once, then keep using it during RL',ha='left',va='top',fontsize=22,fontproperties=TITLE_FONT)
l=fig.add_axes([.095,.23,.275,.52]);r=fig.add_axes([.55,.23,.41,.52])
l.set_title('1.42× faster updates',loc='left',fontsize=15,fontproperties=TITLE_FONT,pad=12)
r.set_title('The frozen draft held through 60 updates',loc='left',fontsize=15,fontproperties=TITLE_FONT,pad=12)
times=[(1223+966+449)/60,(856+545+458)/60]
l.plot([0,1],times,color='#CFD7E1',lw=2)
l.scatter([0,1],times,s=110,c=[gray,blue],zorder=3)
for x,t in enumerate(times):l.annotate(f'{t:.0f} min',(x,t),xytext=(0,14),textcoords='offset points',ha='center',fontsize=14)
l.set(xticks=[0,1],xticklabels=['Without draft','With draft'],xlim=(-.4,1.4),ylim=(0,58),ylabel='Time for three RL updates (minutes)')
l.tick_params(length=0,pad=8)
r.plot(steps,tau,color=blue,lw=2.2)
r.set(xlim=(1,60),ylim=(2.2,2.8),xlabel='RL update',ylabel='Tokens accepted per verification step')
r.set_xticks([10,20,30,40,50,60]);r.grid(axis='y',color=grid,lw=.8);r.tick_params(length=0,pad=8)
r.xaxis.labelpad=10;r.yaxis.labelpad=10
fig.text(.06,.10,'Left: matched five-node timing runs. Right: a separate 60-update run, with no draft retraining.',fontsize=10,color=muted)
fig.text(.06,.06,'A small draft proposes tokens and the main model verifies them. Results are specific to the tested recipe.',fontsize=10,color=muted)
fig.savefig(a.output,dpi=180);fig.savefig(a.output.with_suffix('.svg'))
p=a.output.with_suffix('.svg');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print('Saved',a.output)
