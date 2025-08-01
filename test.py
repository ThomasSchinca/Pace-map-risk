# -*- coding: utf-8 -*-
"""
Created on Tue Nov  7 13:31:17 2023

@author: thoma
"""

import pandas as pd
from shape import Shape,finder
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MaxNLocator, FuncFormatter
import numpy as np
import geopandas as gpd
import seaborn as sns
import pickle
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
from datetime import datetime,timedelta
import math
from matplotlib.font_manager import FontProperties
from matplotlib import font_manager
from PIL import Image


df = pd.read_csv("https://ucdp.uu.se/downloads/ged/ged251-csv.zip",
                  parse_dates=['date_start','date_end'],low_memory=False)
month = datetime.now().strftime("%m")

if month=='01':
   month='13'
for i in range(1,int(month)):
    df_can = pd.read_csv(f'https://ucdp.uu.se/downloads/candidateged/GEDEvent_v25_0_{i}.csv')
    df_can.columns = df.columns
    df_can['date_start'] = pd.to_datetime(df_can['date_start'])
    df_can['date_end'] = pd.to_datetime(df_can['date_end'])
    df_can = df_can.drop_duplicates()
    df= pd.concat([df,df_can],axis=0)

df_tot = pd.DataFrame(columns=df.country.unique(),index=pd.date_range(df.date_start.min(),
                                          df.date_end.max()))
df_tot=df_tot.fillna(0)
for i in df.country.unique():
    df_sub=df[df.country==i]
    for j in range(len(df_sub)):
        if df_sub.date_start.iloc[j].month == df_sub.date_end.iloc[j].month:
            df_tot.loc[df_sub.date_start.iloc[j],i]=df_tot.loc[df_sub.date_start.iloc[j],i]+df_sub.best.iloc[j]
        else:
            pass                                                    
                                                     
df_tot_m=df_tot.resample('M').sum()
last_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
df_tot_m= df_tot_m.loc[:last_month,:]
df_tot_m.to_csv('Conf.csv')
del df
del df_tot
#df_tot_m = pd.read_csv('Conf.csv',parse_dates=True,index_col=(0))


df_conf=pd.read_csv('reg_coun.csv',index_col=0,squeeze=True)
common_columns = df_tot_m.columns.intersection(df_conf.index)
df_tot_m = df_tot_m.loc[:, common_columns]
df_next = {0:pd.DataFrame(columns=df_tot_m.columns,index=range(16)),1:pd.DataFrame(columns=df_tot_m.columns,index=range(16)),2:pd.DataFrame(columns=df_tot_m.columns,index=range(16))}
df_perc = pd.DataFrame(columns=df_tot_m.columns,index=range(3))
dict_sce = {i :[[],[],[]] for i in df_tot_m.columns}

