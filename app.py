import streamlit as st
import pandas as pd
import io
import itertools
from collections import Counter
import re

# --- Streamlit Page Config ---
st.set_page_config(page_title="2D SUPER VIP", page_icon="🛡️", layout="wide")

# --- 1. Configurations & Dictionaries ---
MIN_STREAK = 3    
all_combos = list(itertools.combinations(range(20), 3))
target_types = ["ထိပ်", "ပိတ်", "ဘရိတ်"]

power_dict = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
natkhat_dict = {0: 7, 7: 0, 1: 8, 8: 1, 2: 4, 4: 2, 3: 5, 5: 3, 6: 9, 9: 6}
special_groups = {
    "ညီကို": {"01","10","12","21","23","32","34","43","45","54","56","65","67","76","78","87","89","98","90","09"},
    "ပါဝါ": {"05","50","16","61","27","72","38","83","49","94"},
    "နက္ခတ်": {"07","70","18","81","24","42","35","53","69","96"},
    "ထိုင်းပါဝါ": {"09","90","13","31","26","62","47","74","58","85"},
    "အပူး": {"00","11","22","33","44","55","66","77","88","99"}
}

GLOBAL_TFS = [("၁ ပွဲ", 1, 1), ("၂ ပွဲ", 1, 2), ("၃ ပွဲ", 1, 3), ("၄ ပွဲ", 1, 4), ("၅ ပွဲ", 1, 5), ("၈ ပွဲ", 1, 8), ("၁၀ ပွဲ", 1, 10)]

# --- 2. Password Protection ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.write("### 🛡️ 2D SUPER VIP မှ ကြိုဆိုပါတယ်")
        pwd = st.text_input("Password ရိုက်ထည့်ပါ -", type="password")
        if st.button("ဝင်မည်"):
            if pwd == "v27admin":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password မှားယွင်းနေပါသည်။")
        return False
    return True

# --- 3. UI Helpers ---
def format_combos(combo_list, super_key):
    if not combo_list: return "မရှိပါ"
    res = []
    for c in combo_list:
        if int(c[0]) in super_key or int(c[1]) in super_key:
            res.append(f"<span style='color:#ff4b4b; font-size:1.6em; margin-right:15px;'>{c}</span>")
        else:
            res.append(f"<span style='font-size:1.6em; margin-right:15px;'>{c}</span>")
    return f"<div>{''.join(res)}</div>"

# --- 4. CORE ENGINE: Gap System ---
def get_target_val(draw, t_type, time_slot):
    if time_slot == "AM":
        if t_type == "ထိပ်": return draw[0]
        elif t_type == "ပိတ်": return draw[1]
        elif t_type == "ဘရိတ်": return (draw[0] + draw[1]) % 10 if draw[0] is not None else None
    else:
        if t_type == "ထိပ်": return draw[2]
        elif t_type == "ပိတ်": return draw[3]
        elif t_type == "ဘရိတ်": return (draw[2] + draw[3]) % 10 if draw[2] is not None else None
    return None

