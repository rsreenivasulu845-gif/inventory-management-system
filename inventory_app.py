# from tkinter import messagebox, ttk
import csv
import sqlite3
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

# ----------------------------------------------------
# DATABASE LAYER
# ----------------------------------------------------
class InventoryDatabase:
    def __init__(self, db_name="inventory.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            threshold INTEGER DEFAULT 5
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    def insert_product(self, name, category, quantity, price, threshold):
        query = "INSERT INTO products (name, category, quantity, price, threshold) VALUES (?, ?, ?, ?, ?)"
        self.cursor.execute(query, (name, category, quantity, price, threshold))
        self.conn.commit()

    def fetch_all(self):
        # Natural ascending order
        self.cursor.execute("SELECT * FROM products ORDER BY id ASC")
        return self.cursor.fetchall()

    def search_products(self, query):
        term = f"%{query}%"
        self.cursor.execute(
            "SELECT * FROM products WHERE (name LIKE ? OR category LIKE ?) ORDER BY id ASC",
            (term, term),
        )
        return self.cursor.fetchall()

    def update_product(self, prod_id, name, category, quantity, price, threshold):
        query = """
        UPDATE products 
        SET name = ?, category = ?, quantity = ?, price = ?, threshold = ?
        WHERE id = ?
        """
        self.cursor.execute(query, (name, category, quantity, price, threshold, prod_id))
        self.conn.commit()

    def delete_product(self, prod_id):
        self.cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        self.conn.commit()

    def get_summary_stats(self):
        self.cursor.execute("SELECT COUNT(*), SUM(quantity * price) FROM products")
        count, total_val = self.cursor.fetchone()
        self.cursor.execute("SELECT COUNT(*) FROM products WHERE quantity <= threshold")
        low_stock = self.cursor.fetchone()[0]
        return count or 0, total_val or 0.0, low_stock or 0


# ----------------------------------------------------
# MODERN GUI (CustomTkinter + ttk.Treeview)
# ----------------------------------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ModernInventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Inventory Command Center")
        self.geometry("1180x720")
        self.minsize(1050, 650)

        self.db = InventoryDatabase()
        self.selected_id = None

        self._configure_tree_theme()
        self._build_layout()
        self.refresh_table()

    def _configure_tree_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background="#1E293B",
            foreground="#F8FAFC",
            fieldbackground="#1E293B",
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#0F172A",
            foreground="#94A3B8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 8),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#1E293B")],
            foreground=[("active", "#38BDF8")],
        )
        style.map(
            "Treeview",
            background=[("selected", "#0284C7")],
            foreground=[("selected", "#FFFFFF")],
        )

    def _build_layout(self):
        # 1. Top Navbar
        nav = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#0F172A")
        nav.pack(side="top", fill="x")

        nav_title = ctk.CTkLabel(
            nav,
            text="⚡ INVENTORY HUB",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#38BDF8",
        )
        nav_title.pack(side="left", padx=25, pady=15)

        # 2. Main Layout Area
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Left Panel: Item Entry Form ---
        form_card = ctk.CTkFrame(content, width=320, corner_radius=12, fg_color="#1E293B")
        form_card.pack(side="left", fill="y", padx=(0, 20))
        form_card.pack_propagate(False)

        card_title = ctk.CTkLabel(
            form_card,
            text="Item Specifications",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#F8FAFC",
        )
        card_title.pack(anchor="w", padx=20, pady=(20, 15))

        self.inputs = {}
        fields = [
            ("Product Name", "e.g., Armory"),
            ("Category", "e.g., Rifles, Pistols"),
            ("Quantity", "0"),
            ("Unit Price (₹)", "0.00"),
            ("Low-Stock Limit", "5"),
        ]

        for label, placeholder in fields:
            lbl = ctk.CTkLabel(
                form_card,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#94A3B8",
            )
            lbl.pack(anchor="w", padx=20, pady=(6, 2))

            entry = ctk.CTkEntry(
                form_card,
                height=34,
                placeholder_text=placeholder,
                fg_color="#0F172A",
                border_color="#334155",
                text_color="#FFFFFF",
            )
            entry.pack(fill="x", padx=20, pady=(0, 4))
            self.inputs[label] = entry

        self.inputs["Low-Stock Limit"].insert(0, "5")

        # Action Buttons
        btn_box = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(20, 10))

        self.btn_add = ctk.CTkButton(
            btn_box,
            text="+ Add Item",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            command=self.add_record,
        )
        self.btn_add.pack(fill="x", pady=4)

        self.btn_update = ctk.CTkButton(
            btn_box,
            text="Update Item",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#0D9488",
            hover_color="#0F766E",
            command=self.update_record,
        )
        self.btn_update.pack(fill="x", pady=4)

        action_row = ctk.CTkFrame(btn_box, fg_color="transparent")
        action_row.pack(fill="x", pady=4)

        ctk.CTkButton(
            action_row,
            text="Delete",
            width=130,
            fg_color="#E11D48",
            hover_color="#BE123C",
            command=self.delete_record,
        ).pack(side="left")

        ctk.CTkButton(
            action_row,
            text="Clear",
            width=130,
            fg_color="#475569",
            hover_color="#334155",
            command=self.clear_inputs,
        ).pack(side="right")

        # --- Right Panel: Stats, Search, and Table ---
        right_panel = ctk.CTkFrame(content, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        # Stat Badges
        stats_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 15))

        self.stat_products = self._create_metric_card(stats_frame, "Total Items", "0")
        self.stat_val = self._create_metric_card(stats_frame, "Total Value", "₹0.00")
        self.stat_alerts = self._create_metric_card(stats_frame, "Low Stock Alerts", "0", alert=True)

        # Search Bar & Export Controls
        ctrl_bar = ctk.CTkFrame(right_panel, fg_color="transparent")
        ctrl_bar.pack(fill="x", pady=(0, 12))

        self.search_entry = ctk.CTkEntry(
            ctrl_bar,
            width=280,
            height=36,
            placeholder_text="🔍 Search product or category...",
            fg_color="#1E293B",
            border_color="#334155",
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self.filter_records)

        ctk.CTkButton(
            ctrl_bar,
            text="Export CSV",
            width=100,
            height=36,
            fg_color="#334155",
            hover_color="#475569",
            command=self.export_csv,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            ctrl_bar,
            text="Reset",
            width=80,
            height=36,
            fg_color="#334155",
            hover_color="#475569",
            command=self.refresh_table,
        ).pack(side="right")

        # Table Container
        table_container = ctk.CTkFrame(right_panel, corner_radius=10, fg_color="#1E293B")
        table_container.pack(fill="both", expand=True)

        columns = ("SNo", "Name", "Category", "Quantity", "Price", "Limit", "Status")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("SNo", text="S.No")
        self.tree.heading("Name", text="Product Name")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Price", text="Unit Price")
        self.tree.heading("Limit", text="Min Limit")
        self.tree.heading("Status", text="Stock Status")

        self.tree.column("SNo", width=50, anchor="center")
        self.tree.column("Name", width=180)
        self.tree.column("Category", width=120)
        self.tree.column("Quantity", width=80, anchor="center")
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Limit", width=80, anchor="center")
        self.tree.column("Status", width=130, anchor="center")

        self.tree.tag_configure("even", background="#1E293B", foreground="#F8FAFC")
        self.tree.tag_configure("odd", background="#172233", foreground="#F8FAFC")
        self.tree.tag_configure("low_stock", background="#450A0A", foreground="#F87171")

        tree_scroll = ctk.CTkScrollbar(table_container, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        tree_scroll.pack(side="right", fill="y", padx=5, pady=5)
        self.tree.pack(fill="both", expand=True, padx=(8, 0), pady=8)

        self.tree.bind("<<TreeviewSelect>>", self.on_select_record)

    def _create_metric_card(self, parent, title, initial_val, alert=False):
        card = ctk.CTkFrame(parent, height=65, corner_radius=10, fg_color="#1E293B")
        card.pack(side="left", fill="x", expand=True, padx=4)
        card.pack_propagate(False)

        t_lbl = ctk.CTkLabel(card, text=title, font=("Segoe UI", 11, "bold"), text_color="#94A3B8")
        t_lbl.pack(anchor="w", padx=15, pady=(8, 0))

        v_lbl = ctk.CTkLabel(
            card,
            text=initial_val,
            font=("Segoe UI", 16, "bold"),
            text_color="#EF4444" if alert else "#38BDF8",
        )
        v_lbl.pack(anchor="w", padx=15)
        return v_lbl

    # ----------------------------------------------------
    # CONTROLLER LOGIC (OPTION B INTEGRATION)
    # ----------------------------------------------------
    def validate_inputs(self):
        name = self.inputs["Product Name"].get().strip()
        cat = self.inputs["Category"].get().strip()
        qty = self.inputs["Quantity"].get().strip()
        price = self.inputs["Unit Price (₹)"].get().strip()
        limit = self.inputs["Low-Stock Limit"].get().strip()

        if not all([name, cat, qty, price, limit]):
            messagebox.showerror("Error", "Please fill in all fields.")
            return None

        try:
            qty = int(qty)
            price = float(price)
            limit = int(limit)
            if qty < 0 or price < 0 or limit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Validation Error", "Quantity/Limit must be positive integers, and Price must be a valid number.")
            return None

        return name, cat, qty, price, limit

    def add_record(self):
        data = self.validate_inputs()
        if not data:
            return
        self.db.insert_product(*data)
        self.clear_inputs()
        self.refresh_table()

    def update_record(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select a record from the table to update.")
            return
        data = self.validate_inputs()
        if not data:
            return
        self.db.update_product(self.selected_id, *data)
        self.clear_inputs()
        self.refresh_table()

    def delete_record(self):
        if not self.selected_id:
            messagebox.showwarning("Warning", "Select an item from the table to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Permanently remove this item?"):
            self.db.delete_product(self.selected_id)
            self.clear_inputs()
            self.refresh_table()

    def clear_inputs(self):
        self.selected_id = None
        for key, ent in self.inputs.items():
            ent.delete(0, "end")
        self.inputs["Low-Stock Limit"].insert(0, "5")
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def on_select_record(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return

        values = self.tree.item(selected_item, "values")
        if not values:
            return

        # Option B: The item ID (iid) stores the true database primary key
        self.selected_id = int(selected_item)

        self.inputs["Product Name"].delete(0, "end")
        self.inputs["Product Name"].insert(0, values[1])

        self.inputs["Category"].delete(0, "end")
        self.inputs["Category"].insert(0, values[2])

        self.inputs["Quantity"].delete(0, "end")
        self.inputs["Quantity"].insert(0, values[3])

        raw_price = values[4].replace("₹", "").replace(",", "")
        self.inputs["Unit Price (₹)"].delete(0, "end")
        self.inputs["Unit Price (₹)"].insert(0, raw_price)

        self.inputs["Low-Stock Limit"].delete(0, "end")
        self.inputs["Low-Stock Limit"].insert(0, values[5])

    def render_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows, start=1):
            db_id, name, cat, qty, price, limit = row
            status = "🚨 LOW STOCK" if qty <= limit else "✔ IN STOCK"
            tag = "low_stock" if qty <= limit else ("even" if i % 2 == 0 else "odd")

            self.tree.insert(
                "",
                "end",
                iid=str(db_id),  # Store actual database ID internally
                values=(i, name, cat, qty, f"₹{price:,.2f}", limit, status),
                tags=(tag,),
            )

    def refresh_table(self):
        self.search_entry.delete(0, "end")
        rows = self.db.fetch_all()
        self.render_rows(rows)
        self.update_stats()

    def filter_records(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            self.render_rows(self.db.fetch_all())
        else:
            rows = self.db.search_products(query)
            self.render_rows(rows)

    def update_stats(self):
        count, total_val, low_stock = self.db.get_summary_stats()
        self.stat_products.configure(text=f"{count}")
        self.stat_val.configure(text=f"₹{total_val:,.2f}")
        self.stat_alerts.configure(text=f"{low_stock}")

    def export_csv(self):
        rows = self.db.fetch_all()
        if not rows:
            messagebox.showinfo("Export", "No data to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save Inventory Report",
        )
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Category", "Quantity", "Price", "LowStockLimit"])
                writer.writerows(rows)
            messagebox.showinfo("Export Successful", f"Data exported to:\n{filepath}")


if __name__ == "__main__":
    app = ModernInventoryApp()
    app.mainloop()