h_train=10
h=6
pred_tot=[]
pred_raw=[]
dict_m={i :[] for i in df_tot_m.columns}
dict_sce_plot = {i :[[],[]] for i in df_tot_m.columns}
for coun in range(len(df_tot_m.columns)):
    if not (df_tot_m.iloc[-h_train:,coun]==0).all():
        shape = Shape()
        shape.set_shape(df_tot_m.iloc[-h_train:,coun]) 
        find = finder(df_tot_m.iloc[:-h,:],shape)
        find.find_patterns(min_d=0.1,select=True,metric='dtw',dtw_sel=2,min_mat=3,d_increase=0.05)
        # min_d_d=0.1
        # while len(find.sequences)<3:
        #     min_d_d += 0.05
        #     find.find_patterns(min_d=min_d_d,select=True,metric='dtw',dtw_sel=2)
        pred_ori = find.predict(horizon=h,plot=False,mode='mean')
        find.create_sce(df_conf,h)
        pred_raw.append(pred_ori)
        sce_ts = find.val_sce
        sce_ts.columns = pd.date_range(start=df_tot_m.iloc[-h_train:,coun].index[-1] + pd.DateOffset(months=1), periods=6, freq='M')
        dict_sce_plot[df_tot_m.columns[coun]][0]=find.sce
        dict_sce_plot[df_tot_m.columns[coun]][1]=sce_ts
        
        pred_ori = pred_ori*(df_tot_m.iloc[-h_train:,coun].max()-df_tot_m.iloc[-h_train:,coun].min())+df_tot_m.iloc[-h_train:,coun].min()
        pred_tot.append(pred_ori)
        dict_m[df_tot_m.columns[coun]]=find.sequences
        seq_pred =find.predict(horizon=h,plot=False,mode='mean',seq_out=True)
        y_pred = np.full((len(seq_pred),),np.nan)
        y_pred[seq_pred.sum(axis=1)<=1.5] = 0
        y_pred[(seq_pred.sum(axis=1)>1.5) & (seq_pred.sum(axis=1)<5)] = 1
        y_pred[seq_pred.sum(axis=1)>=5] = 2
        
        perc=[]
        for i in range(3):
            if len(seq_pred[y_pred==i]) != 0:
                norm = seq_pred[y_pred==i].mean() * (df_tot_m.iloc[-h_train:,coun].max()-df_tot_m.iloc[-h_train:,coun].min()) + df_tot_m.iloc[-h_train:,coun].min()
                norm.index = pd.date_range(start=df_tot_m.iloc[-h_train:,coun].index[-1] + pd.DateOffset(months=1), periods=6, freq='M')
                seq_f = pd.concat([df_tot_m.iloc[-h_train:,coun],norm],axis=0)
                index_s = seq_f.index
                seq_f = seq_f.reset_index(drop=True)
                df_next[i].iloc[:,coun] = seq_f
            else : 
                df_next[i].iloc[:,coun] = [float('nan')]*16
            perc.append(round(len(seq_pred[y_pred==i])/len(seq_pred)*100,1))
        df_perc.iloc[:,coun]=perc
        
        y_pred_p = y_pred.astype(float)
        count_zeros = 0
        count_ones = 0
        count_twos = 0
        for i in range(len(y_pred_p)):
            value = y_pred_p[i]
            norm = seq_pred.iloc[i,:]*(find.sequences[i][0].max()-find.sequences[i][0].min())+ find.sequences[i][0].min()
            norm.index = pd.date_range(start=find.sequences[i][0].index[-1] + pd.DateOffset(months=1), periods=6, freq='M')
            seq_f = pd.concat([find.sequences[i][0],norm],axis=0)
            seq_f.name = find.sequences[i][0].name
            if value == 0 and count_zeros<5:   
                dict_sce[df_tot_m.columns[coun]][0].append(seq_f)
                count_zeros += 1
            elif value == 1 and count_ones<5:
                dict_sce[df_tot_m.columns[coun]][1].append(seq_f)
                count_ones += 1
            elif value == 2 and count_twos<5:
                dict_sce[df_tot_m.columns[coun]][2].append(seq_f)
                count_twos += 1
            else:
                pass
    else :
        pred_tot.append(pd.DataFrame(np.zeros((h,3))))
        pred_raw.append(pd.DataFrame(np.zeros((h,3))))
        
with open('saved_dictionary.pkl', 'wb') as f:
    pickle.dump(dict_m, f)

    
pred_df = [df.iloc[:, 0] for df in pred_raw]
pred_df = pd.concat(pred_df, axis=1)
pred_df.columns = df_tot_m.columns
pred_df = pred_df.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                    'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                    'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                    'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                    'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                    'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})

pred_df.to_csv('Pred_df.csv')
pred_df_m = [df.iloc[:, 1] for df in pred_raw]
pred_df_m = pd.concat(pred_df_m, axis=1)
pred_df_m.columns = df_tot_m.columns
pred_df_m = pred_df_m.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                    'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                    'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                    'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                    'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                    'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})

pred_df_m.to_csv('Pred_df_min.csv')
pred_df_m = [df.iloc[:, 2] for df in pred_raw]
pred_df_m = pd.concat(pred_df_m, axis=1)
pred_df_m.columns = df_tot_m.columns
pred_df_m = pred_df_m.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia', 'Dominican Republic':'Dominican Rep.',
                                    'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                    'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini',
                                    'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                    'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                    'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})

pred_df_m.to_csv('Pred_df_max.csv')


#pred_df=pd.read_csv('Pred_df.csv',parse_dates=True,index_col=(0))
pred_df = [df.iloc[:, 0] for df in pred_tot]
pred_df = pd.concat(pred_df, axis=1)
pred_df.columns = df_tot_m.columns
pred_df = pred_df.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                    'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                    'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                    'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                    'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                    'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})


