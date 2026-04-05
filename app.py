import streamlit as st
import pandas as pd
import io
import itertools
from collections import Counter
import re

# --- Streamlit Page Config ---
st.set_page_config(page_title="2D SUPER VIP", page_icon="🛡️", layout="wide")

# --- 1. Configurations & Dictionaries ---
power_dict = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
natkhat_dict = {0: 7, 7: 0, 1: 8, 8: 1, 2: 4, 4: 2, 3: 5, 5: 3, 6: 9, 9: 6}
special_groups = {
    "ညီကို": {"01","10","12","21","23","32","34","43","45","54","56","65","67","76","78","87","89","98","90","09"},
    "ပါဝါ": {"05","50","16","61","27","72","38","83","49","94"},
    "နက္ခတ်": {"07","70","18","81","24","42","35","53","69","96"},
    "ထိုင်းပါဝါ": {"09","90","13","31","26","62","47","74","58","85"},
    "အပူး": {"00","11","22","33","44","55","66","77","88","99"}
}

# --- 2. Password Protection ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        pwd = st.text_input("Password ရိုက်ထည့်ပါ -", type="password")
        if st.button("Login"):
            if pwd == "v27admin":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password မှားယွင်းနေပါသည်။")
        return False
    return True

# --- 3. UI Helper: Color & Size ---
def display_pairs_html(pairs, super_key):
    if not pairs: return "မရှိပါ"
    html_res = ""
    for p in pairs:
        # Check if digits of pair match any digit in super_key
        match = any(int(d) in super_key for d in p)
        color = "#ff4b4b" if match else "#31333f"
        html_res += f"<span style='color:{color}; font-size:26px; margin-right:25px;'>{p}</span>"
    return f"<div>{html_res}</div>"

# --- 4. 5x5 Hybrid Rolling Engine (Upgraded) ---
def get_hybrid_5x5_trend(d, slot, daily_draws, gap_signals=None):
    # Security: Lookahead Prevention
    full_h = []
    for past_d in range(d + 1):
        if daily_draws[past_d][0] is not None:
            if past_d == d and slot == "AM": pass
            else: full_h.append((daily_draws[past_d][0], daily_draws[past_d][1]))
        if daily_draws[past_d][2] is not None:
            if past_d == d and slot == "PM": pass
            else: full_h.append((daily_draws[past_d][2], daily_draws[past_d][3]))
    
    if not full_h: return [0,1,2,3,4], [0,1,2,3,4], [0,1,2,3,4]
    last = full_h[-1]
    
    h_scores = {i: 0.0 for i in range(10)}
    t_scores = {i: 0.0 for i in range(10)}
    b_scores = {i: 0.0 for i in range(10)}

    # 1. Markov Flow (Transition)
    for idx in range(len(full_h)-1):
        curr, nxt = full_h[idx], full_h[idx+1]
        if curr[0] == last[0]: h_scores[nxt[0]] += 1.5
        if curr[1] == last[1]: t_scores[nxt[1]] += 1.5

    # 2. Exponential Heat (Last 15 draws)
    for i, p in enumerate(full_h[-15:]):
        weight = (i+1) * 0.8
        h_scores[p[0]] += weight
        t_scores[p[1]] += weight
        b_scores[(p[0]+p[1])%10] += weight

    # 3. Gap Synergy
    if gap_signals:
        for val in gap_signals.get('h', []): h_scores[val] += 5.0
        for val in gap_signals.get('t', []): t_scores[val] += 5.0

    # 4. Power/Natkhat Triggers
    h_scores[power_dict[last[0]]] += 2.0; h_scores[natkhat_dict[last[0]]] += 2.0
    t_scores[power_dict[last[1]]] += 2.0; t_scores[natkhat_dict[last[1]]] += 2.0

    top_h = sorted(h_scores.keys(), key=lambda x: h_scores[x], reverse=True)[:5]
    top_t = sorted(t_scores.keys(), key=lambda x: t_scores[x], reverse=True)[:5]
    top_b = sorted(b_scores.keys(), key=lambda x: b_scores[x], reverse=True)[:5]
    
    return top_h, top_t, top_b

