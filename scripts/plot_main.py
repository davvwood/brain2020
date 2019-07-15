# -*- coding: utf-8 -*-
"""
Created on Mon May 27 17:44:03 2019

@author: Iluva
"""

from utils_data import AlzheimerDataWrapper, select_roi, load_neurologist_data
from model_bag import ModelBag
from utils_stat import get_roc_info, get_pr_info, calc_neurologist_statistics
import matplotlib.pyplot as plt
from utils_plot import plot_curve, plot_legend, plot_neorologist
from time import time
 
data_root = '../'
device = 'cpu'
roi_src_fn = '../metric/TRAIN_MCC.npy'
roi_thrshold = 0.6
dsets = ['ADNI', 'FHS', 'AIBL', 'NACC']
K = 100  # number of models per bag
load = True

# ROI
print('Constructing region of importance... ', end='')
roi = select_roi(roi_src_fn, roi_thrshold=0.6)
print('Done.')

# load data into dataframe
print('Loading data into Pandas dataframe... ', end='')
dw = AlzheimerDataWrapper()
dw.load(data_root, dsets, roi)
print('Done.')

# remove rows with missing values
dw.keep_data_completeness(['X_mmse'])

# prepare input data
# select columns from dataframe to form ndarray
print('Preparing data for models ... ', end='')
Xb, X_, y = {}, {}, {}
for m, c in zip(['A', 'B', 'C'],
                [['X_rmap'],
                 ['X_mmse', 'X_age', 'X_gender'],
                 ['X_rmap', 'X_mmse', 'X_age', 'X_gender']]):
    Xb[m], X_[m], y = dw.get_ndarray(cols=c)
print('Done.')

# create a bag of models
models_bag = {}
for m in ['A', 'B', 'C']:
    dimb = Xb[m]['ADNI_TRAIN'].shape[1] if Xb[m]['ADNI_TRAIN'] is not None else 0
    dim_ = X_[m]['ADNI_TRAIN'].shape[1] if X_[m]['ADNI_TRAIN'] is not None else 0 
    model_kwargs = {'dim_bn': dimb, 'dim_no_bn': dim_, 'device': device}
    models_bag[m] = ModelBag(model_kwargs, n_model=K)

# fit all models in the bag
# or load
if not load:
    for m in ['A', 'B', 'C']:
        print('Training model {}...'.format(m))
        fit_kwargs = {'X_bn': Xb[m]['ADNI_TRAIN'],
                      'X_no_bn': X_[m]['ADNI_TRAIN'],
                      'y': y['ADNI_TRAIN'], 
                      'n_epoch': 200}
        models_bag[m].fit(fit_kwargs)
        
    # save models
    timestmp = int(time())
    for m in ['A', 'B', 'C']:
        print('Saving models... ', end='')
        models_bag[m].save('./saved_mlp/main_{}_{}'.format(timestmp, m))
        print('Done.')
else:
    print('Loading models... ', end='')
    models_bag['A'].load('./saved_mlp/main_1561427936_A')
    models_bag['B'].load('./saved_mlp/main_1561427936_B')
    models_bag['C'].load('./saved_mlp/main_1561427936_C')
    print('Done.')

# evaluate performace
scores_bag = {}
for m in ['A', 'B', 'C']:
    scores_bag[m] = {}
    for ds in ['ADNI_TEST', 'AIBL', 'FHS', 'NACC']:
        eval_kwargs = {'X_bn': Xb[m][ds], 'X_no_bn': X_[m][ds]}
        scores_bag[m][ds] = models_bag[m].eval(eval_kwargs)

# collect essentials for plot
roc_info, pr_info = {}, {}
for m in ['A', 'B', 'C']:
    roc_info[m], pr_info[m] = {}, {}
    for ds in ['ADNI_TEST', 'AIBL', 'FHS', 'NACC']:
        roc_info[m][ds] = get_roc_info(y[ds], scores_bag[m][ds][:,:,1])
        pr_info[m][ds] = get_pr_info(y[ds], scores_bag[m][ds][:,:,1])

# neorologist
fn = '../Neurologist/Ground_Truth_Test.csv'
data = load_neurologist_data('../Neurologist/Ground_Truth_Test.csv')
neo_info = calc_neurologist_statistics(**data)

# plot
plt.style.use('fivethirtyeight')
plt.rcParams['axes.facecolor'] = 'w'
plt.rcParams['figure.facecolor'] = 'w'
plt.rcParams['savefig.facecolor'] = 'w'

# roc plot
fig, axes_ = plt.subplots(1, 4, figsize=[24, 6], dpi=100)
axes = dict(zip(['ADNI_TEST', 'AIBL', 'FHS', 'NACC'], axes_))
hdl_crv = {'A':{}, 'B':{}, 'C':{}}
for i, ds in enumerate(['ADNI_TEST', 'AIBL', 'FHS', 'NACC']):
    title = 'ADNI (TEST)' if ds == 'ADNI_TEST' else ds
    hdl_crv['A'][ds] = plot_curve(curve='roc', **roc_info['A'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':'//////', 'alpha':.4, 'line':'--', 'title':title})
    hdl_crv['B'][ds] = plot_curve(curve='roc', **roc_info['B'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':'....', 'alpha':.4, 'line':'-.', 'title':title})
    hdl_crv['C'][ds] = plot_curve(curve='roc', **roc_info['C'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':None, 'alpha':.2, 'line':'-', 'title':title})
hdl_neo = plot_neorologist(ax=axes['ADNI_TEST'], mode='roc', info=neo_info)
plot_legend(axes=axes, crv_lgd_hdl=hdl_crv, crv_info=roc_info, neo_lgd_hdl={'ADNI_TEST':hdl_neo})
  
# pr plot
fig, axes_ = plt.subplots(1, 4, figsize=[24, 6], dpi=100)
axes = dict(zip(['ADNI_TEST', 'AIBL', 'FHS', 'NACC'], axes_))
hdl_crv = {'A':{}, 'B':{}, 'C':{}}
for i, ds in enumerate(['ADNI_TEST', 'AIBL', 'FHS', 'NACC']):
    title = 'ADNI (TEST)' if ds == 'ADNI_TEST' else ds
    hdl_crv['A'][ds] = plot_curve(curve='pr', **pr_info['A'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':'//////', 'alpha':.4, 'line':'--', 'title':title})
    hdl_crv['B'][ds] = plot_curve(curve='pr', **pr_info['B'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':'....', 'alpha':.4, 'line':'-.', 'title':title})
    hdl_crv['C'][ds] = plot_curve(curve='pr', **pr_info['C'][ds], ax=axes[ds], **{'color':'C{}'.format(i), 'hatch':None, 'alpha':.2, 'line':'-', 'title':title})
hdl_neo = plot_neorologist(ax=axes['ADNI_TEST'], mode='pr', info=neo_info)
plot_legend(axes=axes, crv_lgd_hdl=hdl_crv, crv_info=pr_info, neo_lgd_hdl={'ADNI_TEST':hdl_neo})