histo = df_tot_m.iloc[-h:,:]
histo = histo.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                   'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                   'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                   'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                   'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                   'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})
histo = histo.sum().reset_index()
histo.columns=['name','hist']


df_tot_m_plot=df_tot_m.iloc[-h_train:,:]
df_tot_m_plot = df_tot_m_plot.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                   'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                   'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                   'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                   'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                   'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})
df_tot_m_plot.to_csv('Hist.csv')
df_tot_m_plot.index = df_tot_m_plot.index.strftime('%b %y')

df_next[0].index = index_s
df_next[1].index = index_s
df_next[2].index = index_s

def rena_f(df):
    df = df.rename(columns={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                    'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                    'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                    'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                    'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                    'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'})
    return df

df_perc=rena_f(df_perc)
df_next[0]=rena_f(df_next[0])
df_next[1]=rena_f(df_next[1])
df_next[2]=rena_f(df_next[2])

df_perc.to_csv('perc.csv')
df_next[0].to_csv('dec.csv')
df_next[1].to_csv('sta.csv')
df_next[2].to_csv('inc.csv')

rena={'Bosnia-Herzegovina':'Bosnia and Herz.','Cambodia (Kampuchea)':'Cambodia',
                                   'Central African Republic':'Central African Rep.','DR Congo (Zaire)':'Dem. Rep. Congo',
                                   'Ivory Coast':'Côte d\'Ivoire','Kingdom of eSwatini (Swaziland)':'eSwatini', 'Dominican Republic':'Dominican Rep.',
                                   'Macedonia, FYR':'Macedonia','Madagascar (Malagasy)':'Madagascar','Myanmar (Burma)':'Myanmar', 'North Macedonia':'Macedonia',
                                   'Russia (Soviet Union)':'Russia','Serbia (Yugoslavia)':'Serbia','South Sudan':'S. Sudan',
                                   'Yemen (North Yemen)':'Yemen','Zimbabwe (Rhodesia)':'Zimbabwe','Vietnam (North Vietnam)':'Vietnam'}
dict_sce_f = {rena[key] if key in rena else key: item for key, item in dict_sce.items()}
with open('dict_sce.pkl', 'wb') as f:
    pickle.dump(dict_sce_f, f)
    
dict_sce_plot_f = {rena[key] if key in rena else key: item for key, item in dict_sce_plot.items()}
with open('sce_dictionary.pkl', 'wb') as f:
    pickle.dump(dict_sce_plot_f, f)


pred_df_sce = []
for i,col in enumerate(pred_df):
    df_scen = dict_sce_plot_f[col][1]
    if len(df_scen)>0:
        indi = pd.Series(df_scen.index)
        max_indices = indi[indi == indi.max()].index.tolist()
        bef = df_tot_m_plot.loc[:,col]
        pred_df_sce.append((df_scen.iloc[max_indices,:].mean()*(bef.max()-bef.min())+ bef.min()).tolist())
        ind_sce = df_scen.columns
    else:
        pred_df_sce.append([0]*h)
pred_df_sce = pd.DataFrame(pred_df_sce).T
pred_df_sce.index=ind_sce
pred_df_sce.columns=pred_df.columns

value_pred = pred_df_sce.sum().reset_index()
value_pred.columns=['name','value']

world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
world = world.merge(value_pred, how='left',on='name')
world = world.merge(histo, how='left',on='name')
world = world[world.name != 'Antarctica']
world = world.fillna(0)
world.loc[world['value'] < 0, 'value'] = 0
world['per_pred']=world['value']/world['pop_est']
world['log_per_pred']=np.log10(world['value']+1)
world.to_file('world_plot.geojson', driver='GeoJSON') 


font_path = 'Poppins/Poppins-Regular.ttf'
prop = FontProperties(fname=font_path)
font_manager.fontManager.addfont(font_path)
prop = font_manager.FontProperties(fname=font_path)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = prop.get_name()

# =============================================================================
# Global Map
# =============================================================================

