import streamlit as st
import pandas as pd
import io
import itertools
from collections import Counter
import datetime

# --- Streamlit Page Config ---
st.set_page_config(page_title="2D SUPER VIP", page_icon="🛡️", layout="wide")

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

# --- 3. Core Algorithms ---
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
    return top_3_keys, full_history

# --- 4. 5x5 Gatekeeper Replacement Logic ---
def get_trend_replacements(full_history, window_size=300):
    recent_history = full_history[-window_size:] if len(full_history) > window_size else full_history
    
    head_scores = {i: 0.0 for i in range(10)}
    tail_scores = {i: 0.0 for i in range(10)}
    break_scores = {i: 0.0 for i in range(10)}
    
    for i, p_d in enumerate(full_history[-15:]):
        w = (i + 1) * 0.5
        head_scores[p_d[0]] += w
        tail_scores[p_d[1]] += w
        break_scores[(p_d[0] + p_d[1]) % 10] += w
        
    top_h = sorted(head_scores.keys(), key=lambda x: head_scores[x], reverse=True)[:5]
    top_t = sorted(tail_scores.keys(), key=lambda x: tail_scores[x], reverse=True)[:5]
    top_b = sorted(break_scores.keys(), key=lambda x: break_scores[x], reverse=True)[:5]
    
    return top_h, top_t, top_b

def gatekeeper_replace(gap_list, trend_list):
    clean_list = []
    for g in gap_list:
        if g in trend_list: clean_list.append(g)
        else:
            for t in trend_list:
                if t not in clean_list:
                    clean_list.append(t)
                    break
    return clean_list

def color_key_match(combo, key_list):
    if int(combo[0]) in key_list or int(combo[1]) in key_list:
        return f":red[**{combo}**]"
    return combo

# --- 5. Date & Calendar Matcher Engine ---
def get_smart_calendar(df, daily_draws):
    # ဖိုင်ထဲမှာ 'Day' ဒါမှမဟုတ် ရက်စွဲခေါင်းစဉ် ပါမပါ ရှာမည်
    day_col = None
    for col in df.columns:
        if col.lower() in ['day', 'date', 'days', 'ရက်']:
            day_col = col
            break
            
    original_len = len(df)
    total_len = len(daily_draws)
    assigned_dates = [""] * total_len
    assigned_days = [""] * total_len
    
    # နောက်ပြန်တိုက်စစ်မည့် အခြေပြုရက်စွဲ (3 April 2026, Friday)
    current_date = pd.to_datetime('2026-04-03')
    
    # (၁) မူလ Excel Data အတွက် နောက်ပြန်တွက်ခြင်း
    for i in range(original_len - 1, -1, -1):
        if day_col is not None and pd.notna(df.iloc[i][day_col]):
            file_day = str(df.iloc[i][day_col]).strip()[:3].title() # ဥပမာ - 'Mon', 'Tue'
            valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            
            if file_day in valid_days:
                # Excel ထဲက နေ့နာမည်နဲ့ မကိုက်မချင်း နောက်ပြန်ဆုတ်မည် (ပိတ်ရက်များကို ကျော်ရန်)
                while current_date.strftime("%a") != file_day:
                    current_date -= pd.Timedelta(days=1)
                
                assigned_dates[i] = current_date.strftime("%d %B %Y")
                assigned_days[i] = file_day
                current_date -= pd.Timedelta(days=1)
                continue
                
        # အကယ်၍ Day ခေါင်းစဉ် မရှိပါက ပုံမှန် စနေ၊ တနင်္ဂနွေကိုသာ ကျော်မည်
        while current_date.weekday() >= 5: 
            current_date -= pd.Timedelta(days=1)
        assigned_dates[i] = current_date.strftime("%d %B %Y")
        assigned_days[i] = current_date.strftime("%a")
        current_date -= pd.Timedelta(days=1)
        
    # (၂) App ပေါ်မှ တိုက်ရိုက် ထည့်ထားသော Data သစ်များအတွက် ရှေ့ဆက်တွက်ခြင်း
    if total_len > original_len:
        next_date = pd.to_datetime('2026-04-03') + pd.Timedelta(days=1)
        for i in range(original_len, total_len):
            while next_date.weekday() >= 5: 
                next_date += pd.Timedelta(days=1)
            assigned_dates[i] = next_date.strftime("%d %B %Y")
            assigned_days[i] = next_date.strftime("%a")
            next_date += pd.Timedelta(days=1)
            
    # Data Frame တည်ဆောက်ခြင်း
    cal_data = []
    for i, d in enumerate(daily_draws):
        am_str = f"{d[0]}{d[1]}" if d[0] is not None else "-"
        pm_str = f"{d[2]}{d[3]}" if d[2] is not None else "-"
        cal_data.append({
            "Date": assigned_dates[i],
            "Day": assigned_days[i],
            "AM": am_str,
            "PM": pm_str
        })
        
    return pd.DataFrame(cal_data)