# --- 5. V26 Data Analysis Engine (Tab 3 & 4) ---
@st.cache_data(show_spinner=False)
def analyze_history_v26(target_2d, f_draws, scope_min=20, scope_max=40, time_frame=20):
    hits = [d for d in f_draws if d['draw'] == target_2d]
    if len(hits) < scope_min: return None
    
    best_pattern = None
    for scope in range(scope_min, min(len(hits), scope_max) + 1):
        scope_hits = hits[-scope:]
        
        # We only check 20-draw time frame fixed as per user request
        ev_subs = []
        for hit in scope_hits:
            s_idx, e_idx = hit['index']+1, min(hit['index']+time_frame+1, len(f_draws))
            ev_subs.append([d['draw'] for d in f_draws[s_idx:e_idx]] if s_idx < len(f_draws) else [])
        
        if not any(ev_subs): continue
        all_flat = list(itertools.chain(*[ev for ev in ev_subs if ev]))
        if not all_flat: continue
        
        # Rule check: Long-Bိုင် (Most Frequent Single Digit)
        top_digits = [x[0] for x in Counter("".join(all_flat)).most_common(3)]
        for digit in top_digits:
            success_count = sum(1 for ev in ev_subs if any(digit in d for d in ev))
            rate = (success_count / len(ev_subs)) * 100
            if rate >= 95.0:
                # Comeback check
                is_comeback = False
                if len(ev_subs) >= 3:
                    results = [any(digit in d for d in ev) for ev in ev_subs]
                    if not results[-2] and results[-1]: is_comeback = True
                
                if best_pattern is None or rate > best_pattern['rate']:
                    best_pattern = {
                        'type': 'လုံးဘိုင်', 'val': digit, 'rate': rate, 
                        'hits': f"{success_count}/{len(ev_subs)}", 'scope': scope,
                        'comeback': is_comeback
                    }
    return best_pattern

# --- 6. Main App Structure ---
if check_password():
    st.sidebar.title("⚙️ V28.0 Control")
    uploaded = st.sidebar.file_uploader("Excel Data ဖိုင်တင်ပါ", type=['xlsx', 'csv'])

    if uploaded:
        if uploaded.name.endswith('.csv'): df = pd.read_csv(uploaded)
        else: df = pd.read_excel(uploaded)
        
        # Data Cleaning
        df.columns = df.columns.str.strip().str.lower()
        for c in ['am1','am2','pm1','pm2']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['am1','am2']).reset_index(drop=True)
        
        daily_draws = []
        for i, row in df.iterrows():
            daily_draws.append([int(row[c]) if pd.notna(row[c]) else None for c in ['am1','am2','pm1','pm2']])
        
        # Build V26 History
        f_draws = []
        for i, d in enumerate(daily_draws):
            if d[0] is not None: f_draws.append({'draw': f"{d[0]}{d[1]}", 'index': len(f_draws)})
            if d[2] is not None: f_draws.append({'draw': f"{d[2]}{d[3]}", 'index': len(f_draws)})

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["မူလစနစ်", "Stock Market", "2d history", "ရက်ချိန်းပြည့်မူများ", "Calendar"])

        # TAB 1: မူလစနစ် (VIP 12 ကွက်)
        with tab1:
            if st.button("VIP ၁၂ ကွက် တွက်မည်"):
                res_am, _ = get_hybrid_5x5_trend(len(daily_draws)-1, "AM", daily_draws)
                # Display logic for 12 pairs cross-checked with trends...
                st.write("### AM VIP Results")
                st.write("*(Tab 1 Logic Processing...)*")

        # TAB 2: Stock Market (25 ကွက်)
        with tab2:
            st.subheader("Stock Market Hybrid (၂၅ ကွက်)")
            t_h, t_t, _ = get_hybrid_5x5_trend(len(daily_draws)-1, "AM", daily_draws)
            s_key = t_h[:3]
            pairs = [f"{h}{t}" for h in t_h for t in t_t]
            st.markdown(f"**Super Key: {s_key}**")
            st.markdown(display_pairs_html(pairs, s_key), unsafe_allow_html=True)
            st.code(", ".join(pairs))

        # TAB 3: 2d history
        with tab3:
            st.subheader("2D Data Analysis (Auto 95-100%)")
            target = st.text_input("ရှာဖွေမည့်ဂဏန်း (01-99)", max_chars=2)
            if target and st.button("သမိုင်းကြောင်းစစ်မည်"):
                res = analyze_history_v26(target, f_draws, scope_min=20, scope_max=40, time_frame=20)
                if res:
                    st.success(f"🎯 အကောင်းဆုံးမူ တွေ့ရှိသည် (Scope: {res['scope']} ကြိမ်)")
                    st.markdown(f"<span style='font-size:30px; color:red;'>{res['type']} : [{res['val']}]</span>", unsafe_allow_html=True)
                    st.write(f"မှန်ကန်မှု: {res['hits']} ({res['rate']:.1f}%) | Time Frame: နောက်ပွဲ ၂၀ အတွင်း")
                    if res['comeback']: st.error("🔥 ဤမူသည် လွဲပြီးပြန်တက်လာသော [အမှားပြန်ဆယ်မူ] ဖြစ်သည်။")
                else: st.warning("95% အထက်သေချာသော မူမရှိပါ။")

        # TAB 4: ရက်ချိန်းပြည့်မူများ
        with tab4:
            st.subheader("ရက်ချိန်းပြည့်မူများ (Current Alerts)")
            st.info("အပေါ်တွင် 5x5 စစ်ထုတ်ထားသော VIP ကတ်များ၊ အောက်တွင် အသေးစိတ်ဇယား")
            # Logic to run run_v26_engine and filter with 5x5...

        # TAB 5: Calendar
        with tab5:
            st.subheader("2D Calendar")
            # Anchor April 3, 2026 logic...
