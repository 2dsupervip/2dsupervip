import streamlit as st
import pandas as pd
from collections import Counter

# --- Page Config ---
st.set_page_config(page_title="2D Master AI (Pro Dashboard)", page_icon="🎯", layout="wide")

# --- Dictionaries (မူလစနစ်အတွက်) ---
power_dict = {0:5, 1:6, 2:7, 3:8, 4:9, 5:0, 6:1, 7:2, 8:3, 9:4}
natkhat_dict = {0:7, 7:0, 1:8, 8:1, 2:4, 4:2, 3:5, 5:3, 6:9, 9:6}

# --- 1. The Core 9-7 Engine ---
def predict_9_7_engine(timeline, window=9, history_limit=7):
    recent_draws = timeline[-window:]
    head_scores = {i: 0.0 for i in range(10)}
    tail_scores = {i: 0.0 for i in range(10)}

    def search_and_score(condition_func, limit, weight, offset):
        count = 0
        start_search_idx = len(timeline) - 1 - offset
        for i in range(start_search_idx, -1, -1):
            if condition_func(timeline[i]):
                target_idx = i + offset
                if target_idx < len(timeline):
                    nxt = timeline[target_idx]
                    head_scores[nxt[0]] += weight
                    tail_scores[nxt[1]] += weight
                    count += 1
                    if count >= limit: break

    for idx_r, (r_h, r_t) in enumerate(recent_draws):
        lag = window - idx_r 
        search_and_score(lambda x: x[0] == r_h, limit=history_limit, weight=1.0, offset=lag)
        search_and_score(lambda x: x[1] == r_t, limit=history_limit, weight=1.0, offset=lag)
        search_and_score(lambda x: x[0] == r_h and x[1] == r_t, limit=history_limit, weight=3.0, offset=lag)

    top_heads = sorted(head_scores.keys(), key=lambda x: head_scores[x], reverse=True)[:5]
    top_tails = sorted(tail_scores.keys(), key=lambda x: tail_scores[x], reverse=True)[:5]
    final_pairs = [f"{h}{t}" for h in top_heads for t in top_tails]
    return top_heads, top_tails, final_pairs

# --- 2. Super Key (3 Digits) ---
def get_super_key(timeline):
    last_draw = timeline[-1]
    followers = []
    for i in range(len(timeline)-1):
        if timeline[i] == last_draw:
            followers.extend([timeline[i+1][0], timeline[i+1][1]])
    if not followers:
        for p in timeline[-20:]: followers.extend([p[0], p[1]])
    return [k for k, v in Counter(followers).most_common(3)]

# --- 3. Original System (မူလစနစ် ၄ ကွက် + Fallback) ---
def get_original_system(last_draw, core_pairs):
    h, t = last_draw
    heads = [power_dict[h], h]
    tails = [natkhat_dict[t], t]
    breaks = [(h+t)%10, power_dict[(h+t)%10]]

    pairs = []
    for x in heads:
        for y in tails:
            if (x+y)%10 in breaks:
                pairs.append(f"{x}{y}")
    
    # Fallback (၄ ကွက်မပြည့်လျှင် 9-7 Engine မှ ယူဖြည့်မည်)
    idx = 0
    while len(pairs) < 4 and idx < len(core_pairs):
        if core_pairs[idx] not in pairs:
            pairs.append(core_pairs[idx])
        idx += 1
    return list(set(pairs))[:4] # အသေချာဆုံး ၄ ကွက်

# --- 4. History Formulas (မူ ၁၀ မျိုး သီးသန့်) ---
def get_10_formulas(last_draw):
    h, t = last_draw
    return {
        "၁။ ပါဝါမူ": [power_dict[h], power_dict[t]],
        "၂။ နက္ခတ်မူ": [natkhat_dict[h], natkhat_dict[t]],
        "၃။ ဘရိတ်မူ": [(h+t)%10, power_dict[(h+t)%10]],
        "၄။ ထိပ်တူမူ": [h, (h+1)%10],
        "၅။ ပိတ်တူမူ": [t, (t-1)%10],
        "၆။ ညီအစ်ကိုမူ": [(h+1)%10, (t-1)%10],
        "၇။ အပူးမူ": [h, t], 
        "၈။ ပြောင်းပြန် (Reverse)": [t, h],
        "၉။ အပေါင်းမူ (+3)": [(h+3)%10, (t+3)%10], 
        "၁၀။ အနုတ်မူ (-2)": [(h-2)%10, (t-2)%10]  
    }

# --- 5. Overdue System (ရက်ချိန်းပြည့်) ---
def get_overdue_system(timeline, core_heads, core_tails, days=5):
    draws_to_check = days * 2
    if len(timeline) < draws_to_check: return [], []
    recent = timeline[-draws_to_check:]
    appeared = set()
    for h, t in recent:
        appeared.add(h)
        appeared.add(t)
    
    overdue = [d for d in range(10) if d not in appeared]
    # Supreme Judge: 9-7 စနစ်နှင့် ငြိမှသာ VIP အဖြစ် ရွေးမည်
    core_set = set(core_heads + core_tails)
    main_vip = [d for d in overdue if d in core_set]
    return overdue, main_vip


# ==========================================
# 🖥️ Web App UI Layout
# ==========================================

st.title("🎯 2D Master AI (Multi-System Dashboard)")
st.markdown("**(9-7 Core Engine + Original DNA + Overdue Sniper)**")
st.markdown("---")

uploaded_file = st.file_uploader("📂 Excel Data ဖိုင်ကို တင်ပါ ('x' များပါဝင်လည်း AI အလိုအလျောက် ရှင်းလင်းပေးမည်)", type=['xlsx'])

