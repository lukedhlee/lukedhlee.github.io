from pathlib import Path
import json
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

OUT=Path(__file__).resolve().parents[1]/'assets/img/snowball'
data=json.loads((Path(__file__).parent/'data/snowball_intro_comparison.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--palette',choices=['current','a','b','c'],default='b')
args=parser.parse_args()
palettes={
 'current':('#5b8ff9','#aa87eb','#64c6a5'),
 'a':('#83adf5','#b99bee','#82d3b5'),
 'b':('#4f8af5','#a275ea','#45c69c'),
 'c':('#69b5ee','#c18ce4','#8dce91'),
}
BLUE,PURPLE,GREEN=palettes[args.palette]
RL_BLUE='#8bb5fa'; GRAY='#c4cbd5'; INK='#283747'; MUTED='#68788c'
NAME='intro-ranked-bars'

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':MUTED,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'svg.fonttype':'path'})
fig,axes=plt.subplots(1,3,figsize=(21,6.4),sharey=True)
fig.subplots_adjust(left=.055,right=.98,bottom=.25,top=.75,wspace=.16)
fig.text(.005,.94,'Snowball 67B–A2B and reference models · Pass@1 with Terminus-2',fontsize=12,color=MUTED)
handles=[Line2D([],[],marker='s',linestyle='none',color=RL_BLUE,markersize=9,label='Snowball + RL'),Line2D([],[],marker='s',linestyle='none',color=GRAY,markersize=9,label='Snowball 09-21'),Line2D([],[],marker='s',linestyle='none',color=BLUE,markersize=9,label='Snowball + coding SFT + RL'),Line2D([],[],marker='s',linestyle='none',color=PURPLE,markersize=9,label='Qwen3.5'),Line2D([],[],marker='s',linestyle='none',color=GREEN,markersize=9,label='Nemotron 3.5 Lightning')]
fig.legend(handles=[handles[1],handles[0],*handles[2:]],loc='upper left',bbox_to_anchor=(.005,.90),ncol=5,frameon=False,fontsize=11,columnspacing=1.8,borderaxespad=0,borderpad=0,handlelength=.8,handletextpad=.6,alignment='left')
labels={'Snowball 09-21':'09-21','Snowball direct RL':'RL','Snowball SFT + RL (step 60)':'SFT + RL','Qwen3.5-4B':'Qwen3.5\n4B','Qwen3.5-9B':'Qwen3.5\n9B','Qwen3.5-35B-A3B':'Qwen3.5\n35B-A3B','Nemotron-3.5-Lightning-30B-A3B':'Nemotron\nLightning\n30B-A3B'}
# Snowballs on the left, reference models on the right; each group sorted low to high per benchmark.
SNOWBALLS=['Snowball 09-21','Snowball direct RL','Snowball SFT + RL (step 60)']
REFERENCES=['Qwen3.5-4B','Qwen3.5-9B','Qwen3.5-35B-A3B','Nemotron-3.5-Lightning-30B-A3B']
GAP=.55
by_model={r['model']:r for r in data}
xs=list(range(len(SNOWBALLS)))+[len(SNOWBALLS)+GAP+i for i in range(len(REFERENCES))]
groups=[('Snowball 67B-A2B',xs[0],xs[len(SNOWBALLS)-1]),('Reference models',xs[len(SNOWBALLS)],xs[-1])]
for ax,key,title in zip(axes,['tb','swe','tblite'],['Terminal-Bench 2.1','SWE-bench Verified random-100','OpenThoughts-TBLite']):
    rows=[r for g in (SNOWBALLS,REFERENCES) for r in sorted((by_model[m] for m in g),key=lambda r:r[key])]
    ax.set_title(title,fontsize=13,loc='left',pad=19,weight='medium')
    ax.set_xlim(-.6,xs[-1]+.6); ax.set_ylim(0,72)
    ax.set_yticks([0,20,40,60]); ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    ax.grid(axis='y',color='#dfe4eb',linestyle=(0,(2,4)),lw=.9); ax.set_axisbelow(True)
    for x,row in zip(xs,rows):
        color=RL_BLUE if row['model']=='Snowball direct RL' else GRAY if row['model']=='Snowball 09-21' else (BLUE if row['model'].startswith('Snowball') else (GREEN if row['model'].startswith('Nemotron') else PURPLE))
        h=row[key]
        bar=FancyBboxPatch((x-.34,0),.68,h,boxstyle='round,pad=0,rounding_size=0.55',facecolor=color,edgecolor='none',zorder=3)
        ax.add_patch(bar)
        ax.text(x,max(3.5,h*.52),f'{h:.1f}',ha='center',va='center',color='white',fontsize=12,weight='bold',zorder=4)
    sep=(xs[len(SNOWBALLS)-1]+xs[len(SNOWBALLS)])/2
    ax.axvline(sep,ymin=0,ymax=.92,color='#c9d1dc',lw=1,zorder=1)
    ax.set_xticks(xs,[labels[r['model']] for r in rows],fontsize=9)
    ax.tick_params(length=0,pad=11)
    for tick,row in zip(ax.get_xticklabels(),rows):
        if row['model']=='Snowball SFT + RL (step 60)':
            tick.set_color(BLUE); tick.set_weight('bold')
    trans=ax.get_xaxis_transform()
    for name,x0,x1 in groups:
        ax.plot([x0-.34,x1+.34],[-.205,-.205],transform=trans,clip_on=False,color='#9aa7b6',lw=1)
        ax.text((x0+x1)/2,-.235,name,transform=trans,ha='center',va='top',fontsize=10.5,color=INK,weight='medium')
axes[0].set_ylabel('Pass@1 (%)',labelpad=12)
for ext in ['png','svg','pdf']:
    fig.savefig(OUT/f'{NAME}.{ext}',dpi=600,facecolor='white',bbox_inches='tight',pad_inches=.38)
print(OUT/f'{NAME}.png')
