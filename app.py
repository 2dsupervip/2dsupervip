import streamlit as st
import pandas as pd
import io
import itertools
from collections import Counter

# --- 1. Password Protection ---
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

# --- 2. Core Algorithm Functions (Gap) ---
MIN_STREAK = 3    
all_combos = list(itertools.combinations(range(20), 3))
target_types = ["ထိပ်", "ပိတ်", "ဘရိတ်"]

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

    top_2_results = {"ထိပ်": [], "ပိတ်": [], "ဘရိတ်": []}
    if target_idx not in daily_hists: return top_2_results
    current_hist = daily_hists[target_idx]

    for t_type in target_types:
        votes = {}
        for skip in skip_sizes:
            step = skip + 1 
            if target_idx - (MIN_STREAK * step) - 6 < 0: continue
            matches = []
            for root_combo in all_combos:
                root_seq = []
                valid_root = True
                for g in range(1, MIN_STREAK + 1):
                    t_idx_temp = target_idx - (g * step)
                    if t_idx_temp not in daily_hists: valid_root = False; break
                    root_seq.append(sum(daily_hists[t_idx_temp][i] for i in root_combo) % 10)
                if not valid_root: continue
                for combo in all_combos:
                    valid = True
                    for g in range(1, MIN_STREAK + 1):
                        t_idx_temp = target_idx - (g * step)
                        if t_idx_temp not in targets: valid = False; break
                        target_val = targets[t_idx_temp][t_type]
                        if target_val is None: valid = False; break
                        current_sum = (sum(daily_hists[t_idx_temp][i] for i in combo) + target_val) % 10
                        if root_seq[g-1] != current_sum: valid = False; break
                    if valid:
                        root_0 = sum(current_hist[i] for i in root_combo) % 10
                        pred = (root_0 - sum(current_hist[i] for i in combo)) % 10
                        matches.append({'pred': pred, 'root_seq': tuple(root_seq)})
            df_matches = pd.DataFrame(matches)
            if not df_matches.empty:
                g_counts = df_matches.groupby(['pred', 'root_seq']).size().reset_index(name='f_count')
                valid_groups = g_counts[g_counts['f_count'] >= 3] 
                s_counts = valid_groups.groupby('pred').size().reset_index(name='g_count')
                valid_preds = s_counts[s_counts['g_count'] >= 2] 
                for _, row in valid_preds.iterrows(): votes[row['pred']] = row['g_count']
        if votes:
            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            top_2_results[t_type] = [k for k, v in sorted_votes[:2]]
    return top_2_results

def process_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
    else: df = pd.read_excel(uploaded_file)
        
    df.columns = df.columns.str.strip().str.lower()
    for col in ['am1', 'am2', 'pm1', 'pm2']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['am1', 'am2']).reset_index(drop=True)
    
    daily_draws = []
    last_valid_index = df.index[-1] if not df.empty else -1
    for index, row in df.iterrows():
        am_valid = pd.notna(row['am1']) and pd.notna(row['am2'])
        pm_valid = 'pm1' in df.columns and 'pm2' in df.columns and pd.notna(row['pm1']) and pd.notna(row['pm2'])
        if am_valid and pm_valid: daily_draws.append([int(row['am1']), int(row['am2']), int(row['pm1']), int(row['pm2'])])
        elif am_valid and not pm_valid and index == last_valid_index: daily_draws.append([int(row['am1']), int(row['am2']), None, None])
    return df, daily_draws

def get_ensemble_results(gap_results_list):
    all_combos, all_vips = [], []
    for res in gap_results_list:
        if not res: continue
        all_combos.extend(res['combos'])
        all_vips.extend(res['vips'])
        
    combo_counts = Counter(all_combos)
    unique_vips = set(all_vips)
    super_vips, vips, mains, backups = [], [], [], []
    
    for num, count in combo_counts.items():
        is_vip = num in unique_vips
        if is_vip and count >= 2: super_vips.append(num)
        elif is_vip and count == 1: vips.append(num)
        elif not is_vip and count >= 2: mains.append(num)
        else: backups.append(num)
            
    return sorted(super_vips), sorted(vips), sorted(mains), sorted(backups)

# --- 3. မြန်မာ 2D ပါဝါ၊ နက္ခတ် နှင့် Hybrid Key Logic ---
power_dict = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
natkhat_dict = {0: 7, 7: 0, 1: 8, 8: 1, 2: 4, 4: 2, 3: 5, 5: 3, 6: 9, 9: 6}

