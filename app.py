import sqlite3
import pandas as pd
import streamlit as st

# Configure modern dashboard layout
st.set_page_config(page_title="Inventory Hub", page_icon="⚡", layout="wide")

# Database initialization
def get_connection():
    conn = sqlite3.connect("inventory.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            threshold INTEGER DEFAULT 5
        )
    """)
    return conn

conn = get_connection()

# Fetch records
def load_data():
    df = pd.read_sql_query("SELECT * FROM products ORDER BY id ASC", conn)
    return df

df = load_data()

# ----------------- UI HEADER -----------------
st.title("⚡ Inventory Management System")
st.markdown("Live Cloud Dashboard")

# ----------------- TOP METRIC CARDS -----------------
col1, col2, col3 = st.columns(3)
total_items = len(df)
total_value = (df['quantity'] * df['price']).sum() if not df.empty else 0.0
low_stock_count = len(df[df['quantity'] <= df['threshold']]) if not df.empty else 0

with col1:
    st.metric("Total Items", f"{total_items}")
with col2:
    st.metric("Total Inventory Value", f"₹{total_value:,.2f}")
with col3:
    st.metric("Low Stock Alerts", f"{low_stock_count}", delta=f"-{low_stock_count}" if low_stock_count > 0 else "0", delta_color="inverse")

st.divider()

# ----------------- SIDEBAR: CRUD CONTROLS -----------------
with st.sidebar:
    st.header("⚙️ Manage Products")
    action = st.radio("Choose Action", ["Add Product", "Update Product", "Delete Product"])

    if action == "Add Product":
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Product Name")
            category = st.text_input("Category")
            qty = st.number_input("Quantity", min_value=0, step=1)
            price = st.number_input("Unit Price (₹)", min_value=0.0, step=10.0, format="%.2f")
            limit = st.number_input("Low Stock Threshold", min_value=1, value=5, step=1)
            submitted = st.form_submit_button("Add Product")
            
            if submitted and name.strip() and category.strip():
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO products (name, category, quantity, price, threshold) VALUES (?, ?, ?, ?, ?)",
                    (name.strip(), category.strip(), int(qty), float(price), int(limit))
                )
                conn.commit()
                st.success(f"Added {name}!")
                st.rerun()

    elif action == "Update Product":
        if df.empty:
            st.info("No items to update.")
        else:
            item_options = {f"{row['id']} - {row['name']}": row['id'] for _, row in df.iterrows()}
            selected = st.selectbox("Select Item to Update", list(item_options.keys()))
            target_id = item_options[selected]
            curr_row = df[df['id'] == target_id].iloc[0]

            with st.form("update_form"):
                u_name = st.text_input("Product Name", value=curr_row['name'])
                u_cat = st.text_input("Category", value=curr_row['category'])
                u_qty = st.number_input("Quantity", min_value=0, value=int(curr_row['quantity']), step=1)
                u_price = st.number_input("Unit Price (₹)", min_value=0.0, value=float(curr_row['price']), step=10.0, format="%.2f")
                u_limit = st.number_input("Threshold", min_value=1, value=int(curr_row['threshold']), step=1)
                update_btn = st.form_submit_button("Update Item")

                if update_btn:
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE products SET name=?, category=?, quantity=?, price=?, threshold=? WHERE id=?",
                        (u_name.strip(), u_cat.strip(), int(u_qty), float(u_price), int(u_limit), target_id)
                    )
                    conn.commit()
                    st.success("Item updated successfully!")
                    st.rerun()

    elif action == "Delete Product":
        if df.empty:
            st.info("No items to delete.")
        else:
            item_options = {f"{row['id']} - {row['name']}": row['id'] for _, row in df.iterrows()}
            selected = st.selectbox("Select Item to Delete", list(item_options.keys()))
            target_id = item_options[selected]

            if st.button("🚨 Delete Item", type="primary"):
                cur = conn.cursor()
                cur.execute("DELETE FROM products WHERE id=?", (target_id,))
                conn.commit()
                st.warning("Deleted successfully!")
                st.rerun()

# ----------------- MAIN VIEW: INVENTORY TABLE -----------------
search = st.text_input("🔍 Search by Product Name or Category", "")

if not df.empty:
    display_df = df.copy()
    if search:
        display_df = display_df[
            display_df['name'].str.contains(search, case=False, na=False) |
            display_df['category'].str.contains(search, case=False, na=False)
        ]

    # Create Option B continuous S.No column
    display_df.insert(0, "S.No", range(1, len(display_df) + 1))
    display_df['Status'] = display_df.apply(
        lambda r: "🚨 LOW STOCK" if r['quantity'] <= r['threshold'] else "✔ IN STOCK", axis=1
    )
    
    # Format currency display
    display_df['price_formatted'] = display_df['price'].apply(lambda x: f"₹{x:,.2f}")

    columns_to_show = ["S.No", "name", "category", "quantity", "price_formatted", "threshold", "Status"]
    st.dataframe(
        display_df[columns_to_show].rename(columns={
            "name": "Product Name",
            "category": "Category",
            "quantity": "Quantity",
            "price_formatted": "Unit Price",
            "threshold": "Min Limit"
        }),
        use_container_width=True,
        hide_index=True
    )

    # CSV Download Button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Inventory Report (CSV)", data=csv, file_name="inventory_report.csv", mime="text/csv")
else:
    st.info("Inventory is currently empty. Use the sidebar on the left to add items.")