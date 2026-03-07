import streamlit as st
import os
import importlib.util
import traceback

# --- Always first ---
st.set_page_config(page_title="Micro Tools for Trading", layout="wide")

# --- App Title ---
st.title("Micro Tools for Trading")
st.write("Welcome! This is the first version of your trading ML tool suite.")

# --- Sidebar navigation ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox("Choose the app mode", ["Home", "MLR with NIFTY50","firstcopy"])

# --- Page router logic ---
if app_mode == "Home":
    st.subheader("🏠 Home")
    st.write("You are on the Home page.")
    st.markdown("""
    - Use the sidebar to navigate to your trading tools.
    - Currently available: **MLR with NIFTY50**
    """)

elif app_mode == "firstcopy":
    st.subheader("📋 firstcopy ")

    # Build relative path to the tool (portable)
    file_dir = os.path.dirname(__file__)             # streamlit_app directory
    file_path = os.path.join(file_dir, "firstcopy.py")

    if os.path.exists(file_path):
        # Try to import module cleanly and call run() if present
        try:
            spec = importlib.util.spec_from_file_location("firstcopy.py", file_path)
            first_copy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(first_copy)
            if hasattr(first_copy, "run") and callable(first_copy.run):
                # If the file defines a run() function, call it (recommended pattern)
                first_copy.run()
            else:
                # Fallback: execute file content (last resort)
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                exec(code, globals())
        except Exception as e:
            st.error("Failed to load first_copy tool.")
            st.text(traceback.format_exc())
    else:
        st.error(f"File not found: {file_path}")

    st.markdown("---")
    st.caption("You are in first_copy page.")

elif app_mode == "MLR with NIFTY50":
    st.subheader("📈 MLR with NIFTY50")

    # Build relative path to the tool (portable)
    file_dir = os.path.dirname(__file__)             # streamlit_app directory
    file_path = os.path.join(file_dir, "MLR_with_nifty50.py")

    if os.path.exists(file_path):
        # Try to import module cleanly and call run() if present
        try:
            spec = importlib.util.spec_from_file_location("mlr_tool", file_path)
            mlr = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mlr)
            if hasattr(mlr, "run") and callable(mlr.run):
                # If the file defines a run() function, call it (recommended pattern)
                mlr.run()
            else:
                # Fallback: execute file content (last resort)
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                exec(code, globals())
        except Exception as e:
            st.error("Failed to load MLR_with_nifty50 tool.")
            st.text(traceback.format_exc())
    else:
        st.error(f"File not found: {file_path}")

    st.markdown("---")
    st.caption("You are in MLR with NIFTY50 page.")