@st.cache_data(show_spinner=False)
def calculate_prediction(target_idx, slot, daily_draws, skip_sizes):
    daily_hists = {}
    targets = {}
    for t_idx in range(5, target_idx + 1):
        start_idx = t_idx - 5
        hist_raw = daily_draws[start_idx : t_idx]
        flat_hist = [val for day in hist_raw for val in day if val is not None]
        if len(flat_hist) == 20: daily_hists[t_idx] = flat_hist
        if t_idx < len(daily_draws):
            targets[t_idx] = {t: get_target_val(daily_draws[t_idx], t, slot) for t in target_types}

    top_results = {"ထိပ်": [], "ပိတ်": [], "ဘရိတ်": []}
    if target_idx not in daily_hists: return top_results
    current_hist = daily_hists[target_idx]

    for t_type in target_types:
        votes = {}
        for skip in skip_sizes:
            step = skip + 1 
            if target_idx - (MIN_STREAK * step) - 6 < 0: continue
            
            root_groups = {}
            for root_combo in all_combos:
                root_seq = []
                valid_root = True
                for g in range(1, MIN_STREAK + 1):
                    t_idx_temp = target_idx - (g * step)
                    if t_idx_temp not in daily_hists: valid_root = False; break
                    root_seq.append(sum(daily_hists[t_idx_temp][i] for i in root_combo) % 10)
                if valid_root: root_groups.setdefault(tuple(root_seq), []).append(root_combo)

            matches = []
            for combo in all_combos:
                valid = True
                required_seq = []
                for g in range(1, MIN_STREAK + 1):
                    t_idx_temp = target_idx - (g * step)
                    if t_idx_temp not in targets: valid = False; break
                    target_val = targets[t_idx_temp][t_type]
                    if target_val is None: valid = False; break
                    current_sum = (sum(daily_hists[t_idx_temp][i] for i in combo) + target_val) % 10
                    required_seq.append(current_sum)
                
                if valid:
                    req_seq_tuple = tuple(required_seq)
                    if req_seq_tuple in root_groups:
                        for root_combo in root_groups[req_seq_tuple]:
                            root_0 = sum(current_hist[i] for i in root_combo) % 10
                            pred = (root_0 - sum(current_hist[i] for i in combo)) % 10
                            matches.append({'pred': pred, 'root_seq': req_seq_tuple})

            df_matches = pd.DataFrame(matches)
            if not df_matches.empty:
                g_counts = df_matches.groupby(['pred', 'root_seq']).size().reset_index(name='f_count')
                valid_groups = g_counts[g_counts['f_count'] >= 3] 
                s_counts = valid_groups.groupby('pred').size().reset_index(name='g_count')
                valid_preds = s_counts[s_counts['g_count'] >= 2] 
                for _, row in valid_preds.iterrows(): votes[row['pred']] = row['g_count']
        if votes:
            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            top_results[t_type] = [k for k, v in sorted_votes] 
    return top_results

def get_gap_5x5_super_key(d, draw_time, daily_draws, window_size=300):
    if d < 10 or d >= len(daily_draws): return None, []
    col_h, col_t = (0, 1) if draw_time == "AM" else (2, 3)
    full_history = []
    for past_d in range(d + 1):
        if daily_draws[past_d][0] is not None and daily_draws[past_d][1] is not None:
            if past_d == d and draw_time == "AM": pass 
            else: full_history.append((daily_draws[past_d][0], daily_draws[past_d][1]))
        if daily_draws[past_d][2] is not None and daily_draws[past_d][3] is not None:
            if past_d == d and draw_time == "PM": pass 
            else: full_history.append((daily_draws[past_d][2], daily_draws[past_d][3]))

    if len(full_history) < 2: return None, []
    last_draw = full_history[-1]
    scores = {i: 0.0 for i in range(10)}

    gap_heads, gap_tails = [], []
    for gap in [3, 4, 5]:
        preds = calculate_prediction(d, draw_time, daily_draws, [gap])
        if preds["ထိပ်"]: gap_heads.extend(preds["ထိပ်"])
        if preds["ပိတ်"]: gap_tails.extend(preds["ပိတ်"])
        
    for h, count in Counter(gap_heads).items(): scores[h] += (count * 3.0)
    for t, count in Counter(gap_tails).items(): scores[t] += (count * 3.0)

    recent_history = full_history[-window_size:] if len(full_history) > window_size else full_history
    trans_freq = {i: 0 for i in range(10)}
    for idx in range(len(recent_history) - 1):
        curr, nxt = recent_history[idx], recent_history[idx + 1]
        if curr[0] == last_draw[0]: trans_freq[nxt[0]] += 1
        if curr[1] == last_draw[1]: trans_freq[nxt[1]] += 1
    
    for idx, (digit, _) in enumerate(Counter(trans_freq).most_common()):
        if idx < 3: scores[digit] += 2.0
        elif idx < 6: scores[digit] += 1.0

    recent_heat = {i: 0.0 for i in range(10)}
    for i, p_d in enumerate(full_history[-10:]):
        weight = (i + 1) * 0.5 
        recent_heat[p_d[0]] += weight
        recent_heat[p_d[1]] += weight
        
    for idx, digit in enumerate(sorted(recent_heat.keys(), key=lambda x: recent_heat[x], reverse=True)):
        if idx < 3: scores[digit] += 2.0
        elif idx < 6: scores[digit] += 1.0

    scores[power_dict[last_draw[0]]] += 1.0; scores[power_dict[last_draw[1]]] += 1.0
    scores[natkhat_dict[last_draw[0]]] += 1.0; scores[natkhat_dict[last_draw[1]]] += 1.0

    top_3_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)[:3]
    return top_3_keys, full_history

