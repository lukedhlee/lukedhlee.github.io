from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

OUT=Path(__file__).resolve().parents[1] / 'assets/img/snowball'
data=json.loads((Path(__file__).parent/'data/snowball_intro_comparison.json').read_text())
BLUE='#2563eb'; GRAY='#a2acb9'; PURPLE='#8b62b1'; INK='#283747'; MUTED='#68788c'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':MUTED,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'svg.fonttype':'path'})
fig,axes=plt.subplots(1,3,figsize=(16,6.4),sharey=True)
fig.subplots_adjust(left=.055,right=.98,bottom=.25,top=.75,wspace=.16)
fig.text(.005,.94,'Snowball 67B–A2B and Qwen3.5 references · Pass@1 with Terminus-2',fontsize=12,color=MUTED)
handles=[Line2D([],[],marker='s',linestyle='none',color=GRAY,markersize=9,label='Snowball 09-21'),Line2D([],[],marker='s',linestyle='none',color=BLUE,markersize=9,label='Snowball + coding SFT + RL'),Line2D([],[],marker='s',linestyle='none',color=PURPLE,markersize=9,label='Qwen3.5 references')]
fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.005,.90),ncol=3,frameon=False,fontsize=11,columnspacing=2.5,borderaxespad=0,borderpad=0,handlelength=.8,handletextpad=.6,alignment='left')
labels={'Snowball 09-21':'Snowball\n09-21','Snowball SFT + RL (step 60)':'Snowball\nSFT + RL','Qwen3.5-35B-A3B':'Qwen3.5\n35B-A3B','Qwen3.5-9B':'Qwen3.5\n9B','Qwen3.5-4B':'Qwen3.5\n4B'}
for ax,key,title in zip(axes,['tb','swe','tblite'],['Terminal-Bench 2.1','SWE-bench Verified random-100','OpenThoughts-TBLite']):
    rows=sorted(data,key=lambda r:r[key],reverse=True)
    ax.set_title(title,fontsize=13,loc='left',pad=19,weight='medium')
    ax.set_xlim(-.6,4.6); ax.set_ylim(0,72)
    ax.set_yticks([0,20,40,60]); ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    ax.grid(axis='y',color='#dfe4eb',linestyle=(0,(2,4)),lw=.9); ax.set_axisbelow(True)
    for i,row in enumerate(rows):
        color=GRAY if row['model']=='Snowball 09-21' else (BLUE if row['model'].startswith('Snowball') else PURPLE)
        h=row[key]
        bar=FancyBboxPatch((i-.34,0),.68,h,boxstyle='round,pad=0,rounding_size=0.55',facecolor=color,edgecolor='none',zorder=3)
        ax.add_patch(bar)
        ax.text(i,max(3.5,h*.52),f'{h:.1f}',ha='center',va='center',color='white',fontsize=12,weight='bold',zorder=4)
    ax.set_xticks(range(5),[labels[r['model']] for r in rows],fontsize=10)
    ax.tick_params(length=0,pad=11)
    for tick,row in zip(ax.get_xticklabels(),rows):
        if row['model']=='Snowball SFT + RL (step 60)':
            tick.set_color(BLUE); tick.set_weight('bold')
axes[0].set_ylabel('Pass@1 (%)',labelpad=12)
for ext in ['png','svg','pdf']:
    fig.savefig(OUT/f'intro-ranked-bars.{ext}',dpi=400,facecolor='white',bbox_inches='tight',pad_inches=.38)
print(OUT/'intro-ranked-bars.png')