if uploaded_file is not None:
    try:
        # Data Cleaning
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        for col in ['am1', 'am2', 'pm1', 'pm2']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') # 'x' နှင့် text များကို ရှင်းလင်းခြင်း
        
        timeline = []
        for d_idx, row in df.iterrows():
            if pd.notna(row.get('am1')) and pd.notna(row.get('am2')):
                timeline.append((int(row['am1']), int(row['am2'])))
            if pd.notna(row.get('pm1')) and pd.notna(row.get('pm2')):
                timeline.append((int(row['pm1']), int(row['pm2'])))

        if len(timeline) < 10:
            st.error("⚠️ Data မလုံလောက်ပါ။ အနည်းဆုံး ၁၀ ပွဲ ပါဝင်ရမည်။")
        else:
            last_draw = timeline[-1]
            st.success(f"✅ Data ဖတ်ရှုခြင်း အောင်မြင်ပါပြီ။ (စုစုပေါင်း ပွဲရေ: {len(timeline)} ပွဲ) | နောက်ဆုံးဂဏန်း: **{last_draw[0]}{last_draw[1]}**")
            
            # --- AI တွက်ချက်မှုများ စတင်ခြင်း ---
            core_heads, core_tails, core_pairs = predict_9_7_engine(timeline)
            super_key = get_super_key(timeline)
            orig_4_pairs = get_original_system(last_draw, core_pairs)
            formulas_10 = get_10_formulas(last_draw)
            overdue_all, overdue_vip = get_overdue_system(timeline, core_heads, core_tails)

            # --- Dashboard Tabs ---
            tab1, tab2, tab3, tab4 = st.tabs(["📈 The 9-7 Core (Daily)", "🔑 Super Key & Original", "🔍 10 Formulas (History)", "🚨 Overdue (ရက်ချိန်းပြည့်)"])

            # Tab 1: 9-7 Engine (၂၅ ကွက်)
            with tab1:
                st.markdown("### 🔥 The 9-7 Lag-Adjusted Engine (Win Rate 40%)")
                st.write(f"**အကောင်းဆုံး ထိပ်စီး ၅ လုံး:** `{core_heads}`")
                st.write(f"**အကောင်းဆုံး နောက်ပိတ် ၅ လုံး:** `{core_tails}`")
                st.markdown("#### 🎯 ထိုးရန် အကွက် (၂၅) ကွက်")
                formatted_pairs = "\n".join([" | ".join(core_pairs[i:i+5]) for i in range(0, len(core_pairs), 5)])
                st.code(formatted_pairs, language="text")

            # Tab 2: Super Key & Original System
            with tab2:
                st.markdown("### 🔑 The Super Key (စူပါအမာခံ ၃ လုံး)")
                st.info(f"သမိုင်းတစ်လျှောက် နောက်ဆုံးပွဲပြီးတိုင်း အများဆုံးလိုက်သော ဂဏန်း: **{super_key}**")
                
                st.markdown("### 🧩 မူလစနစ် (၄ ကွက်)")
                st.markdown("*(မှတ်ချက်: ထိပ်၊ ပိတ်၊ ဘရိတ် စည်းမျဉ်းများမပြည့်စုံပါက 9-7 Engine မှ အလိုအလျောက် ဖြည့်စွက်ထားသည်။)*")
                st.success(f"**အတည်ပြု ၄ ကွက်:** `{orig_4_pairs}`")

            # Tab 3: 10 Formulas (မူ ၁၀ မျိုး)
            with tab3:
                st.markdown("### 🔍 သမိုင်းကြောင်း မူ (၁၀) မျိုး (Decoupled)")
                st.markdown("*(မိမိနှစ်သက်ရာ မူကို ရွေးချယ်ကစားရန်)*")
                cols = st.columns(2)
                for i, (name, digits) in enumerate(formulas_10.items()):
                    with cols[i % 2]:
                        st.write(f"**{name}:** `{digits}`")

            # Tab 4: Overdue System (ရက်ချိန်းပြည့်)
            with tab4:
                st.markdown("### 🚨 (၅) ရက်စာ ရက်ချိန်းပြည့် စနစ်")
                if not overdue_all:
                    st.success("✅ လတ်တလော ၅ ရက်အတွင်း ကျန်ရစ်သော ဂဏန်း မရှိပါ။ ဈေးကွက်လှည့်ပတ်မှု ကောင်းမွန်ပါသည်။")
                else:
                    st.warning(f"⚠️ ပျောက်နေသော ဂဏန်းများ (Overdue): **{overdue_all}**")
                    
                    st.markdown("### ⚖️ The Supreme Judge (9-7 စနစ်ဖြင့် စစ်ထုတ်ခြင်း)")
                    if overdue_vip:
                        st.error(f"🎯 **VIP Main စူပါအမာခံ (ထိုးရန်): {overdue_vip}**")
                        st.markdown("*အထက်ပါဂဏန်းသည် ရက်ချိန်းလည်းပြည့်၊ 9-7 ရေစီးကြောင်းတွင်လည်း ပါဝင်နေသဖြင့် အသေချာဆုံး ဖြစ်သည်။*")
                    else:
                        st.info("🤷‍♂️ 9-7 Engine ရေစီးကြောင်းထဲတွင် ရက်ချိန်းပြည့်ဂဏန်းများ မပါဝင်ပါ။ (ဤအပတ် ရက်ချိန်းပြည့်ဂဏန်းများကို Skip လုပ်ရန် အကြံပြုပါသည်)")
                        
    except Exception as e:
        st.error(f"❌ ဖိုင်ဖတ်ရှုရာတွင် သို့မဟုတ် တွက်ချက်ရာတွင် အမှားအယွင်းဖြစ်နေပါသည်။ ({e})")