# --- 5. CORE ENGINE: Hybrid 5x5 Gatekeeper (Upgraded) ---
def get_hybrid_5x5_trend(full_h, gap_signals=None):
    if not full_h: return [0,1,2,3,4], [0,1,2,3,4], [0,1,2,3,4]
    last = full_h[-1]
    
    h_scores = {i: 0.0 for i in range(10)}; t_scores = {i: 0.0 for i in range(10)}; b_scores = {i: 0.0 for i in range(10)}

    for idx in range(len(full_h)-1):
        curr, nxt = full_h[idx], full_h[idx+1]
        if curr[0] == last[0]: h_scores[nxt[0]] += 1.5
        if curr[1] == last[1]: t_scores[nxt[1]] += 1.5

    for i, p in enumerate(full_h[-15:]):
        weight = (i+1) * 0.8
        h_scores[p[0]] += weight; t_scores[p[1]] += weight; b_scores[(p[0]+p[1])%10] += weight

    if gap_signals:
        for val in gap_signals.get('h', []): h_scores[val] += 5.0
        for val in gap_signals.get('t', []): t_scores[val] += 5.0

    h_scores[power_dict[last[0]]] += 2.0; h_scores[natkhat_dict[last[0]]] += 2.0
    t_scores[power_dict[last[1]]] += 2.0; t_scores[natkhat_dict[last[1]]] += 2.0

    top_h = sorted(h_scores.keys(), key=lambda x: h_scores[x], reverse=True)[:5]
    top_t = sorted(t_scores.keys(), key=lambda x: t_scores[x], reverse=True)[:5]
    top_b = sorted(b_scores.keys(), key=lambda x: b_scores[x], reverse=True)[:5]
    return top_h, top_t, top_b

def gatekeeper_replace(gap_list, trend_list):
    clean_list = []
    for g in gap_list:
        if g in trend_list: clean_list.append(g)
        else:
            for t in trend_list:
                if t not in clean_list:
                    clean_list.append(t); break
    return clean_list

# --- 6. CORE ENGINE: V26 Data Analysis (Mode 1 & Mode 4) ---
def build_v26_universe(daily_draws, raw_df):
    f_draws = []
    day_col = None
    for col in raw_df.columns:
        if col.lower() in ['day', 'date', 'days', 'ရက်']: day_col = col; break
    
    for i, d in enumerate(daily_draws):
        day_str = str(raw_df.iloc[i][day_col]).strip()[:3].title() if day_col and i < len(raw_df) and pd.notna(raw_df.iloc[i][day_col]) else "Mon"
        if d[0] is not None: f_draws.append({'draw': f"{d[0]}{d[1]}", 'time': 'AM', 'day': day_str, 'index': len(f_draws)})
        if d[2] is not None: f_draws.append({'draw': f"{d[2]}{d[3]}", 'time': 'PM', 'day': day_str, 'index': len(f_draws)})
    return f_draws

@st.cache_data(show_spinner=False)
def analyze_history_v26(target_2d, f_draws, scope_min=20, scope_max=40, time_frame=20):
    hits = [d for d in f_draws if d['draw'] == target_2d]
    if len(hits) < scope_min: return None
    
    best_pattern = None
    for scope in range(scope_min, min(len(hits), scope_max) + 1):
        scope_hits = hits[-scope:]
        ev_subs = []
        for hit in scope_hits:
            s_idx, e_idx = hit['index']+1, min(hit['index']+time_frame+1, len(f_draws))
            ev_subs.append([d['draw'] for d in f_draws[s_idx:e_idx]] if s_idx < len(f_draws) else [])
        
        if not any(ev_subs): continue
        all_flat = list(itertools.chain(*[ev for ev in ev_subs if ev]))
        if not all_flat: continue
        
        # 1. လုံးဘိုင် Check
        top_digits = [x[0] for x in Counter(itertools.chain(*[list(d) for d in all_flat])).most_common(3)]
        for digit in top_digits:
            success_count = sum(1 for ev in ev_subs if any(digit in d for d in ev))
            rate = (success_count / len(ev_subs)) * 100
            if rate >= 95.0:
                is_comeback = False
                if len(ev_subs) >= 3:
                    res_list = [any(digit in d for d in ev) for ev in ev_subs]
                    if not res_list[-2] and res_list[-1]: is_comeback = True
                
                if best_pattern is None or rate > best_pattern['rate']:
                    best_pattern = {
                        'type': 'လုံးဘိုင်', 'val': digit, 'rate': rate, 
                        'hits': f"{success_count}/{len(ev_subs)}", 'scope': scope,
                        'comeback': is_comeback
                    }
                    
        # 2. ဘရိတ် Check
        top_breaks = [x[0] for x in Counter([str((int(d[0])+int(d[1]))%10) for d in all_flat]).most_common(2)]
        for brk in top_breaks:
            success_count = sum(1 for ev in ev_subs if any(str((int(d[0])+int(d[1]))%10) == brk for d in ev))
            rate = (success_count / len(ev_subs)) * 100
            if rate >= 95.0:
                if best_pattern is None or rate > best_pattern['rate']:
                    best_pattern = {'type': 'ဘရိတ်', 'val': brk, 'rate': rate, 'hits': f"{success_count}/{len(ev_subs)}", 'scope': scope, 'comeback': False}
                    
    return best_pattern