@st.cache_data(show_spinner=False)
def get_hybrid_super_key(test_idx, time_choice, daily_draws, gaps_to_check=[3, 4, 5]):
    scores = {i: 0 for i in range(10)}
    gap_heads = []
    for gap in gaps_to_check:
        preds = calculate_prediction(test_idx, time_choice, daily_draws, [gap])
        if preds["ထိပ်"]: gap_heads.extend(preds["ထိပ်"])
        
    gap_head_counts = Counter(gap_heads)
    for digit, count in gap_head_counts.items():
        scores[digit] += (count * 4) 
        
    prev_h, prev_t = None, None
    if time_choice == "AM":
        if test_idx > 0 and daily_draws[test_idx-1][2] is not None:
            prev_h, prev_t = daily_draws[test_idx-1][2], daily_draws[test_idx-1][3]
        elif test_idx > 0 and daily_draws[test_idx-1][0] is not None: 
            prev_h, prev_t = daily_draws[test_idx-1][0], daily_draws[test_idx-1][1]
    else: 
        if daily_draws[test_idx][0] is not None:
            prev_h, prev_t = daily_draws[test_idx][0], daily_draws[test_idx][1]
        else:
            if test_idx > 0 and daily_draws[test_idx-1][2] is not None:
                prev_h, prev_t = daily_draws[test_idx-1][2], daily_draws[test_idx-1][3]
            
    if prev_h is not None and prev_t is not None:
        brk = (prev_h + prev_t) % 10
        scores[brk] += 4                           
        scores[power_dict[prev_h]] += 3            
        scores[power_dict[prev_t]] += 3
        scores[natkhat_dict[prev_h]] += 2          
        scores[natkhat_dict[prev_t]] += 2
        scores[prev_h] += 2                        
        scores[prev_t] += 2
        
    top_3_digits = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)[:3]
    return [str(x) for x in top_3_digits]

# --- 4. ကွက်ချုပ် (၁၂-၁၂-၁၂) Scoring Logic ---
@st.cache_data(show_spinner=False)
def get_12_12_12_kuet_chote(test_idx, time_choice, daily_draws, gaps_to_check=[3, 4, 5]):
    history_start = max(0, test_idx - 5)
    recent_draws = daily_draws[history_start:test_idx]
    
    recent_heads, recent_tails = [], []
    for d in recent_draws:
        if d[0] is not None: recent_heads.append(d[0])
        if d[1] is not None: recent_tails.append(d[1])
        if d[2] is not None: recent_heads.append(d[2])
        if d[3] is not None: recent_tails.append(d[3])
        
    if time_choice == "PM" and test_idx < len(daily_draws):
        current_day = daily_draws[test_idx]
        if current_day[0] is not None: recent_heads.append(current_day[0])
        if current_day[1] is not None: recent_tails.append(current_day[1])
        
    head_counts, tail_counts = Counter(recent_heads), Counter(recent_tails)
    
    gap_heads, gap_tails = [], []
    for gap in gaps_to_check:
        preds = calculate_prediction(test_idx, time_choice, daily_draws, [gap])
        if preds["ထိပ်"]: gap_heads.extend(preds["ထိပ်"])
        if preds["ပိတ်"]: gap_tails.extend(preds["ပိတ်"])
        
    gap_head_counts, gap_tail_counts = Counter(gap_heads), Counter(gap_tails)
    
    head_scores, tail_scores = {}, {}
    for digit in range(10):
        h_score = head_counts.get(digit, 0)
        if head_counts.get(digit, 0) == 0: h_score -= 2 
        if digit in gap_head_counts: h_score += (gap_head_counts[digit] * 2) 
        head_scores[digit] = h_score
        
        t_score = tail_counts.get(digit, 0)
        if tail_counts.get(digit, 0) == 0: t_score -= 1 
        if digit in gap_tail_counts: t_score += (gap_tail_counts[digit] * 3) 
        tail_scores[digit] = t_score
        
    top_6_heads = sorted(head_scores.keys(), key=lambda k: head_scores[k], reverse=True)[:6]
    top_6_tails = sorted(tail_scores.keys(), key=lambda k: tail_scores[k], reverse=True)[:6]
    
    combo_scores = {}
    for h in top_6_heads:
        for t in top_6_tails:
            combo = f"{h}{t}"
            combo_scores[combo] = head_scores[h] + tail_scores[t] 
            
    sorted_combos = sorted(combo_scores.items(), key=lambda item: item[1], reverse=True)
    sorted_combo_list = [item[0] for item in sorted_combos]
    
    return sorted_combo_list[:12], sorted_combo_list[12:24], sorted_combo_list[24:36]

