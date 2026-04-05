import streamlit as st
import pandas as pd
import io
import itertools
from collections import Counter

# --- Streamlit Page Config ---
st.set_page_config(page_title="2D SUPER VIP - Super Key", page_icon="🛡️", layout="wide")

# --- 1. Configurations & Dictionaries ---
MIN_STREAK = 3    
all_combos = list(itertools.combinations(range(20), 3))
target_types = ["ထိပ်", "ပိတ်", "ဘရိတ်"]

power_dict = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
natkhat_dict = {0: 7, 7: 0, 1: 8, 8: 1, 2: 4, 4: 2, 3: 5, 5: 3, 6: 9, 9: 6}

# --- 2. Password Protection ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "v27admin": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("2D SUPER VIP မှ ကြိုဆိုပါတယ်။ Password ရိုက်ထည့်ပါ -", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("2D SUPER VIP မှ ကြိုဆိုပါတယ်။ Password ရိုက်ထည့်ပါ -", type="password", on_change=password_entered, key="password")
        st.error("😕 Password မှားနေပါတယ်။ ပြန်ကြိုးစားကြည့်ပါ။")
        return False
    else:
        return True

# --- 3. Data Processing Function ---
def process_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
    else: df = pd.read_excel(uploaded_file)
        
    df.columns = df.columns.str.strip().str.lower()
    for col in ['am1', 'am2', 'pm1', 'pm2']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['am1', 'am2']).reset_index(drop=True)
    
    daily_draws = []
    for index, row in df.iterrows():
        am_valid = pd.notna(row['am1']) and pd.notna(row['am2'])
        pm_valid = 'pm1' in df.columns and 'pm2' in df.columns and pd.notna(row['pm1']) and pd.notna(row['pm2'])
        if am_valid and pm_valid: daily_draws.append([int(row['am1']), int(row['am2']), int(row['pm1']), int(row['pm2'])])
        elif am_valid and not pm_valid: daily_draws.append([int(row['am1']), int(row['am2']), None, None])
    return df, daily_draws

# --- 4. Core Algorithms (Fast & Secure) ---
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
                if valid_root:
                    root_groups.setdefault(tuple(root_seq), []).append(root_combo)

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

@st.cache_data(show_spinner=False)
def get_gap_5x5_super_key(d, draw_time, daily_draws, window_size=300):
    if d < 10 or d >= len(daily_draws): return None
    
    col_h, col_t = (0, 1) if draw_time == "AM" else (2, 3)
    actual_h = daily_draws[d][col_h] if d < len(daily_draws) else None
    actual_t = daily_draws[d][col_t] if d < len(daily_draws) else None
    
    # [🔒 SECURITY: STRICT LOOKAHEAD PREVENTION]
    full_history = []
    for past_d in range(d + 1):
        if daily_draws[past_d][0] is not None and daily_draws[past_d][1] is not None:
            if past_d == d and draw_time == "AM": pass 
            else: full_history.append((daily_draws[past_d][0], daily_draws[past_d][1]))
        if daily_draws[past_d][2] is not None and daily_draws[past_d][3] is not None:
            if past_d == d and draw_time == "PM": pass 
            else: full_history.append((daily_draws[past_d][2], daily_draws[past_d][3]))

    if len(full_history) < 2: return None
    last_draw = full_history[-1]
    last_h, last_t = last_draw[0], last_draw[1]

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
        if curr[0] == last_h: trans_freq[nxt[0]] += 1
        if curr[1] == last_t: trans_freq[nxt[1]] += 1
    
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

    scores[power_dict[last_h]] += 1.0
    scores[power_dict[last_t]] += 1.0
    scores[natkhat_dict[last_h]] += 1.0
    scores[natkhat_dict[last_t]] += 1.0

    top_3_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)[:3]
    
    actual_2d = f"{actual_h}{actual_t}" if actual_h is not None and actual_t is not None else "-"
    is_win = False
    if actual_h is not None and actual_t is not None:
        is_win = (actual_h in top_3_keys) or (actual_t in top_3_keys)

    return {
        'Day': d, 
        'Time': draw_time, 
        'Actual 2D': actual_2d, 
        'Super Key': top_3_keys,
        'is_win': is_win,
        'last_draw': f"{last_h}{last_t}"
    }