@st.cache_data(show_spinner=False)
def run_mode4_alerts(f_draws):
    if len(f_draws) < 20: return []
    history = f_draws[-20:]
    alerts = []
    
    for tf_name, s_off, e_off in GLOBAL_TFS:
        ev_subs = []
        for hit in history:
            s_idx = hit['index'] + s_off
            e_idx = min(hit['index'] + e_off + 1, len(f_draws))
            ev_subs.append([d['draw'] for d in f_draws[s_idx:e_idx]] if s_idx < len(f_draws) else [])
            
        if all(len(ev)==0 for ev in ev_subs): continue
        all_n = list(itertools.chain(*[ev for ev in ev_subs if ev]))
        if not all_n: continue
        
        top_singles = [x[0] for x in Counter(itertools.chain(*[list(d) for d in all_n])).most_common(3)]
        b1 = top_singles[0] if top_singles else ""
        brk2 = [x[0] for x in Counter([str((int(d[0])+int(d[1]))%10) for d in all_n]).most_common(2)]
        
        curr_passed = 0 
        rem = e_off - curr_passed
        
        if rem == 1:
            # လုံးဘိုင် Check
            if b1:
                hit_res = [any(b1 in d for d in ev) for ev in ev_subs if ev]
                if hit_res and sum(hit_res)/len(hit_res) >= 0.95:
                    alerts.append({"Type": "လုံးဘိုင်", "Value": b1, "TF": tf_name, "Rate": (sum(hit_res)/len(hit_res))*100})
            
            # ဘရိတ် Check
            if brk2:
                brk_str = ", ".join(brk2)
                hit_res = [any(str((int(d[0])+int(d[1]))%10) in brk2 for d in ev) for ev in ev_subs if ev]
                if hit_res and sum(hit_res)/len(hit_res) >= 0.95:
                    alerts.append({"Type": "ဘရိတ်", "Value": brk_str, "TF": tf_name, "Rate": (sum(hit_res)/len(hit_res))*100})
                    
            # အုပ်စု Check
            best_g = ""; best_g_c = 0
            for g, g_set in special_groups.items():
                c = sum(1 for ev in ev_subs if ev and any(d in g_set for d in ev))
                if c > best_g_c: best_g_c = c; best_g = g
            if best_g and len(ev_subs) > 0 and (best_g_c/len(ev_subs)) >= 0.95:
                 alerts.append({"Type": "အုပ်စု", "Value": best_g, "TF": tf_name, "Rate": (best_g_c/len(ev_subs))*100})
                 
    return alerts