fig, ax = plt.subplots(1, 1, figsize=(30, 15))
world.boundary.plot(ax=ax, color='black')
norm = mcolors.Normalize(vmin=0, vmax=math.ceil(max(world['log_per_pred'])))
mapping = world.plot(column='log_per_pred', cmap='Reds', ax=ax, norm=norm)
plt.xlim(-180, 180)
plt.box(False)
ax.spines['left'].set_visible(False)
ax.set_yticklabels([])
ax.set_yticks([])
ax.set_xticklabels([])
ax.set_xticks([])
cbar_ax = fig.add_axes([0.65, 0.15, 0.3, 0.02]) 
sm = ScalarMappable(cmap='Reds', norm=norm)
sm.set_array([]) 
cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal')
cbar.set_ticks([*range(math.ceil(max(world['log_per_pred']))+1)])
cbar.set_ticklabels(['1']+[f'$10^{e}$' for e in range(1,math.ceil(max(world['log_per_pred']))+1)],fontsize=20)
plt.text(1.9,1.5,'Risk index', fontsize=30)
plt.text(-8.5,0.1,'The risk index corresponds to the log sum of predicted fatalities in the next 6 months.',color='dimgray', fontdict={'style': 'italic','size':20})
plt.savefig('Images/map.png', bbox_inches='tight')
plt.savefig('docs/Images/map.png', bbox_inches='tight')
plt.show()

# =============================================================================
# Historical Plot
# =============================================================================
pred_df_sce.index = pd.date_range(start=df_tot_m.index[-1],periods=h+1,freq='M')[1:]
historical_series = pd.concat([df_tot_m.sum(axis=1).iloc[-60:],pred_df_sce.sum(axis=1)],axis=0)
date_rng = historical_series.index

plt.figure(figsize=(25, 6))
plt.plot(date_rng[:-h+1], historical_series[:-h+1], marker='o', color='grey', linestyle='-', linewidth=2, markersize=8)
plt.plot(date_rng[-h:], historical_series[-h:], marker='o', color='red', linestyle='-', linewidth=2, markersize=8)
plt.scatter(date_rng[-h:], historical_series[-h:], color='red', s=100, zorder=5)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.xlabel('Date', fontsize=20)
plt.xticks(fontsize=16)
plt.yticks(fontsize=16)
plt.box(False)
plt.xticks(rotation=45, ha='right')
plt.savefig('Images/sub1_1.png', bbox_inches='tight')
plt.savefig('docs/Images/sub1_1.png', bbox_inches='tight')
plt.show()

# =============================================================================
# Risk Countries
# =============================================================================

pred_risk = world.sort_values('value',ascending=False)[['name','value','hist']][:10]
df_plot =pred_risk.set_index('name').sort_values('value',ascending=True)
df_plot['color'] = np.where(df_plot['value'] > df_plot['hist'], 'red', 'black')
def calculate_alpha(row):
    diff_ratio = abs(row['value'] - row['hist']) / (row['hist']+1)
    return np.clip(diff_ratio / 2 +0.5 , 0, 1)
df_plot['alpha'] = df_plot.apply(calculate_alpha, axis=1)

fig, ax = plt.subplots(1, 1, figsize=(10, 6))
ax = sns.barplot(x=df_plot.index, y='value', data=df_plot, palette=df_plot['color'])
for i, bar in enumerate(ax.patches):
    bar.set_alpha(df_plot['alpha'].iloc[i])
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
# ax.set_yticklabels(ax.get_yticklabels(), rotation=45, ha='right',color='white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color('#DDDDDD')
ax.tick_params(bottom=False)
# ax.yaxis.grid(True, color='#EEEEEE',alpha=1)
# ax.xaxis.grid(False)
plt.xlabel('')
plt.ylabel('')
plt.yscale('log')
plt.xticks(fontsize=16)
plt.yticks(fontsize=16)
ax.spines['left'].set_visible(False)
ax.set_yticklabels([])
ax.set_yticks([])
ax.get_yaxis().get_major_formatter().labelOnlyBase = False
ax.get_yaxis().set_tick_params(which='minor', size=0,labelcolor='white')
ax.get_yaxis().set_tick_params(which='minor', width=0,labelcolor='white') 
plt.savefig('Images/sub2.png', bbox_inches='tight')
plt.show()


# =============================================================================
# Increase risk
# =============================================================================

pred_risk = world.sort_values('value',ascending=False)[['name','value','hist']]
df_plot =pred_risk.set_index('name').sort_values('value',ascending=True)
df_plot['color'] = np.where(df_plot['value'] > df_plot['hist'], 'red', 'black')
def calculate_alpha(row):
    diff_ratio = abs(row['value'] - row['hist']) / (row['hist']+1)
    return np.clip(diff_ratio / 2 +0.5 , 0, 1)