# --- 6. Main Web App Layout ---
if check_password():
    st.title("🛡️ 2D SUPER VIP (V28.0 System)")
    st.markdown("---")

    # Initialize State
    if "data_loaded" not in st.session_state:
        st.session_state["data_loaded"] = False

    # Sidebar: Data Input
    if not st.session_state["data_loaded"]:
        st.sidebar.header("📂 Excel / CSV Data စတင်တင်ရန်")
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
        st.sidebar.header("📝 ယနေ့ထွက်ဂဏန်း အသစ်ထည့်ရန်")
        st.sidebar.caption("Data ဖိုင်ကို ထပ်တင်စရာမလိုဘဲ တိုက်ရိုက် Update လုပ်နိုင်ပါသည်။")
        
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
                    
            st.session_state["daily_draws"] = current_draws
            st.rerun()
            
        if st.sidebar.button("Data ဖိုင် အသစ်ပြန်တင်မည်", type="secondary"):
            st.session_state["data_loaded"] = False
            st.rerun()

    # --- MAIN APP ---
    if st.session_state["data_loaded"]:
        daily_draws = st.session_state["daily_draws"]
        raw_df = st.session_state["raw_df"]
        
        tab1, tab2, tab3 = st.tabs(["မူလစနစ်", "Stock Market စနစ်", "2D Calendar"])

        # ==========================================
        # TAB 1: မူလစနစ် (Gap + Gatekeeper Logic)
        # ==========================================
        with tab1:
            st.subheader("AM/PM (ပင်ခြားစနစ်)")
            if st.button("တွက်ချက်မည်", type="primary", key="btn_tab1"):
                with st.spinner("ပင်ခြားစနစ်နှင့် Trend များကို တိုက်စစ်နေပါသည်..."):
                    calc_draws = daily_draws.copy()
                    last_row = calc_draws[-1]
                    predict_slots = []
                    
                    if last_row[2] is None: 
                        predict_slots.append(("PM", len(calc_draws) - 1))
                    else:
                        calc_draws.append([None, None, None, None])
                        predict_slots.append(("AM", len(calc_draws) - 1))
                        predict_slots.append(("PM", len(calc_draws) - 1))
                        
                    cols = st.columns(len(predict_slots))
                    
                    for i, (slot, t_idx) in enumerate(predict_slots):
                        super_key, full_hist = get_gap_5x5_super_key(t_idx, slot, calc_draws)
                        if super_key is None: continue
                        
                        trend_h, trend_t, trend_b = get_trend_replacements(full_hist)
                        gap_results = {3: [], 4: [], 5: []}
                        
                        for gap in [3, 4, 5]:
                            preds = calculate_prediction(t_idx, slot, calc_draws, [gap])
                            g_heads = preds["ထိပ်"][:2] if preds["ထိပ်"] else trend_h[:2]
                            g_tails = preds["ပိတ်"][:2] if preds["ပိတ်"] else trend_t[:2]
                            g_breaks = preds["ဘရိတ်"][:2] if preds["ဘရိတ်"] else trend_b[:2]
                            
                            clean_h = gatekeeper_replace(g_heads, trend_h)
                            clean_t = gatekeeper_replace(g_tails, trend_t)
                            clean_b = gatekeeper_replace(g_breaks, trend_b)
                            
                            combos = []
                            for h in clean_h:
                                for t in clean_t:
                                    if (h + t) % 10 in clean_b: combos.append(f"{h}{t}")
                            gap_results[gap] = combos
                            
                        all_combos_list = gap_results[3] + gap_results[4] + gap_results[5]
                        counts = Counter(all_combos_list)
                        
                        super_vip = [c for c, count in counts.items() if count >= 3]
                        vip = [c for c, count in counts.items() if count == 2]
                        rest = [c for c, count in counts.items() if count == 1]

                        with cols[i]:
                            st.markdown(f"### {slot} ခန့်မှန်းရလဒ်")
                            st.write(f"**Super Key {super_key}**")
                            st.markdown("---")
                            
                            if super_vip:
                                st.markdown("#### Super VIP")
                                st.markdown(" &nbsp;&nbsp; ".join([color_key_match(c, super_key) for c in super_vip]))
                                st.code(", ".join(super_vip), language="text") 
                                
                            if vip:
                                st.markdown("#### VIP")
                                st.markdown(" &nbsp;&nbsp; ".join([color_key_match(c, super_key) for c in vip]))
                                st.code(", ".join(vip), language="text") 
                                
                            if rest:
                                st.markdown("####") 
                                st.markdown(" &nbsp;&nbsp; ".join([color_key_match(c, super_key) for c in rest]))
                                st.code(", ".join(rest), language="text") 
                                
                            with st.expander("အပြည့်အစုံကြည့်ပါ"):
                                st.write("**၃ ပင်ခြား:**", ", ".join(gap_results[3]) if gap_results[3] else "မရှိပါ")
                                st.write("**၄ ပင်ခြား:**", ", ".join(gap_results[4]) if gap_results[4] else "မရှိပါ")
                                st.write("**၅ ပင်ခြား:**", ", ".join(gap_results[5]) if gap_results[5] else "မရှိပါ")

            st.markdown("---")
            st.markdown("### နောက်ကြောင်းပြန်စစ်မည်")
            if st.button("စစ်ဆေးမည် 🔍", key="btn_bt_tab1"):
                with st.spinner("Backtest တွက်ချက်နေပါသည်..."):
                    test_limit = 15
                    bt_data = []
                    start_idx = max(10, len(daily_draws) - test_limit)
                    
                    for test_d in range(start_idx, len(daily_draws)):
                        if daily_draws[test_d][0] is not None:
                            k_am, _ = get_gap_5x5_super_key(test_d, "AM", daily_draws)
                            if k_am:
                                a_am = f"{daily_draws[test_d][0]}{daily_draws[test_d][1]}"
                                is_w = int(a_am[0]) in k_am or int(a_am[1]) in k_am
                                bt_data.append({"Day": test_d, "Time": "AM", "Actual": a_am, "Super Key": str(k_am), "Result": "✅ WIN" if is_w else "❌ LOSE"})
                            
                        if daily_draws[test_d][2] is not None:
                            k_pm, _ = get_gap_5x5_super_key(test_d, "PM", daily_draws)
                            if k_pm:
                                a_pm = f"{daily_draws[test_d][2]}{daily_draws[test_d][3]}"
                                is_w = int(a_pm[0]) in k_pm or int(a_pm[1]) in k_pm
                                bt_data.append({"Day": test_d, "Time": "PM", "Actual": a_pm, "Super Key": str(k_pm), "Result": "✅ WIN" if is_w else "❌ LOSE"})
                    
                    if bt_data:
                        df_bt = pd.DataFrame(bt_data)
                        st.dataframe(df_bt, use_container_width=True)

        # ==========================================
        # TAB 2: Stock Market စနစ်
        # ==========================================
        with tab2:
            st.subheader("Stock Market စနစ်")
            c1, c2 = st.columns([1, 2])
            with c1: e_time = st.radio("အချိန်ရွေးပါ:", ["AM", "PM"], key="tab2_time")
            
            if st.button("ခန့်မှန်းမည်", type="primary", key="btn_tab2"):
                with st.spinner("Stock Market Trend များကို တွက်ချက်နေပါသည်..."):
                    calc_draws = daily_draws.copy()
                    if e_time == "AM" and calc_draws[-1][0] is not None:
                        calc_draws.append([None, None, None, None])
                        target_d = len(calc_draws) - 1
                    elif e_time == "PM" and calc_draws[-1][2] is not None:
                        if calc_draws[-1][0] is None: target_d = len(calc_draws) - 1
                        else:
                            calc_draws.append([None, None, None, None])
                            target_d = len(calc_draws) - 1
                    else: target_d = len(calc_draws) - 1

                    _, full_hist = get_gap_5x5_super_key(target_d, e_time, calc_draws)
                    if full_hist:
                        t_h, t_t, _ = get_trend_replacements(full_hist)
                        st.success(f"🎯 **Stock Market စနစ် ခန့်မှန်းချက်**")
                        col_h, col_t = st.columns(2)
                        with col_h: st.info(f"**ထိပ် ၅ လုံး:** {', '.join(str(x) for x in t_h)}")
                        with col_t: st.warning(f"**ပိတ် ၅ လုံး:** {', '.join(str(x) for x in t_t)}")
                        
                        pairs = [f"{h}{t}" for h in t_h for t in t_t]
                        st.markdown("### 🔥 ထွက်ပေါ်လာသော ၂၅ ကွက်:")
                        st.code(", ".join(pairs), language="text")

            st.markdown("---")
            st.markdown("### Stock Market စနစ်ကို နောက်ကြောင်းပြန်စစ်မည်")
            if st.button("စစ်ဆေးမည် 🔍", key="btn_bt_tab2"):
                 st.info("Stock Market စနစ် နောက်ကြောင်းပြန်စစ်ဆေးမှု ဇယားကို ဤနေရာတွင် မြင်တွေ့ရပါမည်။")

        # ==========================================
        # TAB 3: 2D Calendar
        # ==========================================
        with tab3:
            st.subheader("📅 2D Calendar (မှတ်တမ်း)")
            st.caption("Excel ဖိုင်ပါ ရက်များအတိုင်း အလိုအလျောက် တိုက်စစ်ပေးထားပါသည်။ (ပိတ်ရက်များကို ကျော်ထားပါသည်)")
            
            df_cal = get_smart_calendar(raw_df, daily_draws)
            st.dataframe(df_cal.iloc[::-1].reset_index(drop=True), use_container_width=True)