# --- 7. Main Web App Layout ---
if check_password():
    if "data_loaded" not in st.session_state: st.session_state["data_loaded"] = False

    if not st.session_state["data_loaded"]:
        st.sidebar.header("📂 Excel Data တင်ရန်")
        uploaded_file = st.sidebar.file_uploader("မှတ်တမ်းဖိုင် တင်ပါ", type=['csv', 'xlsx'])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
            else: df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            for col in ['am1', 'am2', 'pm1', 'pm2']:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['am1', 'am2']).reset_index(drop=True)
            
            daily_draws = []
            for index, row in df.iterrows():
                am_v = pd.notna(row['am1']) and pd.notna(row['am2'])
                pm_v = 'pm1' in df.columns and 'pm2' in df.columns and pd.notna(row['pm1']) and pd.notna(row['pm2'])
                if am_v and pm_v: daily_draws.append([int(row['am1']), int(row['am2']), int(row['pm1']), int(row['pm2'])])
                elif am_v and not pm_v: daily_draws.append([int(row['am1']), int(row['am2']), None, None])
            
            st.session_state["raw_df"] = df
            st.session_state["daily_draws"] = daily_draws
            st.session_state["data_loaded"] = True
            st.rerun()
    else:
        st.sidebar.header("📝 ယနေ့ဂဏန်း ထည့်ရန်")
        new_am = st.sidebar.text_input("AM ထွက်ဂဏန်း (ဥပမာ - 15)", max_chars=2)
        new_pm = st.sidebar.text_input("PM ထွက်ဂဏန်း (ဥပမာ - 03)", max_chars=2)
        if st.sidebar.button("Data Update လုပ်မည်", type="primary"):
            current_draws = st.session_state["daily_draws"]
            if new_am and len(new_am) == 2:
                if current_draws[-1][2] is not None: current_draws.append([int(new_am[0]), int(new_am[1]), None, None])
                else: current_draws[-1][0], current_draws[-1][1] = int(new_am[0]), int(new_am[1])
            if new_pm and len(new_pm) == 2:
                if current_draws[-1][2] is None: current_draws[-1][2], current_draws[-1][3] = int(new_pm[0]), int(new_pm[1])
                else: st.sidebar.error("ယနေ့အတွက် PM ဂဏန်း ရှိပြီးသားဖြစ်ပါသည်။")
            st.session_state["daily_draws"] = current_draws; st.rerun()
        if st.sidebar.button("Data ဖိုင် အသစ်ပြန်တင်မည်", type="secondary"):
            st.session_state["data_loaded"] = False; st.rerun()

    if st.session_state["data_loaded"]:
        daily_draws = st.session_state["daily_draws"]
        raw_df = st.session_state["raw_df"]
        f_draws = build_v26_universe(daily_draws, raw_df)
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["မူလစနစ်", "Stock Market စနစ်", "2d history", "ရက်ချိန်းပြည့်မူများ", "2D Calendar"])

        # ==========================================
        # TAB 1: မူလစနစ် (VIP 12 ကွက်)
        # ==========================================
        with tab1:
            st.subheader("AM/PM (ပင်ခြားစနစ်)")
            if st.button("တွက်ချက်မည်", type="primary", key="btn_tab1"):
                with st.spinner("ပင်ခြားစနစ်နှင့် Trend များကို တိုက်စစ်နေပါသည်..."):
                    calc_draws = daily_draws.copy()
                    last_row = calc_draws[-1]
                    predict_slots = []
                    
                    if last_row[2] is None: predict_slots.append(("PM", len(calc_draws) - 1))
                    else:
                        calc_draws.append([None, None, None, None])
                        predict_slots.append(("AM", len(calc_draws) - 1))
                        predict_slots.append(("PM", len(calc_draws) - 1))
                        
                    cols = st.columns(len(predict_slots))
                    for i, (slot, t_idx) in enumerate(predict_slots):
                        super_key, full_hist = get_gap_5x5_super_key(t_idx, slot, calc_draws)
                        if super_key is None: continue
                        trend_h, trend_t, trend_b = get_hybrid_5x5_trend(full_hist)
                        
                        all_12 = []; vip_list = []; super_vip = []; rest_list = []
                        
                        for gap in [3, 4, 5]:
                            preds = calculate_prediction(t_idx, slot, calc_draws, [gap])
                            g_h = preds["ထိပ်"][:2] if preds["ထိပ်"] else trend_h[:2]
                            g_t = preds["ပိတ်"][:2] if preds["ပိတ်"] else trend_t[:2]
                            c_h = gatekeeper_replace(g_h, trend_h)[:2]
                            c_t = gatekeeper_replace(g_t, trend_t)[:2]
                            
                            for h in c_h:
                                for t in c_t:
                                    all_12.append(f"{h}{t}")
                                    
                        counts = Counter(all_12)
                        for cmb, count in counts.items():
                            is_vip = ((int(cmb[0]) + int(cmb[1])) % 10) in trend_b
                            if is_vip and count >= 2: super_vip.append(cmb)
                            elif is_vip: vip_list.append(cmb)
                            else: rest_list.append(cmb)

                        with cols[i]:
                            st.markdown(f"### {slot} ခန့်မှန်းရလဒ်")
                            st.markdown(f"<p style='font-size:1.2em;'>**Super Key [{', '.join(str(k) for k in super_key)}]**</p>", unsafe_allow_html=True)
                            st.markdown("---")
                            
                            if super_vip:
                                st.markdown("#### Super VIP")
                                st.markdown(format_combos(super_vip, super_key), unsafe_allow_html=True)
                                st.code(", ".join(super_vip), language="text")
                            if vip_list:
                                st.markdown("#### VIP")
                                st.markdown(format_combos(vip_list, super_key), unsafe_allow_html=True)
                                st.code(", ".join(vip_list), language="text")
                            if rest_list:
                                st.markdown("####") 
                                st.markdown(format_combos(rest_list, super_key), unsafe_allow_html=True)
                                st.code(", ".join(rest_list), language="text")

            st.markdown("---")
            st.markdown("### နောက်ကြောင်းပြန်စစ်မည်")
            c_bt1, c_bt2 = st.columns(2)
            with c_bt1: bt_days_1 = st.number_input("ရက်အရေအတွက်", min_value=5, max_value=100, value=15, key="bt1_d")
            with c_bt2: bt_time_1 = st.radio("အချိန်ရွေးပါ", ["AM", "PM", "Both"], horizontal=True, key="bt1_t")
            if st.button("စစ်ဆေးမည် 🔍", key="btn_bt_tab1"):
                with st.spinner(f"{bt_days_1} ရက်စာ Backtest တွက်ချက်နေပါသည်..."):
                    bt_data = []
                    start_idx = max(10, len(daily_draws) - bt_days_1)
                    for test_d in range(start_idx, len(daily_draws)):
                        slots_to_test = ["AM", "PM"] if bt_time_1 == "Both" else [bt_time_1]
                        for t_slot in slots_to_test:
                            idx1, idx2 = (0,1) if t_slot == "AM" else (2,3)
                            if daily_draws[test_d][idx1] is not None:
                                k, _ = get_gap_5x5_super_key(test_d, t_slot, daily_draws)
                                if k:
                                    actual = f"{daily_draws[test_d][idx1]}{daily_draws[test_d][idx2]}"
                                    is_win = int(actual[0]) in k or int(actual[1]) in k
                                    bt_data.append({"Day": test_d, "Time": t_slot, "Actual": actual, "Super Key": str(k), "Result": "✅ WIN" if is_win else "❌ LOSE"})
                    if bt_data: st.dataframe(pd.DataFrame(bt_data), use_container_width=True)

        # ==========================================
        # TAB 2: Stock Market စနစ်
        # ==========================================
        with tab2:
            st.subheader("Stock Market Hybrid စနစ်")
            e_time = st.radio("အချိန်ရွေးပါ:", ["AM", "PM"], key="tab2_time", horizontal=True)
            if st.button("ခန့်မှန်းမည်", type="primary", key="btn_tab2"):
                with st.spinner("Hybrid Stock Market Trend များကို တွက်ချက်နေပါသည်..."):
                    calc_draws = daily_draws.copy()
                    if e_time == "AM" and calc_draws[-1][0] is not None:
                        calc_draws.append([None, None, None, None]); target_d = len(calc_draws) - 1
                    elif e_time == "PM" and calc_draws[-1][2] is not None:
                        if calc_draws[-1][0] is None: target_d = len(calc_draws) - 1
                        else: calc_draws.append([None, None, None, None]); target_d = len(calc_draws) - 1
                    else: target_d = len(calc_draws) - 1

                    super_key, full_hist = get_gap_5x5_super_key(target_d, e_time, calc_draws)
                    if full_hist:
                        t_h, t_t, _ = get_hybrid_5x5_trend(full_hist)
                        st.success(f"🎯 **Stock Market စနစ် ခန့်မှန်းချက်**")
                        pairs = [f"{h}{t}" for h in t_h for t in t_t]
                        st.markdown(f"### 🔥 ထွက်ပေါ်လာသော ၂၅ ကွက် (Super Key: {super_key})")
                        st.markdown(format_combos(pairs, super_key), unsafe_allow_html=True)
                        st.code(", ".join(pairs), language="text")

            st.markdown("---")
            st.markdown("### Stock Market စနစ်ကို နောက်ကြောင်းပြန်စစ်မည်")
            c_bt3, c_bt4 = st.columns(2)
            with c_bt3: bt_days_2 = st.number_input("ရက်အရေအတွက်", min_value=5, max_value=100, value=15, key="bt2_d")
            with c_bt4: bt_time_2 = st.radio("အချိန်ရွေးပါ", ["AM", "PM", "Both"], horizontal=True, key="bt2_t")
            if st.button("စစ်ဆေးမည် 🔍", key="btn_bt_tab2"):
                with st.spinner("Stock Market Backtest တွက်ချက်နေပါသည်..."):
                    bt_data_sm = []
                    start_idx = max(10, len(daily_draws) - bt_days_2)
                    for test_d in range(start_idx, len(daily_draws)):
                        slots_to_test = ["AM", "PM"] if bt_time_2 == "Both" else [bt_time_2]
                        for t_slot in slots_to_test:
                            idx1, idx2 = (0,1) if t_slot == "AM" else (2,3)
                            if daily_draws[test_d][idx1] is not None:
                                s_key, f_hist = get_gap_5x5_super_key(test_d, t_slot, daily_draws)
                                if f_hist:
                                    t_h, t_t, _ = get_hybrid_5x5_trend(f_hist)
                                    sm_pairs = [f"{h}{t}" for h in t_h for t in t_t]
                                    actual = f"{daily_draws[test_d][idx1]}{daily_draws[test_d][idx2]}"
                                    sm_win = actual in sm_pairs
                                    key_win = int(actual[0]) in s_key or int(actual[1]) in s_key
                                    bt_data_sm.append({"Day": test_d, "Time": t_slot, "Actual": actual, "Stock 25": "✅" if sm_win else "❌", "Super Key": "✅" if key_win else "❌"})
                    if bt_data_sm: st.dataframe(pd.DataFrame(bt_data_sm), use_container_width=True)

        # ==========================================
        # TAB 3: 2d history
        # ==========================================
        with tab3:
            st.subheader("2D History (Data Analysis)")
            t_2d = st.text_input("ရှာဖွေလိုသော ဂဏန်းရိုက်ထည့်ပါ (ဥပမာ - 01)", max_chars=2)
            ana_mode = st.radio("စစ်ဆေးမည့်ပုံစံ", ["Auto (Best 95%+ & Comeback)", "Manual"], horizontal=True)
            if ana_mode == "Manual": manual_times = st.number_input("နောက်ဆုံး အကြိမ်ရေ ဘယ်လောက်စစ်မလဲ?", min_value=5, max_value=100, value=20)
                
            if st.button("သမိုင်းကြောင်း ရှာဖွေမည် 🔍", type="primary"):
                if len(t_2d) == 2:
                    with st.spinner(f"[{t_2d}] အတွက် Data များကို ရှာဖွေနေပါသည်..."):
                        if ana_mode == "Auto (Best 95%+ & Comeback)":
                            best_res = analyze_history_v26(t_2d, f_draws, scope_min=20, scope_max=40, time_frame=20)
                            if best_res:
                                st.success(f"🎯 **အကောင်းဆုံး အခြေအနေ တွေ့ရှိပါသည်! (နောက်ဆုံး {best_res['scope']} ကြိမ်အတွင်း)**")
                                st.markdown(f"**မူအမျိုးအစား:** {best_res['type']} ➡️ <span style='color:red; font-size:1.6em; font-weight:bold;'>[{best_res['val']}]</span>", unsafe_allow_html=True)
                                st.write(f"**မှန်ကန်မှု:** {best_res['hits']} ({best_res['rate']:.1f}%) | Time Frame: နောက်ပွဲ ၂၀ (၁၀ ရက်စာ) အတွင်း")
                                if best_res['comeback']: st.error("🔥 **အထူးသတိပေးချက်: ဤမူသည် လွန်ခဲ့သောပွဲက လွဲချော်ခဲ့ပြီး ယခု ပြန်လည်ဝင်ရောက်လာသော [အမှားပြန်ဆယ်မူ] ဖြစ်သဖြင့် အထူး အားကောင်းနေပါသည်။**")
                            else: st.warning("လတ်တလော အကြိမ် ၂၀ မှ ၄၀ အတွင်း 95% အထက် သေချာသော အခြေအနေ မတွေ့ရှိပါ။")
                        else:
                            best_res = analyze_history_v26(t_2d, f_draws, scope_min=manual_times, scope_max=manual_times, time_frame=20)
                            if best_res:
                                st.info(f"📊 **နောက်ဆုံး {manual_times} ကြိမ်အတွင်း တွေ့ရှိချက်**")
                                st.write(f"**မူ:** {best_res['type']} [{best_res['val']}] - {best_res['rate']:.1f}%")
                            else: st.warning("သတ်မှတ်ထားသော အကြိမ်ရေအတွင်း ထင်ရှားသော မူမရှိပါ။")

        # ==========================================
        # TAB 4: ရက်ချိန်းပြည့်မူများ
        # ==========================================
        with tab4:
            st.subheader("ရက်ချိန်းပြည့်မူများ (1 Draw Left)")
            st.info("အပေါ်တွင် 5x5 စစ်ထုတ်ထားသော VIP ကတ်များ၊ အောက်တွင် အသေးစိတ်ဇယား")
            if st.button("မူကျန်များ ရှာဖွေမည် 🚀", type="primary"):
                with st.spinner("မူ (၁၀) မျိုးလုံးကို ပတ်မွှေနေပါသည်..."):
                    raw_alerts = run_mode4_alerts(f_draws)
                    if raw_alerts:
                        _, full_hist = get_gap_5x5_super_key(len(daily_draws)-1, "AM", daily_draws)
                        t_h, t_t, t_b = get_hybrid_5x5_trend(full_hist)
                        valid_gks = t_h + t_t
                        
                        super_cards = []
                        for a in raw_alerts:
                            if a['Type'] == "လုံးဘိုင်" and int(a['Value']) in valid_gks: super_cards.append(a)
                                
                        if super_cards:
                            st.markdown("### 🌟 Super VIP ကတ်များ (5x5 Gatekeeper ဖြင့် အတည်ပြုပြီး)")
                            cols = st.columns(min(3, len(super_cards)))
                            for i, card in enumerate(super_cards):
                                with cols[i % 3]:
                                    st.success(f"🔥 **{card['Type']} : {card['Value']}**\n\n⏳ {card['TF']} အတွင်း\n\n🎯 {card['Rate']:.1f}% သေချာသည်")
                                    
                        st.markdown("---")
                        st.markdown("### 📋 မူကျန်အားလုံး အသေးစိတ်ဇယား")
                        df_alerts = pd.DataFrame(raw_alerts)
                        st.dataframe(df_alerts.sort_values(by="Rate", ascending=False), use_container_width=True)
                    else: st.success("✅ ယခုအချိန်တွင် ရက်ချိန်းပြည့် (၁ ပွဲသာလို) မူများ မရှိသေးပါ။")

        # ==========================================
        # TAB 5: 2D Calendar
        # ==========================================
        with tab5:
            st.subheader("📅 2D Calendar (မှတ်တမ်း)")
            def get_smart_calendar(df, daily_draws):
                day_col = None
                for col in df.columns:
                    if col.lower() in ['day', 'date', 'days', 'ရက်']: day_col = col; break
                original_len = len(df); total_len = len(daily_draws)
                assigned_dates = [""] * total_len; assigned_days = [""] * total_len
                current_date = pd.to_datetime('2026-04-03')
                
                for i in range(original_len - 1, -1, -1):
                    if day_col is not None and pd.notna(df.iloc[i][day_col]):
                        file_day = str(df.iloc[i][day_col]).strip()[:3].title() 
                        valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                        if file_day in valid_days:
                            while current_date.strftime("%a") != file_day: current_date -= pd.Timedelta(days=1)
                            assigned_dates[i] = current_date.strftime("%d %B %Y")
                            assigned_days[i] = file_day
                            current_date -= pd.Timedelta(days=1)
                            continue
                    while current_date.weekday() >= 5: current_date -= pd.Timedelta(days=1)
                    assigned_dates[i] = current_date.strftime("%d %B %Y"); assigned_days[i] = current_date.strftime("%a")
                    current_date -= pd.Timedelta(days=1)
                    
                if total_len > original_len:
                    next_date = pd.to_datetime('2026-04-03') + pd.Timedelta(days=1)
                    for i in range(original_len, total_len):
                        while next_date.weekday() >= 5: next_date += pd.Timedelta(days=1)
                        assigned_dates[i] = next_date.strftime("%d %B %Y"); assigned_days[i] = next_date.strftime("%a")
                        next_date += pd.Timedelta(days=1)
                
                cal_data = []
                for i, d in enumerate(daily_draws):
                    cal_data.append({"Date": assigned_dates[i], "Day": assigned_days[i], "AM": f"{d[0]}{d[1]}" if d[0] is not None else "-", "PM": f"{d[2]}{d[3]}" if d[2] is not None else "-"})
                return pd.DataFrame(cal_data)

            df_cal = get_smart_calendar(raw_df, daily_draws)
            st.dataframe(df_cal.iloc[::-1].reset_index(drop=True), use_container_width=True)