df_plot['alpha'] = df_plot.apply(calculate_alpha, axis=1)
df_plot['diff'] = df_plot['value'] - df_plot['hist']
df_plot = df_plot.sort_values('diff')

df_plot_d = df_plot.iloc[:10]
#df_plot_d['alpha'] = 1-df_plot_d['alpha']
df_plot_d['diff'] = -df_plot_d['diff']
df_plot_d = df_plot_d.sort_values('diff',ascending=True)

fig, ax = plt.subplots(1, 1, figsize=(10, 6))
ax = sns.barplot(x=df_plot_d.index, y='diff', data=df_plot_d, palette=df_plot_d['color'])
for i, bar in enumerate(ax.patches):
    bar.set_alpha(df_plot_d['alpha'].iloc[i])
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#DDDDDD')
ax.tick_params(bottom=False, left=False)
ax.set_axisbelow(True)
ax.yaxis.grid(True, color='#EEEEEE')
ax.xaxis.grid(False)
plt.xlabel('')
plt.ylabel('')
plt.yscale('log')
plt.xticks(fontsize=16)  # Set x-axis tick font size
ax.spines['left'].set_visible(False)
ax.set_yticklabels([])
ax.set_yticks([])
ax.get_yaxis().get_major_formatter().labelOnlyBase = False
ax.get_yaxis().set_tick_params(which='minor', size=0,labelcolor='white')
ax.get_yaxis().set_tick_params(which='minor', width=0,labelcolor='white') 
plt.savefig('Images/sub2_d.png', bbox_inches='tight')
plt.show()

df_plot_d = df_plot.iloc[-10:]

fig, ax = plt.subplots(1, 1, figsize=(10, 6))
ax = sns.barplot(x=df_plot_d.index, y='diff', data=df_plot_d, palette=df_plot_d['color'])
for i, bar in enumerate(ax.patches):
    bar.set_alpha(df_plot_d['alpha'].iloc[i])
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#DDDDDD')
ax.tick_params(bottom=False, left=False)
ax.set_axisbelow(True)
ax.yaxis.grid(True, color='#EEEEEE')
ax.xaxis.grid(False)
plt.xlabel('')
plt.ylabel('')
plt.yscale('log')
plt.xticks(fontsize=16)
ax.spines['left'].set_visible(False)
ax.set_yticklabels([])
ax.set_yticks([])
ax.get_yaxis().get_major_formatter().labelOnlyBase = False
ax.get_yaxis().set_tick_params(which='minor', size=0,labelcolor='white')
ax.get_yaxis().set_tick_params(which='minor', width=0,labelcolor='white') 
plt.savefig('Images/sub2_i.png', bbox_inches='tight')
plt.show()



# =============================================================================
# New Specific
# =============================================================================
#df_tot_m_plot=pd.read_csv('Hist.csv',parse_dates=True,index_col=(0))

def paste_images_side_by_side(image1_path, image2_path, output_path):
    image1 = Image.open(image1_path)
    image2 = Image.open(image2_path)
    height = max(image1.height, image2.height)
    image1 = image1.resize((int(image1.width * height / image1.height), height))
    image2 = image2.resize((int(image2.width * height / image2.height), height))
    new_width = image1.width + image2.width
    new_image = Image.new("RGB", (new_width, height))
    new_image.paste(image1, (0, 0))
    new_image.paste(image2, (image1.width, 0))
    new_image.save(output_path)

df_plot =pred_risk.set_index('name').sort_values('value',ascending=True)
df_tot_m=rena_f(df_tot_m)
indo=[]
for coun in range(1,5):
    indo.append(df_tot_m.columns.tolist().index(df_plot.index[-coun]))
indo.reverse()
df_best = pd.DataFrame(df_plot.index[-4:])
df_best['find']=indo
df_best.to_csv('best.csv')

def format_ticks(x, pos):
    if x == 0:
        return ''
    else:
        return '{:d}'.format(int(x))

