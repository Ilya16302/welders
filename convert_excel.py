#!/usr/bin/env python3
"""
Convert Excel file to JSON database for the welder statistics website.
Run this script whenever you update the Excel file.
Usage: python convert_excel.py <path_to_xlsm>
"""

import sys
import json
import pandas as pd
from datetime import datetime, date
import os

import re

def safe_str(val):
    if pd.isna(val) or val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%d.%m.%Y")
    return str(val).strip()

def clean_result(val):
    """Extract result keyword from strings like '(28.04.2026) Годен' """
    s = safe_str(val)
    if not s:
        return ""
    # Remove leading date in parentheses: (dd.mm.yyyy)
    s = re.sub(r'^\(\d{2}\.\d{2}\.\d{4}\)\s*', '', s).strip()
    sl = s.lower()
    if 'годен' in sl and 'не' not in sl:
        return 'Годен'
    if 'не годен' in sl or 'негоден' in sl:
        return 'Не годен'
    if 'вырез' in sl or 'врез' in sl:
        return 'Вырез'
    return s

def safe_float(val):
    try:
        if pd.isna(val):
            return None
        return float(val)
    except:
        return None

def safe_int(val):
    try:
        if pd.isna(val):
            return None
        return int(val)
    except:
        return None

def convert(excel_path, output_path=None):
    if output_path is None:
        output_path = os.path.join(os.path.dirname(excel_path), "data", "db.json")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Reading {excel_path}...")
    
    # ── Лист «Сварщики» ──────────────────────────────────────────────
    df_sw = pd.read_excel(excel_path, sheet_name="Сварщики", engine="openpyxl", header=None)
    
    welders_list = []
    header_row = None
    for i, row in df_sw.iterrows():
        vals = [safe_str(v) for v in row]
        if "ФИО" in vals:
            header_row = i
            break
    
    if header_row is not None:
        for i, row in df_sw.iterrows():
            if i <= header_row:
                continue
            fio = safe_str(row.iloc[5] if len(row) > 5 else "")
            if not fio:
                continue
            welders_list.append({
                "num": safe_str(row.iloc[0]),
                "subdivision": safe_str(row.iloc[1]),
                "project": safe_str(row.iloc[2]),
                "org": safe_str(row.iloc[3]),
                "citizenship": safe_str(row.iloc[4]),
                "fio": fio,
                "stamp": safe_str(row.iloc[6] if len(row) > 6 else ""),
                "qualification": safe_str(row.iloc[7] if len(row) > 7 else ""),
            })
    
    # ── Лист «Полная статистика» ─────────────────────────────────────
    df_stat = pd.read_excel(excel_path, sheet_name="Полная статистика", engine="openpyxl", header=None)
    
    # Find header row (contains "ФИО")
    stat_header = None
    for i, row in df_stat.iterrows():
        vals = [safe_str(v) for v in row]
        if "ФИО" in vals:
            stat_header = i
            break
    
    # Date period from row 2
    period_start = ""
    period_end = ""
    for i, row in df_stat.iterrows():
        if i == 2:
            # Columns 19 and 20 (0-indexed)
            try:
                ps = row.iloc[19] if len(row) > 19 else None
                pe = row.iloc[20] if len(row) > 20 else None
                period_start = safe_str(ps)
                period_end = safe_str(pe)
            except:
                pass
    
    stats_by_fio = {}
    if stat_header is not None:
        for i, row in df_stat.iterrows():
            if i <= stat_header:
                continue
            fio = safe_str(row.iloc[6] if len(row) > 6 else "")
            if not fio:
                continue
            stats_by_fio[fio] = {
                "fio": fio,
                "stamp": safe_str(row.iloc[7] if len(row) > 7 else ""),
                "status": safe_str(row.iloc[8] if len(row) > 8 else ""),
                "org": safe_str(row.iloc[9] if len(row) > 9 else ""),
                "total": safe_int(row.iloc[10] if len(row) > 10 else None),
                "good": safe_int(row.iloc[11] if len(row) > 11 else None),
                "bad": safe_int(row.iloc[12] if len(row) > 12 else None),
                "pct_bad": safe_float(row.iloc[13] if len(row) > 13 else None),
                "total_period": safe_int(row.iloc[14] if len(row) > 14 else None),
                "good_period": safe_int(row.iloc[15] if len(row) > 15 else None),
                "bad_period": safe_int(row.iloc[16] if len(row) > 16 else None),
                "pct_bad_period": safe_float(row.iloc[17] if len(row) > 17 else None),
            }
    
    # ── Лист «Подробнее» ─────────────────────────────────────────────
    df_det = pd.read_excel(excel_path, sheet_name="Подробнее", engine="openpyxl", header=None)
    
    # Find header row: contains "Материал" and "Стык" (col A is empty!)
    det_header_row = None
    for i, row in df_det.iterrows():
        vals = [safe_str(v) for v in row]
        if "Материал" in vals and "Стык" in vals:
            det_header_row = i
            break
    
    # If not found by content, assume row index 2 (3rd row in Excel = row 3)
    if det_header_row is None:
        det_header_row = 2
    
    print(f"  Header row index: {det_header_row}")
    
    joints = []
    if det_header_row is not None:
        # Skip header row AND filter row (det_header_row + 1 is usually filter dropdowns)
        data_start = det_header_row + 2  # skip header + filter row
        
        for i, row in df_det.iterrows():
            if i < data_start:
                continue
            
            # Col A (idx 0) is empty/row number, data starts at col B (idx 1)
            # B=Материал, C=№Заявки, D=R/RW, E=Линия, F=Изо, G=Стык,
            # H=Типоразмер, I=Зона, J=Результат контроля, K=Примечание
            # L+ = история (группы по 3)
            
            material = safe_str(row.iloc[1])
            request_num = safe_str(row.iloc[2])
            
            # Skip empty rows
            if not material and not request_num:
                continue
            
            joint = {
                "num": safe_str(row.iloc[0]) or str(i),
                "material": material,
                "request_num": request_num,
                "rw": safe_str(row.iloc[3]),
                "line": safe_str(row.iloc[4]),
                "iso": safe_str(row.iloc[5]),
                "joint_id": safe_str(row.iloc[6]),
                "size": safe_str(row.iloc[7]),
                "zone": safe_str(row.iloc[8]),
                "control_result": safe_str(row.iloc[9]),
                "note": safe_str(row.iloc[10]),
                "history": []
            }
            
            # History: starting from column L (index 11), groups of 3
            col = 11
            labels = ["первичка"] + [f"ремонт {k}" for k in range(1, 25)]
            label_idx = 0
            while col + 2 < len(row):
                dt = safe_str(row.iloc[col])
                welder = safe_str(row.iloc[col + 1])
                result = safe_str(row.iloc[col + 2])
                result_clean = clean_result(row.iloc[col + 2])
                if dt or welder or result_clean:
                    joint["history"].append({
                        "label": labels[label_idx] if label_idx < len(labels) else f"этап {label_idx}",
                        "date": dt,
                        "welder": welder,
                        "result": result_clean,
                        "result_raw": result,
                    })
                col += 3
                label_idx += 1
            
            joints.append(joint)
    
    # ── Merge welders with stats ─────────────────────────────────────
    # If Сварщики is empty, build list from stats
    if not welders_list and stats_by_fio:
        for fio, stat in stats_by_fio.items():
            welders_list.append({
                "fio": fio,
                "stamp": stat.get("stamp", ""),
                "org": stat.get("org", ""),
                "num": "",
                "subdivision": "",
                "project": "",
                "citizenship": "",
                "qualification": "",
            })
    
    # Also add welders found only in joints but not in stats
    all_fio_in_joints = set()
    for j in joints:
        for h in j["history"]:
            if h["welder"]:
                all_fio_in_joints.add(h["welder"])
    
    known_fio = {w["fio"] for w in welders_list}
    for fio in sorted(all_fio_in_joints):
        if fio not in known_fio:
            welders_list.append({"fio": fio, "stamp": "", "org": "", "num": "", "subdivision": "", "project": "", "citizenship": "", "qualification": ""})
    
    db = {
        "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "period_start": period_start,
        "period_end": period_end,
        "welders": welders_list,
        "stats": stats_by_fio,
        "joints": joints,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Done!")
    print(f"   Welders: {len(welders_list)}")
    print(f"   Joints:  {len(joints)}")
    print(f"   Output:  {output_path}")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_excel.py <path_to_xlsm> [output_json]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    convert(sys.argv[1], out)
