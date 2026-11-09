#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo biểu đồ cho báo cáo giữa kỳ A Rank-Based Backend Recommendation Tool.

Hai nguồn dữ liệu KHÁC NHAU:
  --reported  : dựng lại từ số liệu được ghi trong PDF báo cáo (KHÔNG tái tính).
  --from-csv  : dựng từ các CSV của lần chạy mới trên máy người dùng.

Dữ liệu chưa tồn tại => bỏ qua biểu đồ, không sinh dữ liệu giả.
"""
import argparse
import re
from pathlib import Path
import sys
import unicodedata

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def norm(text):
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def normcols(df):
    rename = {c: norm(c) for c in df.columns}
    return df.rename(columns=rename)


def column(df, *aliases):
    cs = set(df.columns)
    for al in aliases:
        if norm(al) in cs: return norm(al)
    # identify suffixes if CSV contains names such as avg_spearman_score
    for al in aliases:
        candidate = norm(al)
        matches = [c for c in df if c.endswith('_' + candidate)]
        if len(matches) == 1: return matches[0]
    return None


def try_read(path):
    if not path.is_file():
        print(f'[THIẾU FILE] {path}')
        return None
    try:
        data = pd.read_csv(path, encoding='utf-8-sig')
        if data.empty:
            print(f'[FILE RỖNG] {path}')
            return None
        print(f'[ĐÃ ĐỌC] {path} | {len(data)} dòng | Cột: {list(data.columns)}')
        return normcols(data)
    except Exception as e:
        print(f'[LỖI CSV] {path}: {e}')
        return None


def save(fig, dest):
    fig.tight_layout()
    fig.savefig(dest, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print(f'[TẠO HÌNH] {dest}')


def chart_reported(out):
    # DỮ LIỆU THAM CHIẾU ĐƯỢC CHÉP TỪ PDF, KHÔNG PHẢI LẦN CHẠY MỚI.
    models = ['Random (lý thuyết)', 'Heuristic', 'Model A', 'Model B', 'A+readout*']
    sp = np.array([0, .12, .16, .08, .58])
    top1 = np.array([.25, .50, .20, .20, .60])
    x = np.arange(len(models)); w=.35
    fig,ax = plt.subplots(figsize=(10.4,5.4))
    b1=ax.bar(x-w/2,sp,w,label='Spearman')
    b2=ax.bar(x+w/2,top1,w,label='Top-1 accuracy')
    for bars in (b1,b2):
        for bar in bars:
            ax.annotate(f'{bar.get_height():.2f}',(bar.get_x()+bar.get_width()/2,bar.get_height()),ha='center',va='bottom',fontsize=9)
    ax.set_xticks(x,models,rotation=15,ha='right'); ax.set_ylim(0,.76); ax.set_ylabel('Giá trị')
    ax.set_title('Đối chiếu điểm xếp hạng – số liệu báo cáo sơ bộ (10 mạch)')
    ax.legend(); ax.grid(axis='y',alpha=.2)
    fig.text(.01,.01,'*A+readout: thử nghiệm thăm dò 1 lần trên cùng tập đánh giá, không phải kiểm định độc lập.',fontsize=8)
    save(fig,out/'Hinh_02_doi_chieu_mo_hinh_SO_LIEU_BAO_CAO.png')

    names=['fake_athens','fake_lima','fake_belem','fake_manila']; fidelity=[.950,.946,.934,.929]
    fig,ax=plt.subplots(figsize=(8.6,4.7))
    bars=ax.bar(names,fidelity)
    ax.set_ylabel('Distribution fidelity trung bình'); ax.set_ylim(.88,.97)
    ax.set_title('Fidelity theo backend – giá trị tham chiếu từ báo cáo')
    ax.grid(axis='y',alpha=.2)
    for bar in bars:
        ax.annotate(f'{bar.get_height():.3f}',(bar.get_x()+bar.get_width()/2,bar.get_height()),ha='center',va='bottom')
    save(fig,out/'Hinh_01_fidelity_SO_LIEU_BAO_CAO.png')

    labels=['Spearman','Top-1','Precision@2']; before=[.16,.20,.60]; after=[.58,.60,.85]
    fig,ax=plt.subplots(figsize=(8.6,4.6))
    x=np.arange(3); w=.36
    ax.bar(x-w/2,before,w,label='Model A hiện tại')
    ax.bar(x+w/2,after,w,label='Model A + readout (thăm dò)')
    ax.set_xticks(x,labels);ax.set_ylim(0,1.0);ax.set_ylabel('Giá trị')
    ax.legend(loc='upper left');ax.grid(axis='y',alpha=.2)
    ax.set_title('Readout ablation – số liệu thăm dò, chưa tái lập độc lập')
    save(fig,out/'Hinh_03_readout_THAM_DO_SO_LIEU_BAO_CAO.png')


def chart_gt(repo,out):
    candidates=[repo/'mywork/data/results/ground_truth.csv',repo/'mywork/data/results/noise_simulation_summary.csv']
    df=None; path=None; fields=None
    for candidate in candidates:
        d=try_read(candidate)
        if d is None: continue
        cir=column(d,'circuit','circuit_name','circuit_id','name_circuit')
        back=column(d,'backend','backend_name','fake_backend')
        fid=column(d,'fidelity','mean_fidelity','fidelity_mean','distribution_fidelity','avg_fidelity','mean_distribution_fidelity')
        if cir and back and fid:
            df=d;path=candidate; fields=(cir,back,fid);break
        print('[CHƯA ĐỦ CỘT] Cần ba cột: circuit, backend, fidelity hoặc các tên tương đương.')
    if df is None: return
    cir,back,fid=fields
    work=df[[cir,back,fid]].copy()
    work[fid]=pd.to_numeric(work[fid],errors='coerce')
    work=work.dropna(subset=[cir,back,fid]);work[back]=work[back].astype(str)
    if work.empty:
        print('[BỎ QUA] Không có dòng fidelity hợp lệ trong CSV');return
    # Có thể có 3 seed cho mỗi cặp, phải lấy mean thay vì lặp trên heatmap.
    frame=work.groupby([cir,back],as_index=False)[fid].mean()
    ranking=frame.groupby(back)[fid].mean().sort_values(ascending=False)
    fig,ax=plt.subplots(figsize=(8.8,5.0));bars=ax.bar(ranking.index,ranking.values)
    ax.set_ylabel('Mean distribution fidelity');ax.set_ylim(max(0,float(ranking.min())-.07),min(1.01,float(ranking.max())+.035))
    ax.set_title(f'Fidelity theo backend – tính từ {path.name}')
    ax.grid(axis='y',alpha=.2)
    for bar in bars:
        ax.annotate(f'{bar.get_height():.3f}',(bar.get_x()+bar.get_width()/2,bar.get_height()),ha='center',va='bottom')
    save(fig,out/'Hinh_01_fidelity_TINH_TU_CSV.png')

    if frame[cir].nunique()>1 and frame[back].nunique()>1:
        matrix=frame.pivot(index=cir,columns=back,values=fid)
        fig,ax=plt.subplots(figsize=(8.8,max(4.9,.35*len(matrix)+1.4)))
        im=ax.imshow(matrix.to_numpy(),aspect='auto',cmap='viridis',vmin=0,vmax=1)
        ax.set_yticks(np.arange(len(matrix)),matrix.index,fontsize=9)
        ax.set_xticks(np.arange(len(matrix.columns)),matrix.columns,rotation=25,ha='right',fontsize=9)
        ax.set_title('Fidelity theo mạch và backend – dữ liệu thực nghiệm')
        fig.colorbar(im,ax=ax,label='Fidelity')
        save(fig,out/'Hinh_04_heatmap_fidelity_TINH_TU_CSV.png')


def chart_metrics(repo,out):
    f=repo/'mywork/data/results/ranking_metrics_summary.csv';d=try_read(f)
    if d is None:return
    model=column(d,'model','method','predictor','baseline','algorithm','model_name')
    spearman=column(d,'spearman','mean_spearman','spearman_mean','spearman_rho','avg_spearman')
    top1=column(d,'top1','top_1','top1_accuracy','top_1_accuracy','top1_acc','mean_top1','top_1_hit')
    if not model or not (spearman or top1):
        print('[CHƯA ĐỦ CỘT] Cần tên model và ít nhất 1 metric Spearman/top1 trong ranking_metrics_summary.csv.')
        print(' Cột hiện có:',list(d.columns));return
    for c in [spearman,top1]:
        if c:d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=[model]); d[model]=d[model].astype(str)
    records=d.groupby(model,as_index=False)[[c for c in (spearman,top1) if c]].mean().dropna(how='all',subset=[c for c in (spearman,top1) if c])
    if records.empty:return
    x=np.arange(len(records));fig,ax=plt.subplots(figsize=(max(8,len(records)*1.45),5))
    if spearman and top1:
        w=.35;ax.bar(x-w/2,records[spearman],w,label='Spearman');ax.bar(x+w/2,records[top1],w,label='Top-1 accuracy');ax.legend()
    elif spearman:ax.bar(x,records[spearman],.55,label='Spearman')
    else:ax.bar(x,records[top1],.55,label='Top-1 accuracy')
    ax.set_xticks(x,records[model],rotation=20,ha='right');ax.set_ylim(0,max(1.,float(records[[c for c in (spearman,top1) if c]].max().max())+.1))
    ax.set_ylabel('Giá trị');ax.set_title('Chỉ số xếp hạng – tính từ ranking_metrics_summary.csv');ax.grid(axis='y',alpha=.2)
    save(fig,out/'Hinh_02_so_sanh_mo_hinh_TINH_TU_CSV.png')


def simple_experiment_csv(repo,out):
    specs=[
      ('sensitivity_results.csv', ['noise_type','multiplier','spearman','top1'], 'Hinh_05_do_nhay_cam', 'Khảo sát độ nhạy theo hệ số nhiễu', 'multiplier', 'spearman'),
      ('scaling_results.csv', ['num_qubits','runtime_seconds','peak_ram_mb'], 'Hinh_06_mo_phong_quy_mo', 'Thời gian mô phỏng theo số qubit','num_qubits','runtime_seconds'),
      ('hardware_validation.csv', ['circuit','backend','simulation_fidelity','hardware_fidelity'], 'Hinh_07_doi_chieu_thiet_bi', 'Mô phỏng so với phần cứng thật', 'simulation_fidelity','hardware_fidelity')]
    for file,fields,stem,title,x_col,y_col in specs:
        path=repo/file;d=try_read(path)
        if d is None:continue
        if not all(f in d.columns for f in fields):
            print(f'[CHƯA ĐỦ CỘT] {file} yêu cầu {fields}');continue
        d[x_col]=pd.to_numeric(d[x_col],errors='coerce');d[y_col]=pd.to_numeric(d[y_col],errors='coerce')
        d=d.dropna(subset=[x_col,y_col])
        if d.empty:continue
        fig,ax=plt.subplots(figsize=(8.5,5.2))
        if file=='sensitivity_results.csv':
            for noise,g in d.groupby('noise_type'):
                avg=g.groupby(x_col,as_index=False)[y_col].mean().sort_values(x_col)
                ax.plot(avg[x_col],avg[y_col],marker='o',label=str(noise))
            ax.legend(title='Loại nhiễu'); ax.set_ylabel('Spearman trung bình');ax.set_xlabel('Hệ số nhân sai số')
        elif file=='scaling_results.csv':
            avg=d.groupby(x_col,as_index=False)[y_col].mean().sort_values(x_col)
            ax.plot(avg[x_col],avg[y_col],marker='o');ax.set_xlabel('Số qubit');ax.set_ylabel('Thời gian mô phỏng (giây)')
        else:
            ax.scatter(d[x_col],d[y_col],alpha=.75)
            ax.plot([0,1],[0,1],linestyle='--',alpha=.5);ax.set_xlim(0,1);ax.set_ylim(0,1)
            ax.set_xlabel('Fidelity từ mô phỏng');ax.set_ylabel('Fidelity từ phần cứng thật')
        ax.set_title(title+' – dữ liệu thí nghiệm được cung cấp');ax.grid(alpha=.2)
        save(fig,out/(stem+'_TU_DU_LIEU_MOI.png'))


def main():
    parser=argparse.ArgumentParser(description='Vẽ biểu đồ từ báo cáo hoặc từ CSV trên máy thật (không suy diễn dữ liệu)')
    parser.add_argument('--repo',default='.',help='Thư mục gốc repository chứa mywork/')
    parser.add_argument('--out',default='figures',help='Thư mục lưu PNG')
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--reported',action='store_true',help='Dựng từ số liệu đã có trong PDF (chỉ tham khảo)')
    g.add_argument('--from-csv',action='store_true',help='Đọc CSV thực tế, không tạo số liệu giả')
    args=parser.parse_args();repo=Path(args.repo).expanduser().resolve();out=Path(args.out).expanduser().resolve();out.mkdir(parents=True,exist_ok=True)
    print('Root:',repo,'\nOutput:',out)
    if args.reported:chart_reported(out)
    else:
        chart_gt(repo,out)
        chart_metrics(repo,out)
        simple_experiment_csv(repo,out)
    print('Hoàn tất. Chỉ chèn hình có nguồn dữ liệu và nhãn trạng thái phù hợp.')

if __name__=='__main__':main()