def plot_horizontal_bar(df,names,ax,typ,maxi):
    if typ=='reg':
        li=['Africa','Americas','Asia','Europe','Middle East']
    elif typ=='dec':
        li=['90-2000','2000-2010','2010-2020','2020-Now']
    else:
        li=['<10','10-100','100-1000','>1000']
    for i,name in enumerate(li):
        if name in df.index:
            if df[name]>0:
                rect = FancyBboxPatch((0, i-0.25),width=df[name],height=0.5, boxstyle="round,pad=-0.0040,rounding_size=0.03", ec="none", fc='#808080', mutation_aspect=4)
                ax.add_patch(rect)
            else:
                pass
        else:
            pass
        
    if maxi>5:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    elif (maxi>2)&(maxi<=5):
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
    else:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=2, integer=True))
    ax.tick_params(axis='x', labelsize=20)
    formatter = FuncFormatter(format_ticks)
    ax.xaxis.set_major_formatter(formatter)
    ax.set_yticks([*range(len(li))],li,fontsize=20,color='#808080')
    ax.set_frame_on('y')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)  
    ax.set_ylim(-0.5,len(li)-0.5)
    ax.set_xlim(0,maxi)
    ax.set_title(names,fontsize=30,pad=20,color='#808080')  
    ax.grid(axis='x', linestyle='--', alpha=0.7,color='#808080')
    for tick in ax.xaxis.get_major_ticks():
        tick.label1.set_color('gray')

