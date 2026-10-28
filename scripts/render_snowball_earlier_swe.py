#!/usr/bin/env python3
"""Historical Stage-3 SWE-only comparison. Counts: marin issue #9225.
https://github.com/marin-community/marin/issues/9225
"""
from pathlib import Path
from math import sqrt
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
TITLE_FONT = FontProperties(family=["Helvetica Neue", "Arial", "DejaVu Sans"], weight="medium")
from matplotlib.ticker import PercentFormatter
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
labels=['Starting model','SFT on OpenThoughts mix','RL only','SFT + RL']
counts=[(43,297),(72,299),(25,100),(92,300)]
colors=['#a0a9b5','#35a9e6','#f59e0b','#2563eb']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'text.color':'#18212C','axes.labelcolor':'#18212C','xtick.color':'#64748B','ytick.color':'#18212C','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#CBD5E1','savefig.facecolor':'white'})
fig,ax=plt.subplots(figsize=(11.4,5.6));fig.subplots_adjust(left=.30,right=.90,bottom=.19,top=.75)
for i,((k,n),color) in enumerate(zip(counts,colors)):
 v=k/n;z=1.959963984540054;d=1+z*z/n;c=(v+z*z/(2*n))/d;h=z*sqrt(v*(1-v)/n+z*z/(4*n*n))/d
 lo,hi=c-h,c+h;y=3-i
 ax.barh(y,100*v,height=.44,color=color,zorder=2)
 ax.errorbar(100*v,y,xerr=[[100*(v-lo)],[100*(hi-v)]],fmt='none',ecolor='#354052',capsize=5,elinewidth=1.6,zorder=3)
 ax.text(100*hi+1,y,f'{100*v:.1f}%',va='center',fontsize=14)
fig.text(.045,.91,'SFT vs. RL vs. SFT + RL on the Stage-3 checkpoint',fontsize=20,fontproperties=TITLE_FONT,va='top')
fig.text(.045,.79,'SWE-bench Verified random-100',fontsize=13,color='#64748B')
ax.set_yticks([3,2,1,0],labels,fontsize=12);ax.set(xlim=(0,45),ylim=(-.55,3.6),xlabel='Pass@1 (%)')
ax.set_xticks([0,10,20,30,40]);ax.xaxis.set_major_formatter(PercentFormatter(100,decimals=0))
ax.set_axisbelow(True);ax.grid(axis='x',color='#E8EDF3',lw=.8);ax.tick_params(length=0,pad=10);ax.xaxis.labelpad=12
fig.savefig(a.output,dpi=180);fig.savefig(a.output.with_suffix('.svg'))
p=a.output.with_suffix('.svg');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print('Saved',a.output)