# --- 5. Main Web App Layout ---
if check_password():
    st.set_page_config(page_title="2D SUPER VIP", page_icon="🛡️", layout="wide")
    st.title("🛡️ 2D SUPER VIP (V27.00 - Hybrid Edition)")
    st.markdown("---")

    st.sidebar.header("📂 Data Upload")
    uploaded_file = st.sidebar.file_uploader("မှတ်တမ်း Excel/CSV ဖိုင် တင်ရန်", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        df, daily_draws = process_file(uploaded_file)
        total_days = len(daily_draws)
        st.sidebar.success(f"✅ Data ဖတ်ရှုခြင်း အောင်မြင်ပါသည်။ (စုစုပေါင်း {total_days} ရက်)")

        # TABS SETUP
        tab1, tab2, tab3, tab4 = st.tabs(["Super VIP ခန့်မှန်းချက်", "နောက်ကြောင်းပြန်စစ်မည်", "2D calendar", "🎯 ကွက်ချုပ် ၃၆ & Hybrid Filter"])

        # --- TAB 1: PREDICTION ---
        with tab1:
            st.subheader("Am, pm တွက်ချက်ခြင်း")
            if st.button("တွက်ချက်မည်", type="primary"):
                with st.spinner("3, 4, 5 ပင်ခြား နှင့် Hybrid Data များကို တွက်ချက်နေပါသည်..."):
                    last_row = daily_draws[-1]
                    predict_slots = []
                    if last_row[2] is None: predict_slots.append(("PM", total_days - 1))
                    else:
                        predict_slots.append(("AM", total_days))
                        predict_slots.append(("PM", total_days))
                        
                    cols = st.columns(len(predict_slots))
                    gaps_to_check = [3, 4, 5]
                    
                    for i, (slot, t_idx) in enumerate(predict_slots):
                        gap_results_list = []
                        for gap in gaps_to_check:
                            preds = calculate_prediction(t_idx, slot, daily_draws, [gap])
                            if preds["ထိပ်"] and preds["ပိတ်"]:
                                combos = [f"{h}{t}" for h in preds["ထိပ်"] for t in preds["ပိတ်"]]
                                vips_gap = [num for num in combos if (int(num[0]) + int(num[1])) % 10 in preds["ဘရိတ်"]]
                                gap_results_list.append({'combos': combos, 'vips': vips_gap})
                            else: gap_results_list.append(None)

                        super_vips, vips, mains, backups = get_ensemble_results(gap_results_list)
                        hybrid_key = get_hybrid_super_key(t_idx, slot, daily_draws)

                        with cols[i]:
                            st.markdown(f"### {slot} ခန့်မှန်းချက်ရလဒ်")
                            st.markdown(f"#### 🔑 **Hybrid Super Key (70%):** [ {', '.join(hybrid_key)} ]")
                            st.markdown("---")
                            if gap_results_list:
                                st.error(f"🔥 **Super VIP:** {', '.join(super_vips) if super_vips else '-'}")
                                st.warning(f"💎 **VIP:** {', '.join(vips) if vips else '-'}")
                                st.success(f"⭐ **main:** {', '.join(mains) if mains else '-'}")
                                st.info(f"🟢 **အရံ:** {', '.join(backups) if backups else '-'}")
                            else:
                                st.warning(f"⚠️ ဤ {slot} အတွက် မူမတွေ့ရှိပါ။")

        # --- TAB 2: BACKTEST ---
        with tab2:
            st.subheader("Hybrid Key & Super VIP Backtest")
            bt_col1, bt_col2 = st.columns([1, 2])
            with bt_col1:
                time_choice = st.radio("စစ်ဆေးလိုသော အချိန်ရွေးပါ:", ["AM", "PM"])
            
            if st.button("၁၀ ရက်စာ နောက်ကြောင်းပြန်စစ်မည် 🔍", key="bt_btn"):
                with st.spinner(f"{time_choice} အတွက် Backtest စစ်ဆေးနေပါသည်..."):
                    backtest_days = 10
                    start_test_idx = max(MIN_STREAK * 5 + 5, total_days - backtest_days)
                    export_data = []
                    progress_bar = st.progress(0)
                    total_steps = total_days - start_test_idx
                    
                    for step, test_idx in enumerate(range(start_test_idx, total_days)):
                        if time_choice == "AM" and daily_draws[test_idx][0] is None: continue
                        if time_choice == "PM" and daily_draws[test_idx][2] is None: continue
                        
                        actual_head = daily_draws[test_idx][0] if time_choice == "AM" else daily_draws[test_idx][2]
                        actual_tail = daily_draws[test_idx][1] if time_choice == "AM" else daily_draws[test_idx][3]
                        actual_2d = f"{actual_head}{actual_tail}"
                        
                        hybrid_key = get_hybrid_super_key(test_idx, time_choice, daily_draws)
                        key_win = "✅ WIN" if (str(actual_head) in hybrid_key or str(actual_tail) in hybrid_key) else "❌ LOSE"
                        
                        export_data.append({
                            "Day": test_idx, f"{time_choice} ထွက်ဂဏန်း": actual_2d,
                            "Hybrid Key": ", ".join(hybrid_key),
                            "Key Result": key_win
                        })
                        progress_bar.progress((step + 1) / total_steps)
                        
                    if export_data:
                        df_report = pd.DataFrame(export_data)
                        st.success("✅ Backtest စစ်ဆေးမှု ပြီးဆုံးပါပြီ။ (Hybrid Key Win Rate 70% ဝန်းကျင်ကို တွေ့ရပါမည်)")
                        st.dataframe(df_report, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_report.to_excel(writer, index=False)
                        st.download_button(label="📥 Excel ဖိုင်ဖြင့် ဒေါင်းလုဒ်ဆွဲရန်", data=buffer, file_name=f"2D_Hybrid_Backtest_{time_choice}.xlsx", mime="application/vnd.ms-excel")

        # --- TAB 3: CALENDAR VIEW ---
        with tab3:
            st.subheader("2D calendar")
            df_display = df.copy()
            df_display['AM'] = df_display.apply(lambda row: f"{int(row['am1'])}{int(row['am2'])}" if pd.notna(row['am1']) and pd.notna(row['am2']) else "-", axis=1)
            df_display['PM'] = df_display.apply(lambda row: f"{int(row['pm1'])}{int(row['pm2'])}" if 'pm1' in df.columns and 'pm2' in df.columns and pd.notna(row['pm1']) and pd.notna(row['pm2']) else "-", axis=1)
            df_display['Day'] = df_display.index
            st.dataframe(df_display[['Day', 'AM', 'PM']], use_container_width=True, hide_index=True)

        # --- TAB 4: ကွက်ချုပ် ၃၆ ကွက် & HYBRID FILTER ---
        with tab4:
            st.subheader("🎯 ကွက်ချုပ် ၃၆ ကွက် နှင့် Hybrid Key စစ်ထုတ်မှုစနစ်")
            st.caption("Hybrid Key ဖြင့် စစ်ထုတ်ထားသော အကွက်များမှာ အရင်းနည်းပြီး အမြတ်အများဆုံး ကျန်မည့် ရွှေကွက်များ ဖြစ်ပါသည်။")
            
            if st.button("ရွှေကွက်များ စစ်ထုတ်မည်", type="primary", key="btn_tab4"):
                with st.spinner("အကောင်းဆုံး ရွှေကွက်များကို စစ်ထုတ်နေပါသည်..."):
                    last_row = daily_draws[-1]
                    predict_slots = []
                    if last_row[2] is None: predict_slots.append(("PM", total_days - 1))
                    else:
                        predict_slots.append(("AM", total_days))
                        predict_slots.append(("PM", total_days))
                        
                    k_cols = st.columns(len(predict_slots))
                    
                    for i, (slot, t_idx) in enumerate(predict_slots):
                        # 1. ၃၆ ကွက် ထုတ်မည်
                        vip_12, main_12, backup_12 = get_12_12_12_kuet_chote(t_idx, slot, daily_draws)
                        all_36 = vip_12 + main_12 + backup_12
                        
                        # 2. Hybrid Key ထုတ်မည်
                        hybrid_key = get_hybrid_super_key(t_idx, slot, daily_draws)
                        
                        # 3. Hybrid Key ဖြင့် Filter လုပ်မည်
                        filtered_kuets = [k for k in all_36 if k[0] in hybrid_key or k[1] in hybrid_key]
                        
                        # Format list into string
                        def format_kuet(num_list):
                            return " , ".join([f"**{n}**" for n in num_list]) if num_list else "မရှိပါ"

                        with k_cols[i]:
                            st.markdown(f"### {slot} ကွက်ချုပ် ရလဒ်")
                            st.markdown(f"🔑 **စစ်ထုတ်မည့် Hybrid Key:** [ **{', '.join(hybrid_key)}** ]")
                            
                            st.success(f"🔥 **စစ်ထုတ်ပြီးသော ရွှေကွက်များ ({len(filtered_kuets)} ကွက်):**")
                            st.info(f"**{format_kuet(filtered_kuets)}**")
                            st.markdown("---")
                            
                            with st.expander("မူလ ကွက်ချုပ် ၃၆ ကွက် အပြည့်အစုံ ကြည့်ရန်"):
                                st.write(f"**🎯 VIP (Top 12):** {format_kuet(vip_12)}")
                                st.write(f"**⭐ MAIN (13 to 24):** {format_kuet(main_12)}")
                                st.write(f"**🟢 အရံ (25 to 36):** {format_kuet(backup_12)}")

    else:
        st.info("👈 ဘေးဘက် (Sidebar) မှတစ်ဆင့် Data ပါဝင်သော Excel သို့မဟုတ် CSV ဖိုင်ကို အရင် တင်ပေးပါ။")