rena_rev = {v: k for k, v in rena.items()}
pred_risk = world.sort_values('value',ascending=False)[['name','value','hist']]
df_plot =pred_risk.set_index('name').sort_values('value',ascending=True)
h_train=10
h=6
for coun in range(1,5):
    sub_name = df_plot.index[-coun]
    
    if sub_name in rena_rev:
        sub_name_before = rena_rev[sub_name]
    else:
        sub_name_before = sub_name
     
    fig,ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.plot(df_tot_m_plot.loc[:,sub_name], marker='o', color='black', linestyle='-', linewidth=2, markersize=8)
    #ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.tick_params(axis='x', labelsize=25)
    ax.tick_params(axis='y', labelsize=25)
    #ax.set_title(df_tot_m_plot.loc[:,sub_name].name, fontsize=40, font='Poppins')
    ax.set_frame_on(False)
    plt.tight_layout()
    plt.savefig(f'Images/ex{coun}.png', bbox_inches='tight')
    plt.show()
    
    fig,ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.plot(df_tot_m_plot.loc[:,sub_name], marker='o', color='black', linestyle='-', linewidth=2, markersize=8)
    #ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.tick_params(axis='x', labelsize=25)
    ax.tick_params(axis='y', labelsize=25)
    ax.set_title(df_tot_m_plot.loc[:,sub_name].name, fontsize=40, font='Poppins')
    ax.set_frame_on(False)
    plt.tight_layout()
    plt.savefig(f'docs/Images/ex{coun}.png', bbox_inches='tight')
    plt.show()
    
    
    # fig,ax = plt.subplots(1, 3, figsize=(12, 6))
    # maxi=max([dict_sce[sub_name][0]['Region'].value_counts().max(),dict_sce[sub_name][0]['Decade'].value_counts().max(),dict_sce[sub_name][0]['Scale'].value_counts().max()])
    # plot_horizontal_bar(dict_sce[sub_name][0]['Region'].value_counts(), 'Where ?', ax[0],'reg',maxi)
    # plot_horizontal_bar(dict_sce[sub_name][0]['Decade'].value_counts(), 'When ?', ax[1],'dec',maxi)
    # plot_horizontal_bar(dict_sce[sub_name][0]['Scale'].value_counts(), 'Sum of Fatalities ?', ax[2],'sca',maxi)
    # plt.tight_layout()
    # plt.savefig(f'Images/ex{coun}_all.png', bbox_inches='tight')
    # plt.show()
    
    fig,ax = plt.subplots(2, 2, figsize=(12, 6))
    ax = ax.flatten()
    for c in range(4):
        try:
            ax[c].plot(dict_m[sub_name_before][c][0], marker='o', color='#808080', linestyle='-', linewidth=2, markersize=8)
            ax[c].xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %y'))
            ax[c].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=4))
            ax[c].grid(axis='y', linestyle='--', alpha=0.7)
            ax[c].tick_params(axis='x', labelsize=15,color='#808080')
            ax[c].tick_params(axis='y', labelsize=15,color='#808080')
            ax[c].set_title(dict_m[sub_name_before][c][0].name, fontsize=20, font='Poppins',color='#808080')
            ax[c].set_frame_on(False)
        except:
            ax[c].set_frame_on(False)
            ax[c].axis('off')
    plt.tight_layout()
    plt.savefig(f'Images/ex{coun}_all.png', bbox_inches='tight')
    plt.show()
    
    
    if len(dict_sce_plot_f[sub_name][1])>2:
        fig, ax = plt.subplot_mosaic([[0,0,0,0,0,3],
                                      [1,1,1,1,1,4],
                                      [2,2,2,2,2,5]], figsize=(10, 8))
    elif len(dict_sce_plot_f[sub_name][1])==2:
        fig, ax = plt.subplot_mosaic([[2,2,2,2,2,9],
                                      [0,0,0,0,0,3],
                                      [0,0,0,0,0,3],
                                      [0,0,0,0,0,3],
                                      [5,5,5,5,5,6],
                                      [1,1,1,1,1,4],
                                      [1,1,1,1,1,4],
                                      [1,1,1,1,1,4],
                                      [7,7,7,7,7,8]], figsize=(10, 8))    
        ax[6].axis('off')
        ax[7].axis('off')
        ax[8].axis('off')
        ax[9].axis('off')
    else :
        fig, ax = plt.subplot_mosaic([[1,1,1,1,1,4],
                                      [0,0,0,0,0,3],
                                      [2,2,2,2,2,5]], figsize=(10, 8))    
    for c in range(3):
        try:
            if int(dict_sce_plot_f[sub_name][1].iloc[pd.Series(dict_sce_plot_f[sub_name][1].index).sort_values(ascending=False).index[c],:].name*100)>=50:
                colu="#df2226"
            else:
                sup1=hex(34+(50-int(dict_sce_plot_f[sub_name][1].iloc[pd.Series(dict_sce_plot_f[sub_name][1].index).sort_values(ascending=False).index[c],:].name*100))*3)[2:]
                sup2=hex(38+(50-int(dict_sce_plot_f[sub_name][1].iloc[pd.Series(dict_sce_plot_f[sub_name][1].index).sort_values(ascending=False).index[c],:].name*100))*3)[2:]
                colu='#df'+str(sup1)+str(sup2)
            scen = dict_sce_plot_f[sub_name][1].iloc[pd.Series(dict_sce_plot_f[sub_name][1].index).sort_values(ascending=False).index[c],:].tolist()
            b = (df_tot_m_plot.loc[:,sub_name] - df_tot_m_plot.loc[:,sub_name].min())/(df_tot_m_plot.loc[:,sub_name].max()-df_tot_m_plot.loc[:,sub_name].min())
            scen = pd.Series(b.tolist()+scen)
            scen = scen*(df_tot_m_plot.loc[:,sub_name].max()-df_tot_m_plot.loc[:,sub_name].min()) + df_tot_m_plot.loc[:,sub_name].min()
            ax[c].plot(scen, color='gray', linestyle='-', linewidth=2)
            ax[c].plot(scen.iloc[-7:], color=colu, linestyle='-', linewidth=5)
            ax[c].set_frame_on(False)
            ax[c].set_xticks([10,11,12,13,14,15],[f't+{i}' if i not in [1, 3, 5] else '' for i in range(1, 7)])
            ax[c].yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
            ax[c].tick_params(axis='y', labelsize=20)
            ax[c].tick_params(axis='x', labelsize=20,rotation=30)
            ax[c].grid('y',alpha=0.5)
            ax[c].spines['top'].set_visible(False)
            ax[c].spines['right'].set_visible(False)  
            ax[c].spines['bottom'].set_visible(False)
            ax[c].spines['left'].set_visible(False)
            ax[c+3].text(0.1,0.4,f'Freq = {int(dict_sce_plot_f[sub_name][1].iloc[pd.Series(dict_sce_plot_f[sub_name][1].index).sort_values(ascending=False).index[c],:].name*100)}%',fontsize=30,color=colu)
            ax[c+3].set_frame_on(False)
            ax[c+3].set_xticks([])
            ax[c+3].set_yticks([])
        except:
            ax[c].axis('off')
            ax[c+3].axis('off')
    
    plt.tight_layout()
    plt.savefig(f'Images/ex{coun}_sce.png', bbox_inches='tight')
    plt.savefig(f'docs/Images/ex{coun}_sce.png', bbox_inches='tight')
    plt.show()

    paste_images_side_by_side(f'docs/Images/ex{coun}.png', f'docs/Images/ex{coun}_sce.png', f'docs/Images/ex{coun}_tot.png')