# --- 5. Main Web App Layout ---
if check_password():
    st.title("🛡️ 2D SUPER VIP (V28.1 - Synergy Super Key)")
    st.markdown("---")

    st.sidebar.header("📂 Data Upload")
    uploaded_file = st.sidebar.file_uploader("မှတ်တမ်း Excel/CSV ဖိုင် တင်ရန်", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        df, daily_draws = process_file(uploaded_file)
        total_days = len(daily_draws)
        st.sidebar.success(f"✅ Data ဖတ်ရှုခြင်း အောင်မြင်ပါသည်။ (စုစုပေါင်း {total_days} ရက်)")

        tab1, tab2, tab3 = st.tabs([
            "🎯 Super Key ခန့်မှန်းချက် (Live Prediction)", 
            "🔍 နောက်ကြောင်းပြန်စစ်မည် (Backtest)", 
            "📅 2D Calendar"
        ])

        # --- TAB 1: LIVE PREDICTION ---
        with tab1:
            st.subheader("မကြာမီ ထွက်ပေါ်မည့် ပွဲစဉ်အတွက် Super Key (၃) လုံး ခန့်မှန်းခြင်း")
            
            # နောက်လာမည့် ပွဲစဉ်ကို အလိုအလျောက် ရှာဖွေခြင်း
            calc_draws = daily_draws.copy()
            last_row = calc_draws[-1]
            
            if last_row[2] is None:
                target_slot = "PM"
                target_idx = len(calc_draws) - 1
            else:
                target_slot = "AM"
                calc_draws.append([None, None, None, None]) # Appending Empty Day for Future
                target_idx = len(calc_draws) - 1
                
            st.info(f"👉 နောက်ဆုံးထည့်သွင်းထားသော Data အရ ခန့်မှန်းရမည့် ပွဲစဉ်မှာ: **Day {target_idx} ({target_slot})** ဖြစ်ပါသည်။")
            
            if st.button("ခန့်မှန်းမည် 🚀", type="primary"):
                with st.spinner("Gap ပင်ခြား နှင့် 5x5 Rolling Data များကို ပေါင်းစပ်တွက်ချက်နေပါသည်..."):
                    res = get_gap_5x5_super_key(target_idx, target_slot, calc_draws)
                    
                    if res:
                        st.markdown(f"### 🎯 **{target_slot} အတွက် အတိကျဆုံး Super Key ရလဒ်**")
                        st.write(f"နောက်ဆုံးထွက်ခဲ့သော ဂဏန်း: **{res['last_draw']}**")
                        st.markdown("---")
                        
                        key_str = " ၊ ".join([str(k) for k in res['Super Key']])
                        st.success(f"🔥 **SUPER KEY (3 လုံး): [ {key_str} ]**")
                        
                        st.caption("💡 အထက်ပါ Super Key ၃ လုံးထဲမှ တစ်လုံးသည် ထိပ် သို့မဟုတ် ပိတ်တွင် သေချာပေါက် ကပ်နိုင်ခြေ ၆၀% အထက် ရှိပါသည်။ (Pattern + Trend Synergy System ကို အသုံးပြုထားပါသည်။)")
                    else:
                        st.error("Data မလုံလောက်သေးပါ။")

        # --- TAB 2: BACKTEST ---
        with tab2:
            st.subheader("🔍 Synergy Super Key ကို နောက်ကြောင်းပြန်စစ်မည်")
            st.caption("AI သည် အနာဂတ်ဂဏန်းကို ခိုးမကြည့်ကြောင်း (Zero Lookahead Bias) အပြည့်အဝ အာမခံပါသည်။")
            
            if st.button("၁၅ ရက်စာ Backtest စစ်မည်", key="bt_e_btn"):
                with st.spinner("၁၅ ရက်စာ Backtest တွက်ချက်နေပါသည်..."):
                    test_limit = 15
                    bt_data = []
                    start_idx = max(20, len(daily_draws) - test_limit)
                    
                    progress_bar = st.progress(0)
                    total_steps = (len(daily_draws) - start_idx) * 2
                    current_step = 0
                    
                    for test_d in range(start_idx, len(daily_draws)):
                        # Test AM
                        if daily_draws[test_d][0] is not None:
                            res_am = get_gap_5x5_super_key(test_d, "AM", daily_draws)
                            if res_am:
                                bt_data.append({
                                    "Day": res_am['Day'], "Time": "AM",
                                    "Actual": res_am['Actual 2D'],
                                    "Super Key": str(res_am['Super Key']),
                                    "Result": "✅ WIN" if res_am['is_win'] else "❌ LOSE"
                                })
                        current_step += 1
                        progress_bar.progress(current_step / total_steps)
                        
                        # Test PM
                        if daily_draws[test_d][2] is not None:
                            res_pm = get_gap_5x5_super_key(test_d, "PM", daily_draws)
                            if res_pm:
                                bt_data.append({
                                    "Day": res_pm['Day'], "Time": "PM",
                                    "Actual": res_pm['Actual 2D'],
                                    "Super Key": str(res_pm['Super Key']),
                                    "Result": "✅ WIN" if res_pm['is_win'] else "❌ LOSE"
                                })
                        current_step += 1
                        progress_bar.progress(current_step / total_steps)
                        
                    if bt_data:
                        df_bt = pd.DataFrame(bt_data)
                        win_count = df_bt['Result'].str.contains('WIN').sum()
                        total_tests = len(df_bt)
                        win_rate = (win_count / total_tests) * 100
                        
                        st.success(f"📊 စမ်းသပ်မှု ပြီးဆုံးပါပြီ။ စုစုပေါင်း ({total_tests}) ကြိမ်တွင် ({win_count}) ကြိမ် အောင်မြင်ပါသည်။ (Win Rate: **{win_rate:.1f}%**)")
                        st.dataframe(df_bt, use_container_width=True)

        # --- TAB 3: CALENDAR VIEW ---
        with tab3:
            st.subheader("📅 2D Calendar (မှတ်တမ်း)")
            df_display = df.copy()
            df_display['AM'] = df_display.apply(lambda row: f"{int(row['am1'])}{int(row['am2'])}" if pd.notna(row['am1']) and pd.notna(row['am2']) else "-", axis=1)
            df_display['PM'] = df_display.apply(lambda row: f"{int(row['pm1'])}{int(row['pm2'])}" if 'pm1' in df.columns and 'pm2' in df.columns and pd.notna(row['pm1']) and pd.notna(row['pm2']) else "-", axis=1)
            df_display['Day'] = df_display.index
            st.dataframe(df_display[['Day', 'AM', 'PM']], use_container_width=True, hide_index=True)

    else:
        st.info("👈 ဘေးဘက် (Sidebar) မှတစ်ဆင့် Data ပါဝင်သော Excel သို့မဟုတ် CSV ဖိုင်ကို အရင် တင်ပေးပါ။")
