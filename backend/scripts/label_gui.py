"""
scripts/label_gui.py - simple Streamlit labeling UI
Run: streamlit run scripts/label_gui.py
"""
import streamlit as st, pandas as pd, os
st.set_page_config(layout="wide")
data_path = st.sidebar.text_input("labels parquet", "data/labels.parquet")
if not os.path.exists(data_path):
    st.warning("Put labelled parquet at "+data_path)
else:
    df = pd.read_parquet(data_path)
    idx = st.sidebar.number_input("index", 0, max(0, len(df)-1), 0)
    row = df.iloc[idx]
    st.write("Timestamp:", row['ts'])
    st.write("Signal:", row['signal'], "Label:", row['label'])
    st.write("Reason:", row.get('reason',''))
    if st.button("Mark Good"):
        df.at[idx,'label']=1; df.to_parquet(data_path); st.success("Marked good")
    if st.button("Mark Bad"):
        df.at[idx,'label']=0; df.to_parquet(data_path); st.success("Marked bad")
    st.dataframe(df.iloc[idx:idx+10])